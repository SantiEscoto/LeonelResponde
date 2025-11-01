import React, { useEffect, useRef, useState } from 'react'

function base64ToUint8Array(base64: string): Uint8Array {
  const binary_string = atob(base64)
  const len = binary_string.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i++) {
    bytes[i] = binary_string.charCodeAt(i)
  }
  return bytes
}

const TtsWsClient: React.FC = () => {
  const [host, setHost] = useState<string>('localhost')
  const [port, setPort] = useState<number>(8010)
  const [connected, setConnected] = useState<boolean>(false)
  const [speaking, setSpeaking] = useState<boolean>(false)
  const [text, setText] = useState<string>('Hola, este es un ejemplo de TTS en el frontend.')
  const [provider, setProvider] = useState<string>('')
  const [sampleRate, setSampleRate] = useState<number | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const chunksRef = useRef<Uint8Array[]>([])

  useEffect(() => {
    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
      if (audioUrl) URL.revokeObjectURL(audioUrl)
    }
  }, [audioUrl])

  const connect = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return
    const url = `ws://${host}:${port}/ws/tts`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const type = data.type
        if (type === 'pong') return
        if (type === 'tts_start') {
          chunksRef.current = []
        } else if (type === 'audio_chunk') {
          const chunkB64 = data.data_base64 // servidor usa data_base64
          if (chunkB64) {
            const bytes = base64ToUint8Array(chunkB64)
            chunksRef.current.push(bytes)
          }
        } else if (type === 'tts_end') {
          // proveedor y sample rate se informan aquí
          setProvider(data.provider || '')
          setSampleRate(data.sample_rate || null)
          finalizeAudio()
          setSpeaking(false)
        } else if (type === 'error') {
          console.error('TTS error:', data.message)
          setSpeaking(false)
        }
      } catch (e) {
        console.warn('Mensaje no JSON en TTS:', e)
      }
    }

    ws.onclose = () => {
      setConnected(false)
    }

    ws.onerror = (err) => {
      console.error('WebSocket TTS error:', err)
    }
  }

  const disconnect = () => {
    if (wsRef.current) wsRef.current.close()
    setConnected(false)
  }

  const speak = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) connect()
    if (!wsRef.current) return
    setSpeaking(true)
    chunksRef.current = []
    wsRef.current.send(JSON.stringify({ type: 'tts_request', text }))
  }

  const finalizeAudio = () => {
    const totalLength = chunksRef.current.reduce((sum, arr) => sum + arr.length, 0)
    if (totalLength === 0) {
      console.warn('No se recibieron chunks de audio TTS')
      return
    }
    const merged = new Uint8Array(totalLength)
    let offset = 0
    for (const arr of chunksRef.current) {
      merged.set(arr, offset)
      offset += arr.length
    }
    const blob = new Blob([merged], { type: 'audio/wav' })
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    const url = URL.createObjectURL(blob)
    setAudioUrl(url)
  }

  return (
    <div style={{ border: '1px solid #333', borderRadius: 8, padding: 12, marginTop: 12 }}>
      <h3>TTS WebSocket</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <label>
          Host
          <input value={host} onChange={(e) => setHost(e.target.value)} style={{ marginLeft: 6 }} />
        </label>
        <label>
          Port
          <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} style={{ marginLeft: 6, width: 90 }} />
        </label>
        {connected ? (
          <button onClick={disconnect}>Desconectar</button>
        ) : (
          <button onClick={connect}>Conectar</button>
        )}
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        style={{ width: '100%', marginBottom: 8 }}
        placeholder="Texto para convertir a voz"
      />
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button onClick={speak} disabled={!connected || speaking}>Hablar</button>
        <span style={{ fontSize: 12, color: '#666' }}>
          {speaking ? 'Generando audio...' : connected ? 'Conectado' : 'Desconectado'}
        </span>
      </div>
      <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
        Proveedor: {provider || '—'} | Sample Rate: {sampleRate ?? '—'}
      </div>
      {audioUrl && (
        <audio src={audioUrl} controls style={{ marginTop: 8, width: '100%' }} />
      )}
    </div>
  )
}

export default TtsWsClient