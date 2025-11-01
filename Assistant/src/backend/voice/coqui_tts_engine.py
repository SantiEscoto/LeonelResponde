"""
Coqui XTTS engine integration for high-quality TTS.
Optional engine used by PySide6 Web UI when the `TTS` package is available.
"""

from __future__ import annotations

import tempfile
import os
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread, QTimer, QUrl

try:
    # Import lazily to allow app to run without voice deps
    from TTS.api import TTS as CoquiTTS  # type: ignore
    COQUI_AVAILABLE = True
except Exception:
    COQUI_AVAILABLE = False


class CoquiSynthThread(QThread):
    """Background synthesis thread that produces a temporary WAV file."""

    synthesis_done = Signal(str, bool, str)  # (file_path, success, error)

    def __init__(self, tts: CoquiTTS, text: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.tts = tts
        self.text = text
        self.logger = logging.getLogger("CoquiSynthThread")

    def run(self):  # type: ignore[override]
        try:
            # Generate audio to a temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            self.tts.tts_to_file(text=self.text, file_path=tmp_path)
            self.synthesis_done.emit(tmp_path, True, "")
        except Exception as e:
            self.logger.error(f"Coqui synthesis error: {e}")
            self.synthesis_done.emit("", False, str(e))


class CoquiTTSEngine(QObject):
    """Minimal high-quality TTS engine wrapper using Coqui XTTS v2.

    Public API:
    - speak_async(text: str) -> None
    - is_available() -> bool
    - cleanup() -> None
    """

    synthesis_started = Signal(str)
    synthesis_completed = Signal(str)
    synthesis_error = Signal(str)
    engine_ready = Signal()

    def __init__(self, parent: Optional[QObject] = None, model: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        super().__init__(parent)
        self.logger = logging.getLogger("CoquiTTSEngine")
        self.tts: Optional[CoquiTTS] = None
        self.media_player = None
        self.audio_output = None
        self._init(model)

    def _init(self, model: str) -> None:
        if not COQUI_AVAILABLE:
            raise ImportError("Package 'TTS' (Coqui) no disponible")
        try:
            self.tts = CoquiTTS(model)
            self.engine_ready.emit()
            self.logger.info("Coqui XTTS v2 inicializado")
        except Exception as e:
            self.logger.error(f"Error inicializando Coqui XTTS: {e}")
            raise

    def is_available(self) -> bool:
        return self.tts is not None

    def speak_async(self, text: str) -> None:
        if not text or not text.strip():
            return
        if not self.tts:
            self.synthesis_error.emit("Coqui TTS no disponible")
            return

        self.synthesis_started.emit(text)
        thread = CoquiSynthThread(self.tts, text, self)
        thread.synthesis_done.connect(self._on_synth_done)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_synth_done(self, file_path: str, success: bool, error: str) -> None:
        if not success:
            self.synthesis_error.emit(error)
            return
        try:
            self._play_file(file_path)
            self.synthesis_completed.emit(file_path)
        finally:
            # Remove temp file shortly after starting playback (best effort)
            QTimer.singleShot(30000, lambda: self._safe_delete(file_path))

    def _play_file(self, file_path: str) -> None:
        # Prefer QtMultimedia if available
        try:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            if self.media_player is None:
                self.audio_output = QAudioOutput()
                self.media_player = QMediaPlayer()
                self.media_player.setAudioOutput(self.audio_output)
            url = QUrl.fromLocalFile(file_path)
            self.media_player.setSource(url)
            self.media_player.play()
            return
        except Exception as e:
            self.logger.warning(f"QtMultimedia no disponible, usando fallback: {e}")

        # macOS fallback using 'afplay'
        try:
            import subprocess
            subprocess.run(["afplay", file_path], check=False)
        except Exception as e:
            self.logger.error(f"No se pudo reproducir el audio: {e}")

    def _safe_delete(self, file_path: str) -> None:
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass

    def cleanup(self) -> None:
        # Nothing persistent except media player
        self.tts = None
        self.media_player = None
        self.audio_output = None