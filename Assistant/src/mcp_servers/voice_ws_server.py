#!/usr/bin/env python3
"""
LeonelResponde Voice WebSocket Server (Preparation for Streaming)
- /ws/tts: Text-to-Speech, sends start, audio_chunk(s), end
- /ws/stt: Speech-to-Text, receives base64 audio chunks, emits partial/final
"""
import asyncio
import json
import os
import base64
import logging
from typing import Dict, Any

import websockets
import webrtcvad
import time

# Reuse core voice functionality
from Assistant.src.mcp_servers.voice_server import VoiceServer, STT_AVAILABLE

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("voice_ws_server")

# Allow overriding Vosk model path via env var
DEFAULT_VOSK_MODEL_PATH = "./models/voice/vosk-model-es-0.42"
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", DEFAULT_VOSK_MODEL_PATH)
voice = VoiceServer(model_path=VOSK_MODEL_PATH)


def _chunk_bytes(data: bytes, size: int = 8 * 1024):
    for i in range(0, len(data), size):
        yield data[i : i + size]


def _has_voice(vad: webrtcvad.Vad, pcm_bytes: bytes, sample_rate: int, frame_ms: int = 30) -> bool:
    # Simple VAD gating over 30ms frames on 16-bit mono PCM
    if not pcm_bytes:
        return False
    try:
        frame_len = int(sample_rate * (frame_ms / 1000.0)) * 2  # bytes for 16-bit mono
        voiced = 0
        total = 0
        for i in range(0, len(pcm_bytes) - frame_len + 1, frame_len):
            frame = pcm_bytes[i:i+frame_len]
            if len(frame) < frame_len:
                break
            total += 1
            if vad.is_speech(frame, sample_rate):
                voiced += 1
        return voiced > 0 and total > 0
    except Exception:
        return True  # if any error, don't block


import time
try:
    from Assistant.src.backend.utils.metrics_collector import (
        get_metrics_collector,
        MetricType,
        MetricCategory,
    )
    METRICS_AVAILABLE = True
    metrics = get_metrics_collector()
    # Registrar métricas de voz si no existen
    metrics.register_metric(
        name="voice.tts.latency_first_chunk_ms",
        metric_type=MetricType.HISTOGRAM,
        category=MetricCategory.CUSTOM,
        description="Latency from tts_start to first audio_chunk",
        unit="ms",
    )
    metrics.register_metric(
        name="voice.tts.total_time_ms",
        metric_type=MetricType.HISTOGRAM,
        category=MetricCategory.CUSTOM,
        description="Total time from tts_start to tts_end/interrupted",
        unit="ms",
    )
except Exception:
    METRICS_AVAILABLE = False
    metrics = None


async def handle_tts(websocket):
    """Handle TTS requests over WebSocket.
    Protocol:
      Client -> {"type":"tts_request", "text":"...", "provider":"pyttsx3|coqui", "language":"es"}
                (optional) send {"type":"stop_tts"} at any time to interrupt
      Server -> {"type":"tts_start"}
               {"type":"audio_chunk", "seq":N, "data_base64":"..."}*
               {"type":"tts_end", "provider":"coqui|pyttsx3", "format":"wav", "sample_rate":22050}
               or {"type":"tts_interrupted"} if interrupted
      On error -> {"type":"error", "message":"..."}
    """
    try:
        # Initial request with text and options
        msg = await websocket.recv()
        req = json.loads(msg)
        text = req.get("text")
        provider = req.get("provider")
        language = req.get("language") or "es"
        if not text:
            await websocket.send(json.dumps({"type": "error", "message": "text is required"}))
            return

        await websocket.send(json.dumps({"type": "tts_start"}))
        t_start = time.time()
        first_chunk_ms = None

        result = voice.tts_generate(text, provider=provider, language=language)
        if not result.get("success"):
            await websocket.send(json.dumps({"type": "error", "message": result.get("error", "tts failed")}))
            return

        audio_b64 = result["audio_base64"]
        audio_bytes = base64.b64decode(audio_b64)

        interrupt_event = asyncio.Event()

        async def control_listener():
            # Listen for control messages to interrupt
            while True:
                try:
                    ctrl_msg = await websocket.recv()
                except Exception:
                    break
                if isinstance(ctrl_msg, str):
                    try:
                        ctrl = json.loads(ctrl_msg)
                    except Exception:
                        continue
                    if isinstance(ctrl, dict) and ctrl.get("type") == "stop_tts":
                        interrupt_event.set()
                        break

        async def stream_audio():
            nonlocal first_chunk_ms
            seq = 0
            for chunk in _chunk_bytes(audio_bytes):
                if interrupt_event.is_set():
                    # Interrumpir inmediatamente si se solicitó
                    return
                chunk_b64 = base64.b64encode(chunk).decode("ascii")
                await websocket.send(json.dumps({
                    "type": "audio_chunk",
                    "seq": seq,
                    "data_base64": chunk_b64,
                }))
                if first_chunk_ms is None:
                    first_chunk_ms = (time.time() - t_start) * 1000.0
                    if METRICS_AVAILABLE:
                        metrics.record(
                            "voice.tts.latency_first_chunk_ms",
                            first_chunk_ms,
                            labels={"provider": str(result.get("provider"))}
                        )
                seq += 1
                # Ceder control al loop para procesar mensajes de control (stop_tts)
                await asyncio.sleep(0)

        stream_task = asyncio.create_task(stream_audio())
        control_task = asyncio.create_task(control_listener())

        # Esperar a que termine el streaming
        await stream_task
        # Pequeña ventana para capturar interrupciones que lleguen al final del streaming
        await asyncio.sleep(0.05)
        interrupted = interrupt_event.is_set()
        total_ms = (time.time() - t_start) * 1000.0
        if METRICS_AVAILABLE:
            metrics.record(
                "voice.tts.total_time_ms",
                total_ms,
                labels={
                    "provider": str(result.get("provider")),
                    "interrupted": "true" if interrupted else "false",
                }
            )
        if interrupted:
            await websocket.send(json.dumps({"type": "tts_interrupted"}))
        else:
            await websocket.send(json.dumps({
                "type": "tts_end",
                "provider": result.get("provider"),
                "format": result.get("format", "wav"),
                "sample_rate": result.get("sample_rate", 22050),
            }))

        # Cancelar el listener de control si sigue activo
        if not control_task.done():
            control_task.cancel()

        done, pending = await asyncio.wait({stream_task, control_task}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
    except Exception as e:
        logger.error(f"TTS handler error: {e}")
        await websocket.send(json.dumps({"type": "error", "message": str(e)}))


async def handle_stt(websocket):
    """Handle STT streaming over WebSocket using Vosk.
    Protocol:
      Client -> {"type":"stt_start", "sample_rate":16000}
                {"type":"audio_chunk", "data_base64":"..."}*
                {"type":"stt_end"}
      (binary supported) -> send raw PCM 16-bit mono bytes after stt_start
      Server -> {"type":"partial", "text":"..."}*
                {"type":"final", "text":"...", "confidence":float}
                {"type":"ack", "seq":N, "accepted":bool}
      On error -> {"type":"error", "message":"..."}
    """
    if not (STT_AVAILABLE and voice.vosk_model):
        await websocket.send(json.dumps({"type": "error", "message": "STT not available"}))
        return

    import vosk

    try:
        # Wait for start message
        start_msg = await websocket.recv()
        start = json.loads(start_msg) if isinstance(start_msg, str) else {}
        if start.get("type") != "stt_start":
            await websocket.send(json.dumps({"type": "error", "message": "stt_start required first"}))
            return

        sample_rate = int(start.get("sample_rate", voice.sample_rate))
        use_vad = bool(start.get("use_vad", True))
        frame_ms = int(start.get("frame_ms", 30))
        vad = webrtcvad.Vad(int(start.get("vad_level", 2)))  # 0-3 (aggressive)

        rec = vosk.KaldiRecognizer(voice.vosk_model, sample_rate)
        rec.SetWords(True)

        recv_count = 0

        # Receive audio chunks until stt_end
        while True:
            msg = await websocket.recv()
            # End signal can only be structured JSON
            if isinstance(msg, str):
                try:
                    data = json.loads(msg)
                except Exception:
                    data = None
                if isinstance(data, dict) and data.get("type") == "stt_end":
                    final = json.loads(rec.FinalResult())
                    await websocket.send(json.dumps({
                        "type": "final",
                        "text": final.get("text", ""),
                        "confidence": final.get("confidence", 0.0),
                    }))
                    break
                # JSON audio chunk path
                if isinstance(data, dict) and data.get("type") == "audio_chunk":
                    audio_b64 = data.get("data_base64")
                    if not audio_b64:
                        continue
                    audio_bytes = base64.b64decode(audio_b64)
                elif isinstance(data, dict) and data.get("type") == "ping":
                    await websocket.send(json.dumps({
                        "type": "pong",
                        "ts": data.get("ts"),
                        "server_ts": int(time.time() * 1000)
                    }))
                    continue
                else:
                    # Unknown message type, ignore
                    continue
            else:
                # Binary audio path
                audio_bytes = msg

            accepted = True
            # Optional VAD gating
            if use_vad and not _has_voice(vad, audio_bytes, sample_rate, frame_ms):
                accepted = False
                recv_count += 1
                await websocket.send(json.dumps({"type": "ack", "seq": recv_count, "accepted": False}))
                continue

            # Feed recognizer
            if rec.AcceptWaveform(audio_bytes):
                res = json.loads(rec.Result())
                await websocket.send(json.dumps({"type": "partial", "text": res.get("text", "")}))
            else:
                pres = json.loads(rec.PartialResult())
                if pres.get("partial"):
                    await websocket.send(json.dumps({"type": "partial", "text": pres.get("partial", "")}))

            recv_count += 1
            await websocket.send(json.dumps({"type": "ack", "seq": recv_count, "accepted": True}))

    except Exception as e:
        logger.error(f"STT handler error: {e}")
        await websocket.send(json.dumps({"type": "error", "message": str(e)}))


async def router(websocket, path):
    if path == "/ws/tts":
        await handle_tts(websocket)
    elif path == "/ws/stt":
        await handle_stt(websocket)
    else:
        await websocket.send(json.dumps({"type": "error", "message": f"unknown path: {path}"}))


async def main():
    host = os.getenv("VOICE_WS_HOST", "0.0.0.0")
    port = int(os.getenv("VOICE_WS_PORT", "8000"))

    logger.info(f"Voice WS server starting on ws://{host}:{port}")
    logger.info("Paths: /ws/tts, /ws/stt")

    async with websockets.serve(router, host, port, ping_interval=60, ping_timeout=600):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())