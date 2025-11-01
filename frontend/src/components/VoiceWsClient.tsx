import React, { useEffect, useRef, useState } from 'react'
import { useSendMessageMutation } from '../hooks/useChatMutation'

interface Pong {
  type: 'pong'
  ts?: number
  server_ts?: number
}

interface PartialMsg {
  type: 'partial'
  text: string
}

interface FinalMsg {
  type: 'final'
  text: string
  confidence?: number
}

interface AckMsg {
  type: 'ack'
  seq: number
  accepted: boolean
}

type WsMsg = Pong | PartialMsg | FinalMsg | AckMsg | { type: 'error'; message: string }

function floatTo16BitPCM(input: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(input.length * 2)
  const view = new DataView(buffer)
  let offset = 0
  for (let i = 0; i < input.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, input[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return buffer
}

function resampleFloat32ToRate(input: Float32Array, sourceRate: number, targetRate: number): Float32Array {
  if (sourceRate === targetRate) return input
  const ratio = sourceRate / targetRate
  const newLength = Math.round(input.length / ratio)
  const output = new Float32Array(newLength)
  for (let i = 0; i < newLength; i++) {
    const srcPos = i * ratio
    const idx0 = Math.floor(srcPos)
    const idx1 = Math.min(idx0 + 1, input.length - 1)
    const t = srcPos - idx0
    output[i] = input[idx0] + (input[idx1] - input[idx0]) * t
  }
  return output
}

const VoiceWsClient: React.FC = () => {
  const [host, setHost] = useState<string>('localhost')
  const [port, setPort] = useState<number>(8010)
  const [useVAD, setUseVAD] = useState<boolean>(true)
  const [vadLevel, setVadLevel] = useState<number>(2)
  const [frameMs, setFrameMs] = useState<number>(30)
  const [connected, setConnected] = useState<boolean>(false)
  const [recording, setRecording] = useState<boolean>(false)
  const [sampleRate, setSampleRate] = useState<number>(0)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [partialText, setPartialText] = useState<string>('')
  const [finalText, setFinalText] = useState<string>('')
  const [queueSize, setQueueSize] = useState<number>(0)
  const [waitingAck, setWaitingAck] = useState<boolean>(false)

  const { mutate: sendMessage } = useSendMessageMutation()

  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const heartbeatRef = useRef<number | null>(null)
  const awaitAckRef = useRef<boolean>(false)
  const queueRef = useRef<ArrayBuffer[]>([])
  const sttStartedRef = useRef<boolean>(false)

  const maybeSendNext = () => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    if (!sttStartedRef.current) return
    if (awaitAckRef.current) return
    const next = queueRef.current.shift()
    if (next) {
      awaitAckRef.current = true
      setWaitingAck(true)
      setQueueSize(queueRef.current.length)
      ws.send(next)
    }
  }

  // Conectar al servidor WS
  const connect = async () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return
    const url = `ws://${host}:${port}/ws/stt`
    const ws = new WebSocket(url)

    ws.onopen = async () => {
      setConnected(true)
      const ctx = new AudioContext()
      audioContextRef.current = ctx
      setSampleRate(ctx.sampleRate)
      // Enviar heartbeat solo después de iniciar STT
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
            if (data.ts && data.server_ts) {
              const rtt = Date.now() - data.ts
              setLatencyMs(rtt)
            }
            break
          }
          case 'ack': {
            awaitAckRef.current = false
            setWaitingAck(false)
            setQueueSize(queueRef.current.length)
            // Enviar el siguiente chunk si existe
            maybeSendNext()
            break
          }
          case 'partial': {
            setPartialText(data.text || '')
            break
          }
          case 'final': {
            const text = data.text || ''
            setFinalText(text)
            setRecording(false)
            sttStartedRef.current = false
            if (text.trim().length > 0) {
              sendMessage({ message: text })
            }
            break
          }
          case 'error': {
            console.error('WS error:', (data as { type: 'error'; message: string }).message)
            break
          }
          default:
            break
        }
      } catch {
        // Mensajes binarios ignorados
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
  }

  const disconnect = () => {
    if (wsRef.current) {
      try {
        wsRef.current.close()
      } catch {
        /* noop */
      }
      wsRef.current = null
    }
    awaitAckRef.current = false
    queueRef.current = []
    setQueueSize(0)
    setWaitingAck(false)
    cleanupAudio()
  }

  const startRecording = async () => {
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

      processor.onaudioprocess = (e) => {
        const inputBuffer = e.inputBuffer
        const channelData = inputBuffer.getChannelData(0)
        const TARGET_SR = 16000
        const downsampled = resampleFloat32ToRate(channelData, ctx.sampleRate, TARGET_SR)
        const pcm = floatTo16BitPCM(downsampled)
        queueRef.current.push(pcm)
        setQueueSize(queueRef.current.length)
        maybeSendNext()
      }

      wsRef.current!.send(JSON.stringify({
        type: 'stt_start',
        sample_rate: 16000,
        use_vad: useVAD,
        vad_level: vadLevel,
        frame_ms: frameMs,
      }))

      sttStartedRef.current = true
      source.connect(processor)
      processor.connect(ctx.destination)

      setRecording(true)
      setPartialText('')
      setFinalText('')
    } catch (err) {
      console.error('Error accediendo al micrófono:', err)
    }
  }

  const stopRecording = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'stt_end' }))
    setRecording(false)
    sttStartedRef.current = false
    cleanupAudio()
    awaitAckRef.current = false
    queueRef.current = []
    setQueueSize(0)
    setWaitingAck(false)
  }

  const cleanupAudio = () => {
    if (processorRef.current) {
      try { processorRef.current.disconnect() } catch {
        /* noop */
      }
      processorRef.current = null
    }
    if (audioContextRef.current) {
      try { audioContextRef.current.close() } catch {
        /* noop */
      }
      audioContextRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
  }

  useEffect(() => {
    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Prueba de Voz por WebSocket</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600 dark:text-gray-300">Host</label>
            <input className="border px-2 py-1 rounded" value={host} onChange={e => setHost(e.target.value)} />
            <label className="text-sm text-gray-600 dark:text-gray-300">Port</label>
            <input className="border px-2 py-1 rounded w-24" type="number" value={port} onChange={e => setPort(parseInt(e.target.value || '8000'))} />
            <button className="px-3 py-1 bg-blue-600 text-white rounded" onClick={connect} disabled={connected}>Conectar</button>
            <button className="px-3 py-1 bg-gray-600 text-white rounded" onClick={disconnect} disabled={!connected}>Desconectar</button>
          </div>
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600 dark:text-gray-300">VAD</label>
            <input type="checkbox" checked={useVAD} onChange={e => setUseVAD(e.target.checked)} />
            <label className="text-sm text-gray-600 dark:text-gray-300">Nivel</label>
            <input className="border px-2 py-1 rounded w-16" type="number" min={0} max={3} value={vadLevel} onChange={e => setVadLevel(parseInt(e.target.value || '2'))} />
            <label className="text-sm text-gray-600 dark:text-gray-300">Frame (ms)</label>
            <input className="border px-2 py-1 rounded w-20" type="number" value={frameMs} onChange={e => setFrameMs(parseInt(e.target.value || '30'))} />
          </div>
          <div className="flex items-center space-x-2">
            <button className="px-3 py-1 bg-green-600 text-white rounded" onClick={startRecording} disabled={!connected || recording}>Iniciar</button>
            <button className="px-3 py-1 bg-red-600 text-white rounded" onClick={stopRecording} disabled={!connected || !recording}>Detener</button>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-300">
            <div>Estado: {connected ? 'Conectado' : 'Desconectado'} | Grabando: {recording ? 'Sí' : 'No'}</div>
            <div>SampleRate: {sampleRate || '-'} Hz | Latencia (ping): {latencyMs !== null ? `${latencyMs} ms` : '-'}</div>
            <div>Backpressure: esperando ACK: {waitingAck ? 'Sí' : 'No'} | Cola: {queueSize}</div>
          </div>
        </div>
        <div className="space-y-2">
          <div>
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Parcial</div>
            <div className="border rounded p-2 text-sm bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200 min-h-[60px]">{partialText}</div>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">Final</div>
            <div className="border rounded p-2 text-sm bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200 min-h-[60px]">{finalText}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default VoiceWsClient