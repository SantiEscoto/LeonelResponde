import React, { useCallback, useEffect, useRef, useState } from 'react'

interface MicButtonProps {
  onPartialText?: (text: string) => void
  onFinalText?: (text: string) => void
  useVAD?: boolean
  vadLevel?: number
  frameMs?: number
  className?: string
}

function floatTo16BitPCM(input: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(input.length * 2)
  const view = new DataView(buffer)
  let offset = 0
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }
  return buffer
}

function resampleFloat32ToRate(input: Float32Array, sourceRate: number, targetRate: number): Float32Array {
  if (sourceRate === targetRate) return input
  const ratio = sourceRate / targetRate
  const outLength = Math.floor(input.length / ratio)
  const output = new Float32Array(outLength)
  let pos = 0
  for (let i = 0; i < outLength; i++) {
    output[i] = input[Math.floor(pos)] || 0
    pos += ratio
  }
  return output
}

// Convertir ArrayBuffer a base64 para modo JSON
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

// Tipos de mensajes del WS
interface Pong { type: 'pong'; ts?: number; server_ts?: number }
interface PartialMsg { type: 'partial'; text: string }
interface FinalMsg { type: 'final'; text: string; confidence?: number }
interface AckMsg { type: 'ack'; seq: number; accepted: boolean }
interface ErrMsg { type: 'error'; message: string }

type WsMsg = Pong | PartialMsg | FinalMsg | AckMsg | ErrMsg

const MicButton: React.FC<MicButtonProps> = ({
  onPartialText,
  onFinalText,
  useVAD = true,
  vadLevel = 2,
  frameMs = 30,
  className = ''
}) => {
  const [connected, setConnected] = useState<boolean>(false)
  const [recording, setRecording] = useState<boolean>(false)
  const [waitingAck, setWaitingAck] = useState<boolean>(false)
  const [queueSize, setQueueSize] = useState<number>(0)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const heartbeatRef = useRef<number | null>(null)
  const awaitAckRef = useRef<boolean>(false)
  const queueRef = useRef<ArrayBuffer[]>([])
  const sttStartedRef = useRef<boolean>(false)

  // Referencias para auto-stop por silencio
  const voiceDetectedRef = useRef<boolean>(false)
  const lastVoiceTsRef = useRef<number>(0)
  const autoStopSentRef = useRef<boolean>(false)

  const voiceWsUrl = (() => {
    const full = import.meta.env.VITE_VOICE_WS_URL as string | undefined
    if (full && full.startsWith('ws')) return full
    const host = (import.meta.env.VITE_VOICE_WS_HOST as string) || 'localhost'
    const port = (import.meta.env.VITE_VOICE_WS_PORT as string) || '8010'
    return `ws://${host}:${port}/ws/stt`
  })()

  const sendMode: 'binary' | 'json' = (
    ((import.meta.env.VITE_VOICE_WS_MODE as string) || 'binary').toLowerCase() as 'binary' | 'json'
  )

  // Configuración de silencio (con valores por defecto sensatos)
  const silenceMs = Number.parseInt((import.meta.env.VITE_VOICE_SILENCE_MS as string) || '1500', 10)
  const silenceRms = Number.parseFloat((import.meta.env.VITE_VOICE_SILENCE_RMS as string) || '0.015')
  const autoStopOnSilence = (((import.meta.env.VITE_VOICE_AUTOSTOP_SILENCE as string) || 'true').toLowerCase() !== 'false')

  const cleanupAudio = useCallback(() => {
    try {
      processorRef.current?.disconnect()
      processorRef.current = null
    } catch (err) {
      console.debug('Audio processor disconnect error', err)
    }

    try {
      audioContextRef.current?.close()
      audioContextRef.current = null
    } catch (err) {
      console.debug('AudioContext close error', err)
    }

    try {
      streamRef.current?.getTracks().forEach(t => t.stop())
      streamRef.current = null
    } catch (err) {
      console.debug('MediaStream tracks stop error', err)
    }
  }, [])

  // Enviar siguiente chunk según modo
  const maybeSendNext = useCallback(() => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    if (!sttStartedRef.current) return
    if (awaitAckRef.current) return
    const next = queueRef.current.shift()
    if (next) {
      awaitAckRef.current = true
      setWaitingAck(true)
      setQueueSize(queueRef.current.length)
      if (sendMode === 'json') {
        try {
          const b64 = arrayBufferToBase64(next)
          ws.send(JSON.stringify({ type: 'audio_chunk', data_base64: b64 }))
        } catch (e) {
          console.error('WS error: base64 encode failed', e)
        }
      } else {
        ws.send(next)
      }
    }
  }, [sendMode])

  // Asegurar apertura del WS antes de continuar
  const ensureWsOpen = useCallback(async () => {
    const current = wsRef.current
    if (current && current.readyState === WebSocket.OPEN) return
    await connect()
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) return
    await new Promise<void>((resolve) => {
      const handler: EventListener = () => {
        try { ws?.removeEventListener('open', handler) } catch (err) { console.debug('WS removeEventListener error', err) }
        resolve()
      }
      ws?.addEventListener('open', handler)
    })
  }, [])

  const connect = useCallback(async () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return
    const ws = new WebSocket(voiceWsUrl)

    ws.onopen = async () => {
      setConnected(true)
      const ctx = new AudioContext()
      audioContextRef.current = ctx
      // Heartbeat solo cuando STT está activo
      heartbeatRef.current = window.setInterval(() => {
        const ws = wsRef.current
        if (ws && ws.readyState === WebSocket.OPEN && sttStartedRef.current) {
          const ts = Date.now()
          ws.send(JSON.stringify({ type: 'ping', ts }))
        }
      }, 15000)
    }

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as WsMsg
        switch (data.type) {
          case 'pong': {
            const d = data as Pong
            if (d.ts && d.server_ts) {
              const rtt = Date.now() - d.ts
              setLatencyMs(rtt)
            }
            break
          }
          case 'ack': {
            awaitAckRef.current = false
            setWaitingAck(false)
            setQueueSize(queueRef.current.length)
            maybeSendNext()
            break
          }
          case 'partial': {
            const t = (data as PartialMsg).text || ''
            onPartialText?.(t)
            break
          }
          case 'final': {
            const t = (data as FinalMsg).text || ''
            onFinalText?.(t)
            setRecording(false)
            sttStartedRef.current = false
            cleanupAudio()
            break
          }
          case 'error': {
            console.error('WS error:', (data as ErrMsg).message)
            break
          }
          default:
            break
        }
      } catch {
        // mensajes binarios ignorados
      }
    }

    ws.onclose = () => {
      setConnected(false)
      setRecording(false)
      cleanupAudio()
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current)
        heartbeatRef.current = null
      }
      awaitAckRef.current = false
      queueRef.current = []
      setQueueSize(0)
      setWaitingAck(false)
    }

    ws.onerror = (err) => {
      console.error('WS error:', err)
    }

    wsRef.current = ws
  }, [cleanupAudio, maybeSendNext, voiceWsUrl, onFinalText, onPartialText])

  const startRecording = useCallback(async () => {
    await ensureWsOpen()
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WS no conectado')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const ctx = audioContextRef.current || new AudioContext()
      audioContextRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)

      const processor = ctx.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      // Inicializar estado de silencio
      voiceDetectedRef.current = false
      lastVoiceTsRef.current = Date.now()
      autoStopSentRef.current = false

      processor.onaudioprocess = (e) => {
        const inputBuffer = e.inputBuffer
        const channelData = inputBuffer.getChannelData(0)
        const TARGET_SR = 16000
        const downsampled = resampleFloat32ToRate(channelData, ctx.sampleRate, TARGET_SR)
        const pcm = floatTo16BitPCM(downsampled)
        queueRef.current.push(pcm)
        setQueueSize(queueRef.current.length)
        maybeSendNext()

        // Calcular RMS y auto-parar por silencio prolongado
        if (autoStopOnSilence) {
          let sumSq = 0
          for (let i = 0; i < downsampled.length; i++) {
            const v = downsampled[i]
            sumSq += v * v
          }
          const rms = Math.sqrt(sumSq / Math.max(1, downsampled.length))
          const now = Date.now()
          if (rms >= silenceRms) {
            voiceDetectedRef.current = true
            lastVoiceTsRef.current = now
          } else if (voiceDetectedRef.current && !autoStopSentRef.current && (now - lastVoiceTsRef.current) >= silenceMs) {
            autoStopSentRef.current = true
            try {
              wsRef.current?.send(JSON.stringify({ type: 'stt_end' }))
            } catch (err) {
              console.debug('WS stt_end send error', err)
            }
            cleanupAudio()
            setRecording(false)
            sttStartedRef.current = false
            awaitAckRef.current = false
            queueRef.current = []
            setQueueSize(0)
            setWaitingAck(false)
            return
          }
        }
      }

      wsRef.current!.send(JSON.stringify({
        type: 'stt_start',
        sample_rate: 16000,
        use_vad: useVAD,
        vad_level: vadLevel,
        frame_ms: frameMs,
      }))

      const sourceNode = source
      const processorNode = processor
      sourceNode.connect(processorNode)
      processorNode.connect(ctx.destination)

      sttStartedRef.current = true
      setRecording(true)
    } catch (err) {
      console.error('Error iniciando grabación:', err)
    }
  }, [ensureWsOpen, frameMs, useVAD, vadLevel, maybeSendNext, autoStopOnSilence, silenceMs, silenceRms, cleanupAudio])

  const stopRecording = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      cleanupAudio()
      setRecording(false)
      return
    }
    try {
      wsRef.current.send(JSON.stringify({ type: 'stt_end' }))
    } catch (err) {
      console.debug('WS stt_end send error', err)
    }

    cleanupAudio()
    setRecording(false)
    sttStartedRef.current = false
    awaitAckRef.current = false
    queueRef.current = []
    setQueueSize(0)
    setWaitingAck(false)
  }, [cleanupAudio])

  const toggleRecording = useCallback(async () => {
    if (!recording) {
      await startRecording()
    } else {
      stopRecording()
    }
  }, [recording, startRecording, stopRecording])

  useEffect(() => {
    return () => {
      try { wsRef.current?.close() } catch (err) { console.debug('WS close error', err) }
      cleanupAudio()
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current)
        heartbeatRef.current = null
      }
    }
  }, [cleanupAudio])

  return (
    <button
      onClick={toggleRecording}
      className={`flex items-center space-x-2 px-3 py-2 rounded-md border ${recording ? 'bg-red-600 text-white border-red-700' : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-100 border-gray-300 dark:border-gray-600'} ${className}`}
      title={recording ? 'Detener grabación' : 'Grabar voz'}
    >
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d={recording ? 'M12 3v10m0 0a4 4 0 004-4m-4 4a4 4 0 01-4-4m8 10H8' : 'M12 1a3 3 0 013 3v7a3 3 0 11-6 0V4a3 3 0 013-3zm0 14a7 7 0 007-7h-2a5 5 0 01-10 0H5a7 7 0 007 7zm-4 2h8v2H8v-2z'}
        />
      </svg>
      <span>{recording ? 'Grabando…' : 'Mic'}</span>
      {connected && (
        <span className="ml-2 text-xs opacity-70">
          {waitingAck ? '↗︎ enviando…' : `cola: ${queueSize}${latencyMs ? ` • ${latencyMs}ms` : ''}`}
        </span>
      )}
    </button>
  )
}

export default MicButton