#!/usr/bin/env python3
"""
WebSocket TTS demo client for LeonelResponde
- Connects to ws://HOST:PORT/ws/tts
- Sends text and saves received audio chunks to a WAV file
"""
import argparse
import asyncio
import json
import base64
import websockets

async def run(host: str, port: int, text: str, output: str, ping_interval: int = 60, ping_timeout: int = 600):
    uri = f"ws://{host}:{port}/ws/tts"
    async with websockets.connect(uri, ping_interval=ping_interval, ping_timeout=ping_timeout) as ws:
        await ws.send(json.dumps({"type": "tts_request", "text": text}))

        audio_bytes = bytearray()
        provider = None
        sample_rate = 22050
        fmt = "wav"

        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            t = data.get("type")

            if t == "error":
                raise RuntimeError(data.get("message", "unknown error"))
            elif t == "tts_start":
                print("[server] tts_start")
            elif t == "audio_chunk":
                b64 = data.get("data_base64")
                if b64:
                    audio_bytes.extend(base64.b64decode(b64))
            elif t == "tts_end":
                provider = data.get("provider")
                fmt = data.get("format", fmt)
                sample_rate = int(data.get("sample_rate", sample_rate))
                break

        # Write WAV file
        with open(output, "wb") as f:
            f.write(audio_bytes)
        print(f"Saved {fmt} ({sample_rate} Hz) from provider={provider} to {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", default="ws_tts.wav")
    parser.add_argument("--ping-interval", type=int, default=60)
    parser.add_argument("--ping-timeout", type=int, default=600)
    args = parser.parse_args()
    asyncio.run(run(args.host, args.port, args.text, args.output, args.ping_interval, args.ping_timeout))