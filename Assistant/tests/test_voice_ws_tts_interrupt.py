import asyncio
import json
import base64
import io
import wave
import sys
from pathlib import Path

import pytest

# Ensure repo root and Assistant are importable
REPO_ROOT = Path(__file__).resolve().parents[2]
ASSISTANT_DIR = REPO_ROOT / "Assistant"
if str(ASSISTANT_DIR) not in sys.path:
    sys.path.insert(0, str(ASSISTANT_DIR))


def _make_silence_wav(duration_sec: float = 0.5, sample_rate: int = 22050) -> bytes:
    num_samples = int(duration_sec * sample_rate)
    # 16-bit mono silence
    pcm = b"\x00\x00" * num_samples
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_tts_interruption_ws():
    """Validate that /ws/tts supports dynamic interruption via stop_tts."""
    import websockets
    from Assistant.src.mcp_servers import voice_ws_server as vws

    host = "127.0.0.1"
    port = 8030

    # Monkeypatch tts_generate to avoid heavy dependencies and ensure deterministic output
    wav_bytes = _make_silence_wav(duration_sec=1.0)
    audio_b64 = base64.b64encode(wav_bytes).decode("ascii")
    original_tts = vws.voice.tts_generate
    vws.voice.tts_generate = lambda text, provider=None, language="es": {
        "success": True,
        "format": "wav",
        "sample_rate": 22050,
        "audio_base64": audio_b64,
        "provider": (provider or "pyttsx3"),
    }

    # Start WS server using the module router
    server = await websockets.serve(vws.router, host, port, ping_interval=60, ping_timeout=600)

    try:
        async with websockets.connect(f"ws://{host}:{port}/ws/tts") as ws:
            # Send TTS request
            await ws.send(json.dumps({
                "type": "tts_request",
                "text": "Hola mundo",
                "provider": "pyttsx3",
                "language": "es",
            }))

            # Expect start
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            data = json.loads(msg)
            assert data.get("type") == "tts_start"

            # Receive at least one audio chunk
            got_chunk = False
            for _ in range(5):
                msg2 = await asyncio.wait_for(ws.recv(), timeout=3)
                d2 = json.loads(msg2)
                if d2.get("type") == "audio_chunk":
                    got_chunk = True
                    break
            assert got_chunk, "Expected at least one audio_chunk before interruption"

            # Send interruption
            await ws.send(json.dumps({"type": "stop_tts"}))

            # Expect interruption event
            interrupted = False
            for _ in range(10):
                try:
                    msg3 = await asyncio.wait_for(ws.recv(), timeout=3)
                except asyncio.TimeoutError:
                    break
                d3 = json.loads(msg3)
                if d3.get("type") == "tts_interrupted":
                    interrupted = True
                    break
                # If tts_end arrives before interrupted, treat as failure for this test
                if d3.get("type") == "tts_end":
                    break

            assert interrupted, "Expected tts_interrupted after stop_tts"
    finally:
        # Restore and shutdown server
        vws.voice.tts_generate = original_tts
        server.close()
        await server.wait_closed()