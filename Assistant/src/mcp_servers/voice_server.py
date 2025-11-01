#!/usr/bin/env python3
"""
LeonelResponde Voice Server (Simplified)
Provides voice processing capabilities without MCP dependencies
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
from pathlib import Path
import queue
import tempfile
from typing import Any, Dict, List
import wave
import base64

# Try to import voice processing libraries (optional)
try:
    import numpy as np
    import sounddevice as sd

    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logging.warning("Audio libraries not available. Voice features disabled.")

try:
    import vosk

    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False
    logging.warning("Vosk not available. STT features disabled.")

# TTS engines (optional)
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logging.warning("pyttsx3 not available. Basic TTS disabled.")

try:
    from TTS.api import TTS as CoquiTTS
    COQUI_AVAILABLE = True
except Exception as e:
    COQUI_AVAILABLE = False
    logging.warning(f"Coqui TTS not available. XTTS disabled. ({e})")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceServer:
    """
    Simplified Voice Server for LeonelResponde
    """

    def __init__(self, model_path: str = None):
        self.model_path = model_path or "./models/voice/vosk-model-es-0.42"
        self.vosk_model = None
        self.sample_rate = 16000
        self.channels = 1
        self.recording = False
        self.audio_buffer = []
        self.logger = logging.getLogger(__name__)

        # Voice processing components
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.recording_thread = None
        self.chunk_size = 1024
        # Cache Coqui TTS engine to avoid repeated heavy initialization
        self.coqui_tts = None
        # Cache de muestra speaker_wav para XTTS (evitar generarlo en cada petición)
        self.speaker_wav_cached_path = None

        # Initialize Vosk model
        self._initialize_vosk()

    def _initialize_vosk(self):
        """Initialize Vosk speech recognition model"""
        if not STT_AVAILABLE:
            self.logger.warning("STT not available")
            return

        try:
            if Path(self.model_path).exists():
                self.vosk_model = vosk.Model(self.model_path)
                self.logger.info(f"Vosk model loaded from: {self.model_path}")
            else:
                self.logger.warning(f"Vosk model not found at: {self.model_path}")
                # Try to use a smaller model or download one
                self.logger.info("Consider downloading a Vosk model for Spanish")
        except Exception as e:
            self.logger.error(f"Failed to initialize Vosk model: {e}")

    def list_audio_devices(self) -> List[Dict[str, Any]]:
        """List available audio input devices"""
        if not AUDIO_AVAILABLE:
            return []

        try:
            devices = sd.query_devices()
            audio_devices = []

            for i, device in enumerate(devices):
                if device["max_input_channels"] > 0:  # Input device
                    audio_devices.append(
                        {
                            "id": i,
                            "name": device["name"],
                            "channels": device["max_input_channels"],
                            "sample_rate": device["default_samplerate"],
                        }
                    )

            return audio_devices
        except Exception as e:
            self.logger.error(f"Failed to list audio devices: {e}")
            return []

    def record_audio(self, duration: float = 5.0, device_id: int = None) -> str:
        """Record audio from microphone"""
        if not AUDIO_AVAILABLE:
            return ""

        try:
            self.logger.info(f"Recording audio for {duration} seconds...")

            # Record audio
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                device=device_id,
                dtype=np.int16,
            )
            sd.wait()  # Wait for recording to complete

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # Write WAV file
            with wave.open(temp_path, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data.tobytes())

            self.logger.info(f"Audio recorded and saved to: {temp_path}")
            return temp_path

        except Exception as e:
            self.logger.error(f"Failed to record audio: {e}")
            return ""

    def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file to text using Vosk"""
        if not STT_AVAILABLE or not self.vosk_model:
            return {
                "success": False,
                "error": "Vosk model not initialized",
                "text": "",
                "confidence": 0.0,
            }

        try:
            # Create recognizer
            rec = vosk.KaldiRecognizer(self.vosk_model, self.sample_rate)
            rec.SetWords(True)

            # Read audio file
            with wave.open(audio_file_path, "rb") as wav_file:
                # Check audio format
                if (
                    wav_file.getnchannels() != 1
                    or wav_file.getsampwidth() != 2
                    or wav_file.getframerate() != self.sample_rate
                ):
                    self.logger.warning("Audio format may not be optimal for recognition")

                results = []
                while True:
                    data = wav_file.readframes(4000)
                    if len(data) == 0:
                        break

                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        if result.get("text"):
                            results.append(result)

                # Get final result
                final_result = json.loads(rec.FinalResult())
                if final_result.get("text"):
                    results.append(final_result)

            # Combine all text results
            full_text = " ".join([r.get("text", "") for r in results]).strip()

            # Calculate average confidence
            confidences = [r.get("confidence", 0.0) for r in results if "confidence" in r]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Clean up temporary file
            try:
                os.unlink(audio_file_path)
            except Exception:
                # Ignore cleanup errors (file may already be removed or locked)
                pass

            return {
                "success": True,
                "text": full_text,
                "confidence": avg_confidence,
                "results": results,
            }

        except Exception as e:
            self.logger.error(f"Failed to transcribe audio: {e}")
            return {"success": False, "error": str(e), "text": "", "confidence": 0.0}

    def record_and_transcribe(self, duration: float = 5.0, device_id: int = None) -> Dict[str, Any]:
        """Record audio and transcribe it in one operation"""
        audio_file = self.record_audio(duration, device_id)
        if not audio_file:
            return {
                "success": False,
                "error": "Failed to record audio",
                "text": "",
                "confidence": 0.0,
            }

        return self.transcribe_audio(audio_file)

    def get_audio_info(self) -> Dict[str, Any]:
        """Get information about audio system"""
        try:
            return {
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "vosk_model_loaded": self.vosk_model is not None,
                "model_path": self.model_path,
                "audio_available": AUDIO_AVAILABLE,
                "stt_available": STT_AVAILABLE,
                "devices": self.list_audio_devices(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get audio info: {e}")
            return {"error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        """Get current voice processing status"""
        return {
            "status": "active" if self.is_recording else "idle",
            "stt_available": self.vosk_model is not None,
            "audio_available": AUDIO_AVAILABLE,
            "audio_devices": self.list_audio_devices() if AUDIO_AVAILABLE else [],
        }

    def get_health(self) -> Dict[str, Any]:
        """Comprehensive health check for the voice server"""
        try:
            return {
                "ok": (AUDIO_AVAILABLE or STT_AVAILABLE or COQUI_AVAILABLE or PYTTSX3_AVAILABLE),
                "audio_available": AUDIO_AVAILABLE,
                "stt_available": STT_AVAILABLE,
                "vosk_model_loaded": self.vosk_model is not None,
                "tts_available": COQUI_AVAILABLE or PYTTSX3_AVAILABLE,
                "coqui_available": COQUI_AVAILABLE,
                "pyttsx3_available": PYTTSX3_AVAILABLE,
                "sample_rate": self.sample_rate,
                "channels": self.channels,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def tts_generate(self, text: str, provider: str = None, language: str = "es") -> Dict[str, Any]:
        """Generate speech audio from text.
        - provider: "coqui" | "pyttsx3" | None (auto coqui->pyttsx3)
        - language: ISO language code (used by Coqui XTTS)
        Returns base64-encoded WAV bytes and provider info.
        """
        if not text or not isinstance(text, str):
            return {"success": False, "error": "text is required"}

        chosen_provider = (provider or "").strip().lower() if isinstance(provider, str) else None
        disable_coqui = os.getenv("DISABLE_COQUI", "0") == "1"

        # Helper: synth using pyttsx3
        def _tts_pyttsx3(say_text: str) -> Dict[str, Any]:
            if not PYTTSX3_AVAILABLE:
                return {"success": False, "error": "pyttsx3 not available"}
            try:
                engine = pyttsx3.init()
                try:
                    voices = engine.getProperty("voices") or []
                    chosen = None
                    for v in voices:
                        vid = getattr(v, "id", "") or ""
                        name = getattr(v, "name", "") or ""
                        langs = getattr(v, "languages", []) or []
                        if "es" in vid.lower() or "spanish" in name.lower() or any("es" in str(l).lower() for l in langs):
                            chosen = vid
                            break
                    if chosen:
                        engine.setProperty("voice", chosen)
                except Exception:
                    pass
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    path = temp_file.name
                engine.save_to_file(say_text, path)
                engine.runAndWait()
                with open(path, "rb") as f:
                    audio_bytes = f.read()
                try:
                    os.unlink(path)
                except Exception:
                    pass
                b64 = base64.b64encode(audio_bytes).decode("ascii")
                return {
                    "success": True,
                    "format": "wav",
                    "sample_rate": 22050,
                    "audio_base64": b64,
                    "provider": "pyttsx3",
                }
            except Exception as e:
                self.logger.error(f"pyttsx3 TTS failed: {e}")
                return {"success": False, "error": str(e)}

        # Helper: synth using Coqui XTTS
        def _tts_coqui(say_text: str) -> Dict[str, Any]:
            if not COQUI_AVAILABLE or disable_coqui:
                return {"success": False, "error": "coqui disabled or not available"}
            try:
                try:
                    import torch
                    from TTS.tts.configs.xtts_config import XttsConfig
                    from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
                    from TTS.config.shared_configs import BaseDatasetConfig
                    try:
                        torch.serialization.add_safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs])
                    except Exception:
                        pass
                except Exception:
                    pass

                if self.coqui_tts is None:
                    self.coqui_tts = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2")

                # Cache/reutilizar speaker_wav para evitar coste por solicitud
                speaker_wav_path = self.speaker_wav_cached_path
                if speaker_wav_path is None and PYTTSX3_AVAILABLE:
                    try:
                        engine = pyttsx3.init()
                        try:
                            voices = engine.getProperty("voices") or []
                            chosen = None
                            for v in voices:
                                vid = getattr(v, "id", "") or ""
                                name = getattr(v, "name", "") or ""
                                langs = getattr(v, "languages", []) or []
                                if "es" in vid.lower() or "spanish" in name.lower() or any("es" in str(l).lower() for l in langs):
                                    chosen = vid
                                    break
                            if chosen:
                                engine.setProperty("voice", chosen)
                        except Exception:
                            pass
                        # Crear una ruta persistente temporal
                        import tempfile as _tf
                        speaker_wav_path = os.path.join(_tf.gettempdir(), "leonel_xtts_speaker.wav")
                        engine.save_to_file("Muestra de voz para clonación.", speaker_wav_path)
                        engine.runAndWait()
                        self.speaker_wav_cached_path = speaker_wav_path
                    except Exception:
                        speaker_wav_path = None

                audio = self.coqui_tts.tts(text=say_text, language=language or "es", speaker_wav=speaker_wav_path)
                import soundfile as sf
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    sf.write(temp_file.name, audio, 22050)
                    path = temp_file.name
                with open(path, "rb") as f:
                    audio_bytes = f.read()
                try:
                    os.unlink(path)
                except Exception:
                    pass
                b64 = base64.b64encode(audio_bytes).decode("ascii")
                return {
                    "success": True,
                    "format": "wav",
                    "sample_rate": 22050,
                    "audio_base64": b64,
                    "provider": "coqui",
                }
            except Exception as e:
                self.logger.error(f"Coqui TTS failed: {e}")
                return {"success": False, "error": str(e)}

        # Selección de proveedor (pyttsx3 deshabilitado)
        if chosen_provider == "pyttsx3":
            return {"success": False, "error": "pyttsx3 disabled"}
        elif chosen_provider == "coqui":
            result = _tts_coqui(text)
            if result.get("success"):
                return result
            # Sin fallback a pyttsx3
            return result

        # Modo auto (por defecto): solo Coqui
        result = _tts_coqui(text)
        return result


# Initialize voice processor
voice_processor = VoiceServer()

# Simple HTTP server for voice operations


class VoiceHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for voice server requests"""

    def __init__(self, *args, voice_server=None, **kwargs):
        self.voice_server = voice_server or VoiceServer()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/status":
            self._send_json_response(self.voice_server.get_status())
        elif self.path == "/info":
            self._send_json_response(self.voice_server.get_audio_info())
        elif self.path == "/devices":
            devices = self.voice_server.list_audio_devices()
            self._send_json_response({"devices": devices, "count": len(devices)})
        elif self.path == "/health":
            self._send_json_response(self.voice_server.get_health())
        else:
            self._send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode("utf-8")) if post_data else {}
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON")
            return

        if self.path == "/record":
            duration = data.get("duration", 5.0)
            device_id = data.get("device_id")
            audio_file = self.voice_server.record_audio(duration, device_id)
            result = {
                "success": bool(audio_file),
                "audio_file_path": audio_file,
                "duration": duration,
                "device_id": device_id,
            }
            self._send_json_response(result)
        elif self.path == "/transcribe":
            audio_file_path = data.get("audio_file_path")
            if not audio_file_path:
                self._send_error(400, "audio_file_path is required")
                return
            result = self.voice_server.transcribe_audio(audio_file_path)
            self._send_json_response(result)
        elif self.path == "/record_and_transcribe":
            duration = data.get("duration", 5.0)
            device_id = data.get("device_id")
            result = self.voice_server.record_and_transcribe(duration, device_id)
            self._send_json_response(result)
        elif self.path == "/tts":
            text = data.get("text")
            result = self.voice_server.tts_generate(text)
            self._send_json_response(result)
        else:
            self._send_error(404, "Not Found")

    def _send_json_response(self, data):
        """Send JSON response"""
        response = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _send_error(self, code, message):
        """Send error response"""
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))


def main():
    """Main function to run the voice server"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create voice server
    voice_server = VoiceServer()

    # Create HTTP server
    host = os.getenv("VOICE_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("VOICE_SERVER_PORT", "8000"))

    def handler(*args, **kwargs):
        VoiceHTTPHandler(*args, voice_server=voice_server, **kwargs)

    server = HTTPServer((host, port), handler)

    print(f"Voice server starting on http://{host}:{port}")
    print("Available endpoints:")
    print("  GET  /status - Get server status")
    print("  GET  /info - Get audio system info")
    print("  GET  /devices - List audio devices")
    print("  GET  /health - Health check")
    print("  POST /record - Record audio")
    print("  POST /transcribe - Transcribe audio")
    print("  POST /record_and_transcribe - Record and transcribe")
    print("  POST /tts - Text-to-Speech (Coqui->pyttsx3 fallback)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        server.shutdown()


if __name__ == "__main__":
    main()
