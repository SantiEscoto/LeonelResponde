#!/usr/bin/env python3
"""
WebSocket STT demo client for LeonelResponde
- Connects to ws://HOST:PORT/ws/stt
- Streams a WAV file in chunks and prints partial/final results
"""
import argparse
import asyncio
import json
import base64
import wave
import sys
import websockets

async def receiver(ws):
    """Receive and print STT partial/final results."""
    final_text = None
    while True:
        msg = await ws.recv()
        try:
            data = json.loads(msg)
        except Exception:
            continue
        t = data.get("type")
        if t == "error":
            raise RuntimeError(data.get("message", "unknown error"))
        elif t == "partial":
            txt = data.get("text", "")
            if txt:
                print(f"[partial] {txt}")
        elif t == "final":
            final_text = data.get("text", "")
            conf = data.get("confidence", 0.0)
            print(f"[final] {final_text} (conf={conf})")
            break
    return final_text

async def run(host: str, port: int, input_wav: str, chunk_frames: int, binary: bool, use_vad: bool, vad_level: int, frame_ms: int):
    uri = f"ws://{host}:{port}/ws/stt"
    async with websockets.connect(uri) as ws:
        # Open WAV file
        try:
            wf = wave.open(input_wav, "rb")
        except FileNotFoundError:
            print(f"Input file not found: {input_wav}")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to open WAV: {e}")
            sys.exit(1)

        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()

        if channels != 1:
            print(f"Warning: WAV has {channels} channels; mono (1) recommended.")
        if sample_width != 2:
            print(f"Warning: WAV sample width is {sample_width*8} bits; 16-bit PCM recommended.")
        if sample_rate not in (8000, 16000, 22050, 44100, 48000):
            print(f"Warning: WAV sample rate {sample_rate} Hz; recognition optimal at 16 kHz.")

        # Start STT session (with optional VAD controls)
        await ws.send(json.dumps({
            "type": "stt_start",
            "sample_rate": sample_rate,
            "use_vad": use_vad,
            "vad_level": vad_level,
            "frame_ms": frame_ms,
        }))

        # Start receiver in background
        recv_task = asyncio.create_task(receiver(ws))

        # Send audio chunks
        while True:
            frames = wf.readframes(chunk_frames)
            if len(frames) == 0:
                break
            if binary:
                await ws.send(frames)
            else:
                b64 = base64.b64encode(frames).decode("ascii")
                await ws.send(json.dumps({"type": "audio_chunk", "data_base64": b64}))

        # Signal end
        await ws.send(json.dumps({"type": "stt_end"}))

        # Wait for final result
        final_text = await recv_task
        print(f"Transcription done: {final_text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--input", default="Assistant/data/voice_samples/ws_tts_16k.wav")
    parser.add_argument("--chunk", type=int, default=4096, help="Frames per chunk (default 4096)")
    parser.add_argument("--binary", action="store_true", help="Send audio chunks as binary (PCM 16-bit mono)")
    parser.add_argument("--use-vad", action="store_true", help="Enable server-side VAD gating (defaults to disabled if not set)")
    parser.add_argument("--vad-level", type=int, default=2, help="VAD aggressiveness 0-3 (default 2)")
    parser.add_argument("--frame-ms", type=int, default=30, help="Frame duration for VAD in ms (default 30)")
    args = parser.parse_args()
    asyncio.run(run(args.host, args.port, args.input, args.chunk, args.binary, args.use_vad, args.vad_level, args.frame_ms))