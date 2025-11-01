"""
Implementación de interfaz PySide6 para el asistente.
Interfaz moderna con botones, área de conversación y controles de voz.
"""

import sys
import os
from typing import Dict, Any, Optional, Callable

# Configurar entorno antes de importar PySide6
os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"

# Importar TTS (pyttsx3) — deshabilitado para ahorrar recursos
TTS_AVAILABLE = False

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame, QScrollArea,
    QSplitter, QGroupBox, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMutex, QWaitCondition, QObject, QMutexLocker
import threading
import time
import platform
import logging
from PySide6.QtGui import QFont, QIcon, QPalette, QColor
from .ui_abstraction import UIInterface, UIState


class TTSEngine(QObject):
    """Motor TTS moderno y robusto usando QThread para operaciones asíncronas"""

    # Señales para comunicación con la UI
    synthesis_started = Signal(str)
    synthesis_completed = Signal(str)
    synthesis_error = Signal(str)
    engine_ready = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = self._setup_logger()
        self.engine = None
        self.is_speaking = False
        self.current_text = ""
        self._init_engine()
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.pending_messages = []  # Cola de mensajes pendientes

    def _setup_logger(self) -> logging.Logger:
        """Configurar logger estructurado para TTS"""
        logger = logging.getLogger('TTSEngine')
        logger.setLevel(logging.WARNING)  # Solo mostrar warnings y errores

        # Evitar duplicados si ya existe
        if logger.handlers:
            return logger

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '🔊 TTS - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _init_engine(self) -> None:
        """Inicializar motor TTS con configuración multiplataforma"""
        try:
            # Configuración específica por plataforma
            system = platform.system().lower()

            self.engine = pyttsx3.init()

            # Configuración por defecto
            self.engine.setProperty('rate', 150)  # Velocidad normal
            self.engine.setProperty('volume', 0.8)  # Volumen estándar

            # Obtener voces disponibles
            voices = self.engine.getProperty('voices')

            # Seleccionar voz por defecto (primera voz femenina si está disponible)
            default_voice = self._select_best_voice(voices)
            if default_voice:
                self.engine.setProperty('voice', default_voice.id)

            self.engine_ready.emit()

        except Exception as e:
            self.logger.error(f"Error inicializando motor TTS: {e}")
            self.engine = None

    def _select_best_voice(self, voices) -> Optional[object]:
        """Seleccionar la mejor voz disponible"""
        if not voices:
            return None

        # Buscar voces en español con mejor calidad
        spanish_voices = []
        for voice in voices:
            name_lower = voice.name.lower()
            if any(keyword in name_lower for keyword in ['spanish', 'español', 'es-mx', 'es-es']):
                spanish_voices.append(voice)
        
        if spanish_voices:
            # Priorizar voces de alta calidad (no compact)
            high_quality = [v for v in spanish_voices if 'compact' not in v.id.lower()]
            if high_quality:
                return high_quality[0]
            else:
                return spanish_voices[0]

        # Si no hay voces en español, buscar voces femeninas
        female_voices = [v for v in voices if v.gender and 'female' in v.gender.lower()]
        if female_voices:
            return female_voices[0]

        # Fallback: primera voz disponible
        return voices[0]

    def speak_async(self, text: str) -> None:
        """Iniciar síntesis de voz asíncrona con cola de mensajes"""
        if not text or not text.strip():
            self.logger.warning("Texto vacío para síntesis")
            return

        if not self.engine:
            self.logger.error("Motor TTS no disponible")
            self.synthesis_error.emit("Motor TTS no disponible")
            return

        # Usar mutex para evitar race conditions
        with QMutexLocker(self.mutex):
            # Si ya está hablando, agregar a la cola
            if self.is_speaking:
                self.pending_messages.append(text)
                return

            # Marcar como hablando inmediatamente
            self.is_speaking = True

        # Iniciar síntesis inmediata (fuera del mutex)
        self._start_synthesis_internal(text)

    def _start_synthesis_internal(self, text: str) -> None:
        """Iniciar síntesis de un mensaje (método interno sin mutex)"""
        self.current_text = text

        # Emitir señal de inicio
        self.synthesis_started.emit(text)

        # Crear y ejecutar hilo de síntesis
        # No guardamos referencia - el thread se autodestruirá
        thread = TTSSynthesisThread(self.engine, text, self)
        thread.synthesis_done.connect(self._on_synthesis_done, Qt.QueuedConnection)
        thread.finished.connect(thread.deleteLater)  # Autodestruir cuando termine
        thread.start()

    def stop_synthesis(self) -> None:
        """Detener síntesis actual"""
        with QMutexLocker(self.mutex):
            if self.engine and self.is_speaking:
                try:
                    self.engine.stop()
                    self.logger.info("Síntesis detenida por usuario")
                except Exception as e:
                    self.logger.warning(f"Error deteniendo síntesis: {e}")
            self.is_speaking = False
            self.pending_messages.clear()  # Limpiar cola
            self.condition.wakeAll()

    def set_voice(self, voice_id: str) -> bool:
        """Cambiar voz del motor TTS"""
        if not self.engine:
            return False

        try:
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if voice.id == voice_id:
                    self.engine.setProperty('voice', voice_id)
                    self.logger.info(f"Voz cambiada a: {voice.name}")
                    return True
            self.logger.warning(f"Voz no encontrada: {voice_id}")
            return False
        except Exception as e:
            self.logger.error(f"Error cambiando voz: {e}")
            return False

    def set_rate(self, rate: int) -> bool:
        """Cambiar velocidad de habla (palabras por minuto)"""
        if not self.engine:
            return False

        try:
            self.engine.setProperty('rate', rate)
            self.logger.info(f"Velocidad cambiada a: {rate} WPM")
            return True
        except Exception as e:
            self.logger.error(f"Error cambiando velocidad: {e}")
            return False

    def set_volume(self, volume: float) -> bool:
        """Cambiar volumen (0.0 a 1.0)"""
        if not self.engine:
            return False

        try:
            self.engine.setProperty('volume', volume)
            self.logger.info(f"Volumen cambiado a: {volume}")
            return True
        except Exception as e:
            self.logger.error(f"Error cambiando volumen: {e}")
            return False

    def is_available(self) -> bool:
        """Verificar si TTS está disponible"""
        return self.engine is not None

    def _on_synthesis_done(self, success: bool, error_msg: str) -> None:
        """Manejador unificado cuando la síntesis termina (éxito o error)"""
        if success:
            # Emitir señal de completado
            completed_text = self.current_text
            self.synthesis_completed.emit(completed_text)
        else:
            self.logger.error(f"Error en síntesis: {error_msg}")
            
            # Emitir señal de error
            self.synthesis_error.emit(error_msg)
            
            # Intentar reinicializar el motor
            self._reinitialize_engine()
        
        # Marcar como no hablando y verificar cola
        with QMutexLocker(self.mutex):
            self.is_speaking = False
            has_pending = len(self.pending_messages) > 0
            queue_size = len(self.pending_messages)
        
        # Procesar siguiente mensaje en cola si existe (fuera del mutex)
        if has_pending:
            self._process_next_message()

    def _process_next_message(self) -> None:
        """Procesar siguiente mensaje en la cola"""
        with QMutexLocker(self.mutex):
            if not self.pending_messages:
                return
            next_message = self.pending_messages.pop(0)
            queue_size = len(self.pending_messages)
            # Marcar como hablando inmediatamente para evitar race conditions
            self.is_speaking = True
        
        # Procesar inmediatamente (ya marcamos is_speaking=True)
        self._start_synthesis_internal(next_message)

    def _reinitialize_engine(self) -> None:
        """Reinicializar motor TTS en caso de error"""

        # Limpiar motor actual
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass

        # Crear nuevo motor
        self._init_engine()

    def cleanup(self) -> None:
        """Limpiar recursos del motor TTS"""
        self.logger.info("Limpiando recursos TTS...")

        # Limpiar cola de mensajes
        self.pending_messages.clear()

        # Detener síntesis
        self.stop_synthesis()

        # Limpiar motor
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass

        self.engine = None


class LLMResponseThread(QThread):
    """Hilo dedicado para generar respuesta del LLM sin bloquear UI"""

    # Señales
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, llm_callback, message: str, parent=None):
        super().__init__(parent)
        self.llm_callback = llm_callback
        self.message = message
        self.logger = logging.getLogger('LLMResponseThread')

    def run(self):
        """Ejecutar generación de respuesta en hilo separado"""
        try:
            response = self.llm_callback(self.message)
            if response:
                self.response_ready.emit(response)
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error generando respuesta: {error_msg}")
            self.error_occurred.emit(error_msg)


class TTSSynthesisThread(QThread):
    """Hilo dedicado para síntesis de voz"""

    # Señales
    synthesis_done = Signal(bool, str)  # (success, error_message)

    def __init__(self, engine, text: str, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.text = text
        self.logger = logging.getLogger('TTSSynthesisThread')

    def run(self):
        """Ejecutar síntesis en hilo separado"""
        try:
            # Limpiar texto de caracteres especiales que pueden causar problemas
            clean_text = self._clean_text(self.text)

            self.logger.info(f"Iniciando síntesis: {clean_text[:100]}...")

            # SOLUCIÓN DEFINITIVA PARA macOS: Usar comando nativo 'say'
            # Esta es la solución más confiable según la investigación
            try:
                self.logger.info("🔊 Usando comando nativo 'say' de macOS...")
                
                # Usar subprocess para ejecutar el comando 'say' nativo de macOS
                import subprocess
                import platform
                
                # Verificar que estamos en macOS
                if platform.system() == 'Darwin':
                    # Configurar voz en español si está disponible
                    voice_options = [
                        'com.apple.voice.compact.es-MX.Paulina',  # Voz mexicana
                        'com.apple.voice.compact.es-ES.Eddy',      # Voz española
                        'com.apple.voice.compact.es-ES.Monica',    # Voz española femenina
                        'com.apple.voice.compact.es-ES.Paulina',   # Voz española
                    ]
                    
                    # Intentar con diferentes voces hasta encontrar una disponible
                    for voice in voice_options:
                        try:
                            self.logger.info(f"🔊 Probando voz: {voice}")
                            result = subprocess.run([
                                'say', '-v', voice, '-r', '150', clean_text
                            ], capture_output=True, text=True, timeout=30)
                            
                            if result.returncode == 0:
                                self.logger.info(f"✅ Audio reproducido exitosamente con voz: {voice}")
                                break
                            else:
                                self.logger.warning(f"Voz {voice} no disponible, probando siguiente...")
                                
                        except subprocess.TimeoutExpired:
                            self.logger.error(f"Timeout con voz {voice}")
                            continue
                        except Exception as voice_error:
                            self.logger.warning(f"Error con voz {voice}: {voice_error}")
                            continue
                    else:
                        # Si ninguna voz específica funciona, usar voz por defecto
                        self.logger.info("🔊 Usando voz por defecto del sistema...")
                        result = subprocess.run([
                            'say', '-r', '150', clean_text
                        ], capture_output=True, text=True, timeout=30)
                        
                        if result.returncode == 0:
                            self.logger.info("✅ Audio reproducido con voz por defecto")
                        else:
                            raise Exception(f"Error en comando say: {result.stderr}")
                
                else:
                    # Para otros sistemas, usar pyttsx3 como fallback
                    self.logger.info("🔄 Sistema no macOS, usando pyttsx3 como fallback...")
                    self.engine.setProperty('rate', 150)
                    self.engine.setProperty('volume', 0.9)
                    self.engine.say(clean_text)
                    self.engine.runAndWait()
                    self.logger.info("✅ Audio reproducido con pyttsx3")
                
            except Exception as say_error:
                self.logger.error(f"Error con comando say: {say_error}")
                # Fallback final: usar pyttsx3
                try:
                    self.logger.info("🔄 Fallback final: usando pyttsx3...")
                    self.engine.setProperty('rate', 150)
                    self.engine.setProperty('volume', 0.9)
                    self.engine.say(clean_text)
                    self.engine.runAndWait()
                    self.logger.info("✅ Audio reproducido con pyttsx3 fallback")
                except Exception as final_error:
                    self.logger.error(f"Error final con pyttsx3: {final_error}")
                    raise final_error

            self.logger.info("Síntesis completada exitosamente")
            
            # Emitir señal de éxito
            self.synthesis_done.emit(True, "")

        except Exception as e:
            error_msg = f"Error en síntesis: {str(e)}"
            self.logger.error(error_msg)
            # Emitir señal de error
            self.synthesis_done.emit(False, error_msg)

    def _clean_text(self, text: str) -> str:
        """Limpiar texto de caracteres especiales"""
        # Lista de caracteres a eliminar que pueden causar problemas en TTS
        special_chars = [
            "/", "*", "_", "🤖", "👤", "ℹ️", "✅", "❌", "⚠️", "📝", "🔧", "🧠",
            "🎯", "🚀", "💡", "📊", "🔍", "⚡", "🎤", "🔊", "💬", "🎛️", "📊",
            "🗑️", "❓", "🟢", "🎤", "🔊", "💭", "🌟", "🔥", "💫", "⭐"
        ]

        clean_text = text
        for char in special_chars:
            clean_text = clean_text.replace(char, "")

        return clean_text.strip()


class PySide6UI(UIInterface):
    """Interfaz PySide6 moderna para el asistente"""

    def __init__(self):
        self.app: Optional[QApplication] = None
        self.window: Optional[QMainWindow] = None
        self.components: Optional[Dict[str, Any]] = None
        self.user_input_callback: Optional[Callable[[str], None]] = None

        # Estado de la interfaz
        self.mic_enabled = False
        self.tts_enabled = True  # TTS activado por defecto
        self.current_status = UIState.IDLE

        # Logger siempre disponible
        self.logger = logging.getLogger('PySide6UI')

        # Motor TTS moderno
        self.tts_engine: Optional[TTSEngine] = None
        if TTS_AVAILABLE:
            try:
                self.tts_engine = TTSEngine()
                self.logger = logging.getLogger('PySide6UI')

                # Conectar señales del TTSEngine con la UI
                self.tts_engine.synthesis_started.connect(self._on_tts_started)
                self.tts_engine.synthesis_completed.connect(self._on_tts_completed)
                self.tts_engine.synthesis_error.connect(self._on_tts_error)
                self.tts_engine.engine_ready.connect(self._on_tts_ready)

                self.logger.info("Motor TTS moderno inicializado correctamente")
            except Exception as e:
                self.logger.error(f"Error inicializando motor TTS moderno: {e}")
                self.tts_engine = None
        
        # Widgets principales
        self.conversation_area: Optional[QTextEdit] = None
        self.input_field: Optional[QLineEdit] = None
        self.mic_button: Optional[QPushButton] = None
        self.tts_button: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None
        self.send_button: Optional[QPushButton] = None
    
    def initialize(self, components: Dict[str, Any]) -> None:
        """Inicializar la interfaz con los componentes del sistema"""
        self.components = components
        self._create_application()
        self._create_main_window()
        self._setup_ui()
        self._apply_modern_styling()
    
    def _create_application(self) -> None:
        """Crear aplicación Qt"""
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("Leonel Responde")
            self.app.setApplicationVersion("1.0.0")
        else:
            self.app = QApplication.instance()
    
    def _create_main_window(self) -> None:
        """Crear ventana principal"""
        self.window = QMainWindow()
        self.window.setWindowTitle("🤖 Leonel Responde - Asistente Multimodal")
        self.window.setMinimumSize(800, 600)
        self.window.resize(1000, 700)
    
    def _setup_ui(self) -> None:
        """Configurar la interfaz de usuario moderna"""
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Barra superior con controles
        self._create_top_controls(main_layout)
        
        # Área principal de conversación
        self._create_conversation_area(main_layout)
        
        # Área de entrada con controles
        self._create_input_area(main_layout)
    
    def _create_top_controls(self, parent) -> None:
        """Crear barra superior con controles"""
        # Contenedor de la barra superior
        top_bar = QFrame()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("""
            QFrame {
                background: linear-gradient(135deg, #2a2a2a, #1a1a1a);
                border-bottom: 2px solid #404040;
            }
        """)
        
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(15)
        
        # Botón de historial (izquierda)
        self.history_button = QPushButton("📋 Historial")
        self.history_button.setCheckable(True)
        self.history_button.setChecked(True)  # Visible por defecto
        self.history_button.clicked.connect(self._toggle_conversation_history)
        self.history_button.setStyleSheet("""
            QPushButton {
                background: #404040;
                color: #ffffff;
                border: 1px solid #606060;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #505050;
            }
            QPushButton:checked {
                background: #00ff41;
                color: #000000;
            }
        """)
        layout.addWidget(self.history_button)
        
        # Espaciador central
        layout.addStretch()
        
        # Botón de audio (derecha)
        self.audio_button = QPushButton("🔊 Audio")
        self.audio_button.setCheckable(True)
        self.audio_button.setChecked(True)  # Audio activado por defecto
        self.audio_button.clicked.connect(self._toggle_audio)
        self.audio_button.setStyleSheet("""
            QPushButton {
                background: #404040;
                color: #ffffff;
                border: 1px solid #606060;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #505050;
            }
            QPushButton:checked {
                background: #00ff41;
                color: #000000;
            }
        """)
        layout.addWidget(self.audio_button)
        
        # Botón de salida (derecha)
        self.exit_button = QPushButton("🚪 Salir")
        self.exit_button.clicked.connect(self._exit_application)
        self.exit_button.setStyleSheet("""
            QPushButton {
                background: #d32f2f;
                color: #ffffff;
                border: 1px solid #b71c1c;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #f44336;
            }
        """)
        layout.addWidget(self.exit_button)
        
        parent.addWidget(top_bar)
    
    def _create_conversation_area(self, parent) -> None:
        """Crear área principal de conversación"""
        # Contenedor del área de conversación
        self.conversation_container = QWidget()
        self.conversation_container.setStyleSheet("""
            QWidget {
                background: linear-gradient(135deg, #0a0a0a, #1a1a1a);
                border: 1px solid #333333;
            }
        """)
        
        layout = QVBoxLayout(self.conversation_container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Título del área de conversación
        title_label = QLabel("💬 Conversación")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Área de conversación con fondo claro para mejor contraste
        self.conversation_area = QTextEdit()
        self.conversation_area.setReadOnly(True)
        self.conversation_area.setFont(QFont("Inter", 12))
        self.conversation_area.setPlaceholderText("💬 La conversación aparecerá aquí...")
        self.conversation_area.setStyleSheet("""
            QTextEdit {
                background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                color: #212529;
                border: none;
                border-radius: 16px;
                padding: 24px;
                font-family: 'Inter', 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.1);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 0, 0, 0.5);
            }
        """)
        layout.addWidget(self.conversation_area)
        
        parent.addWidget(self.conversation_container)
    
    def _create_input_area(self, parent) -> None:
        """Crear área de entrada con controles"""
        # Contenedor del área de entrada
        input_container = QFrame()
        input_container.setFixedHeight(80)
        input_container.setStyleSheet("""
            QFrame {
                background: linear-gradient(135deg, #2a2a2a, #1a1a1a);
                border-top: 2px solid #404040;
            }
        """)
        
        layout = QHBoxLayout(input_container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # Botón de micrófono
        self.mic_button = QPushButton("🎤")
        self.mic_button.setCheckable(True)
        self.mic_button.setFixedSize(50, 50)
        self.mic_button.clicked.connect(self._toggle_mic_mode)
        self.mic_button.setStyleSheet("""
            QPushButton {
                background: #404040;
                color: #ffffff;
                border: 2px solid #606060;
                border-radius: 25px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #505050;
            }
            QPushButton:checked {
                background: #ff5722;
                border-color: #d84315;
            }
        """)
        layout.addWidget(self.mic_button)
        
        # Campo de entrada de texto
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe tu mensaje aquí...")
        self.input_field.returnPressed.connect(self._send_message)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: #2d2d2d;
                color: #ffffff;
                border: 2px solid #404040;
                border-radius: 25px;
                padding: 12px 20px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #00ff41;
            }
        """)
        layout.addWidget(self.input_field)
        
        # Botón de envío
        self.send_button = QPushButton("📤")
        self.send_button.setFixedSize(50, 50)
        self.send_button.clicked.connect(self._send_message)
        self.send_button.setStyleSheet("""
            QPushButton {
                background: #00ff41;
                color: #000000;
                border: 2px solid #00e676;
                border-radius: 25px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #00e676;
            }
        """)
        layout.addWidget(self.send_button)
        
        # Indicador de modo micrófono
        self.mic_indicator = QLabel("")
        self.mic_indicator.setStyleSheet("""
            QLabel {
                color: #ff5722;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.mic_indicator.hide()
        layout.addWidget(self.mic_indicator)
        
        parent.addWidget(input_container)
    
    def _toggle_conversation_history(self) -> None:
        """Toggle para mostrar/ocultar historial de conversación"""
        if hasattr(self, 'conversation_container'):
            if self.history_button.isChecked():
                self.conversation_container.show()
                self.history_button.setText("📋 Historial")
            else:
                self.conversation_container.hide()
                self.history_button.setText("📋 Oculto")
    
    def _toggle_audio(self) -> None:
        """Toggle para activar/desactivar audio TTS"""
        self.tts_enabled = self.audio_button.isChecked()
        if self.tts_enabled:
            self.audio_button.setText("🔊 Audio")
        else:
            self.audio_button.setText("🔇 Mudo")
    
    def _toggle_mic_mode(self) -> None:
        """Toggle para activar/desactivar modo micrófono"""
        if self.mic_button.isChecked():
            # Activar modo micrófono
            self.mic_enabled = True
            self.input_field.hide()
            self.mic_indicator.setText("🎙️ Escuchando...")
            self.mic_indicator.show()
            self.mic_button.setText("🎤")
        else:
            # Desactivar modo micrófono
            self.mic_enabled = False
            self.input_field.show()
            self.mic_indicator.hide()
            self.mic_button.setText("🎤")
    
    def _exit_application(self) -> None:
        """Salir de la aplicación de forma segura"""
        if hasattr(self, 'cleanup'):
            self.cleanup()
        if self.app:
            self.app.quit()
    
    def _create_conversation_panel(self, parent) -> None:
        """Crear panel de conversación"""
        conversation_widget = QWidget()
        conversation_layout = QVBoxLayout(conversation_widget)
        
        # Título del panel
        title_label = QLabel("💬 Conversación")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        conversation_layout.addWidget(title_label)
        
        # Área de conversación con estilo de chat moderno
        self.conversation_area = QTextEdit()
        self.conversation_area.setReadOnly(True)
        self.conversation_area.setFont(QFont("Segoe UI", 12))
        self.conversation_area.setPlaceholderText("💬 La conversación aparecerá aquí...")
        self.conversation_area.setStyleSheet("""
            QTextEdit {
                background: linear-gradient(135deg, #0a0a0a, #1a1a1a);
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 12px;
                padding: 15px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                line-height: 1.4;
            }
            QScrollBar:vertical {
                background: #2a2a2a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #777777;
            }
        """)
        conversation_layout.addWidget(self.conversation_area)
        
        # Panel de entrada
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe tu mensaje aquí...")
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_button)
        
        conversation_layout.addLayout(input_layout)
        
        parent.addWidget(conversation_widget)
    
    def _create_control_panel(self, parent) -> None:
        """Crear panel de controles"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # Título del panel
        title_label = QLabel("🎛️ Controles")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        control_layout.addWidget(title_label)
        
        # Grupo de controles de voz
        voice_group = QGroupBox("🎤 Controles de Voz")
        voice_layout = QGridLayout(voice_group)
        
        # Botón de micrófono
        self.mic_button = QPushButton("🎤 Micrófono: OFF")
        self.mic_button.clicked.connect(self._toggle_mic)
        self.mic_button.setCheckable(True)
        voice_layout.addWidget(self.mic_button, 0, 0)
        
        # Botón de TTS (activado por defecto)
        self.tts_button = QPushButton("🔊 TTS: ON")
        self.tts_button.clicked.connect(self._toggle_tts)
        self.tts_button.setCheckable(True)
        self.tts_button.setChecked(True)  # Activado por defecto
        voice_layout.addWidget(self.tts_button, 0, 1)
        
        control_layout.addWidget(voice_group)
        
        # Grupo de estado
        status_group = QGroupBox("📊 Estado del Sistema")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("🟢 Listo")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        # Información de componentes
        if self.components:
            components_label = QLabel(f"🧠 Componentes: {len(self.components)}")
            components_label.setFont(QFont("Arial", 10))
            status_layout.addWidget(components_label)
        
        control_layout.addWidget(status_group)
        
        # Botones de acción
        action_layout = QVBoxLayout()
        
        clear_button = QPushButton("🗑️ Limpiar Conversación")
        clear_button.clicked.connect(self._clear_conversation)
        action_layout.addWidget(clear_button)
        
        help_button = QPushButton("❓ Ayuda")
        help_button.clicked.connect(self._show_help)
        action_layout.addWidget(help_button)
        
        control_layout.addLayout(action_layout)
        
        # Espaciador
        control_layout.addStretch()
        
        parent.addWidget(control_widget)
    
    def _apply_modern_styling(self) -> None:
        """Aplicar estilo moderno a la interfaz"""
        # Estilo moderno con tema oscuro mejorado
        style = """
        QMainWindow {
            background: linear-gradient(135deg, #0a0a0a, #1a1a1a);
            color: #ffffff;
        }
        
        QWidget {
            background: transparent;
        }
        
        QTextEdit {
            background: transparent;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-size: 14px;
            line-height: 1.4;
        }
        
        QLineEdit {
            background: #2d2d2d;
            color: #ffffff;
            border: 2px solid #404040;
            border-radius: 25px;
            padding: 12px 20px;
            font-size: 14px;
        }
        
        QLineEdit:focus {
            border-color: #00ff41;
        }
        
        QPushButton {
            background: #404040;
            color: #ffffff;
            border: 1px solid #606060;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 12px;
        }
        
        QPushButton:hover {
            background: #505050;
        }
        
        QPushButton:pressed {
            background: #303030;
        }
        
        QPushButton:checked {
            background: #00ff41;
            color: #000000;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #404040;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QScrollBar:vertical {
            background: #2a2a2a;
            width: 8px;
            border-radius: 4px;
        }
        
        QScrollBar::handle:vertical {
            background: #555555;
            border-radius: 4px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: #777777;
        }
        """
        
        self.window.setStyleSheet(style)
    
    def _send_message(self) -> None:
        """Enviar mensaje del usuario"""
        if not self.input_field or not self.user_input_callback:
            return

        message = self.input_field.text().strip()
        if not message:
            return

        # Agregar mensaje del usuario a la conversación
        self.append_message(message, "user")

        # Limpiar campo de entrada
        self.input_field.clear()

        # Cambiar estado a "pensando"
        self.set_status(UIState.THINKING, "Generando respuesta...")

        # Procesar mensaje con LLM real si está disponible
        if hasattr(self, 'llm_callback') and self.llm_callback:
            # Ejecutar LLM en thread separado para no bloquear UI
            self._process_llm_async(message)
        else:
            # Fallback: procesar mensaje normal
            self.user_input_callback(message)
            self.set_status(UIState.IDLE)

    def _process_llm_async(self, message: str) -> None:
        """Procesar mensaje con LLM en thread separado"""
        # Crear thread para generar respuesta
        thread = LLMResponseThread(self.llm_callback, message, self)
        thread.response_ready.connect(self._on_llm_response)
        thread.error_occurred.connect(self._on_llm_error)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_llm_response(self, response: str) -> None:
        """Manejador cuando el LLM termina de generar respuesta"""
        if response:
            self.append_message(response, "assistant")
        self.set_status(UIState.IDLE)

    def _on_llm_error(self, error: str) -> None:
        """Manejador cuando hay error en el LLM"""
        self.show_error(f"Error generando respuesta: {error}")
        self.set_status(UIState.IDLE)
    
    def _toggle_mic(self) -> None:
        """Alternar micrófono (método legacy)"""
        # Este método se mantiene para compatibilidad
        # El nuevo control está en _toggle_mic_mode()
        self.mic_enabled = not self.mic_enabled
        if hasattr(self, 'mic_button'):
            self.mic_button.setChecked(self.mic_enabled)
            self._toggle_mic_mode()
    
    def _toggle_tts(self) -> None:
        """Alternar TTS (método legacy)"""
        # Este método se mantiene para compatibilidad
        # El nuevo control está en _toggle_audio()
        self.tts_enabled = not self.tts_enabled
        if hasattr(self, 'audio_button'):
            self.audio_button.setChecked(self.tts_enabled)
            self._toggle_audio()
        else:
            # Fallback para el botón legacy
            if hasattr(self, 'tts_button') and self.tts_button:
                self.tts_button.setChecked(self.tts_enabled)
    
    def _clear_conversation(self) -> None:
        """Limpiar conversación"""
        if self.conversation_area:
            self.conversation_area.clear()
            self.append_message("Conversación limpiada", "system")
    
    def _show_help(self) -> None:
        """Mostrar ayuda"""
        help_text = """
        <h3>🤖 Leonel Responde - Ayuda</h3>
        <p><b>Controles:</b></p>
        <ul>
        <li>🎤 Micrófono: Activar/desactivar reconocimiento de voz</li>
        <li>🔊 TTS: Activar/desactivar síntesis de voz</li>
        </ul>
        <p><b>Uso:</b></p>
        <ul>
        <li>Escribe tu mensaje en el campo de entrada</li>
        <li>Presiona Enter o el botón Enviar</li>
        <li>La conversación se mostrará en el área principal</li>
        </ul>
        <p><b>Comandos especiales:</b></p>
        <ul>
        <li>/help - Mostrar esta ayuda</li>
        <li>/status - Ver estado del sistema</li>
        <li>/clear - Limpiar conversación</li>
        </ul>
        """
        
        if self.conversation_area:
            self.conversation_area.append(help_text)
    
    def append_message(self, message: str, sender: str = "assistant") -> None:
        """Agregar mensaje a la conversación con interfaz limpia"""
        if not self.conversation_area:
            return
        
        # Logs técnicos van a la consola
        print(f"🔊 TTS DEBUG: append_message - sender: {sender}, tts_enabled: {self.tts_enabled}, tts_engine: {self.tts_engine is not None}")
        
        # Log del mensaje del usuario para análisis (solo mensajes importantes)
        if sender == "user":
            print(f"👤 USUARIO: {message}")
        elif sender == "assistant":
            print(f"🤖 ASISTENTE: {message}")
        elif sender == "system" and not any(keyword in message for keyword in ["Tiempo E2E", "límite", "⏱️"]):
            # Solo mostrar mensajes del sistema que no sean métricas de tiempo
            print(f"⚙️ SISTEMA: {message}")
        
        # Diseño moderno con contraste mejorado y sin emojis
        if sender == "assistant":
            # Burbuja del asistente (izquierda, fondo claro con texto oscuro)
            formatted_message = f"""
            <div style='display: flex; justify-content: flex-start; margin: 12px 0; animation: fadeInLeft 0.3s ease-out;'>
                <div style='
                    background: #ffffff;
                    color: #2c3e50;
                    padding: 14px 18px;
                    border-radius: 18px 18px 18px 6px;
                    max-width: 80%;
                    word-wrap: break-word;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    font-weight: 400;
                    line-height: 1.5;
                    position: relative;
                    font-family: "Inter", "Segoe UI", "Arial", sans-serif;
                    font-size: 14px;
                    transition: transform 0.2s ease;
                    border: 1px solid #e1e8ed;
                '>
                    {message}
                </div>
            </div>
            """
        elif sender == "user":
            # Burbuja del usuario (derecha, azul con texto blanco)
            formatted_message = f"""
            <div style='display: flex; justify-content: flex-end; margin: 12px 0; animation: fadeInRight 0.3s ease-out;'>
                <div style='
                    background: #007bff;
                    color: white;
                    padding: 14px 18px;
                    border-radius: 18px 18px 6px 18px;
                    max-width: 80%;
                    word-wrap: break-word;
                    box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);
                    font-weight: 400;
                    line-height: 1.5;
                    position: relative;
                    font-family: "Inter", "Segoe UI", "Arial", sans-serif;
                    font-size: 14px;
                    transition: transform 0.2s ease;
                '>
                    {message}
                </div>
            </div>
            """
        elif sender == "system":
            # Mensaje del sistema (centro, estilo pill minimalista)
            formatted_message = f"""
            <div style='display: flex; justify-content: center; margin: 8px 0; animation: fadeIn 0.4s ease-out;'>
                <div style='
                    background: rgba(108, 117, 125, 0.2);
                    color: #6c757d;
                    padding: 8px 16px;
                    border-radius: 20px;
                    max-width: 90%;
                    word-wrap: break-word;
                    border: 1px solid rgba(108, 117, 125, 0.3);
                    font-weight: 400;
                    text-align: center;
                    font-family: "Inter", "Segoe UI", "Arial", sans-serif;
                    font-size: 12px;
                    font-style: italic;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                '>
                    {message}
                </div>
            </div>
            """
        else:
            # Mensaje genérico con estilo minimalista
            formatted_message = f"""
            <div style='margin: 8px 0; padding: 8px 12px; background: rgba(255,255,255,0.1); border-radius: 8px; color: #adb5bd; font-family: "Inter", "Segoe UI", "Arial", sans-serif;'>
                {message}
            </div>
            """
        
        # Agregar estilos CSS para animaciones
        css_styles = """
        <style>
        @keyframes fadeInLeft {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeInRight {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """
        
        # Solo agregar estilos CSS una vez
        if not hasattr(self, '_css_added'):
            self.conversation_area.append(css_styles)
            self._css_added = True
        
        self.conversation_area.append(formatted_message)
        
        # Scroll hacia abajo
        scrollbar = self.conversation_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Reproducir con TTS si está habilitado y es mensaje del asistente
        if sender == "assistant" and self.tts_enabled and self.tts_engine and self.tts_engine.is_available():
            self.logger.info("Iniciando síntesis TTS para mensaje del asistente")
            # Usar QTimer con delay más largo para asegurar que la UI se actualice primero
            QTimer.singleShot(300, lambda: self.tts_engine.speak_async(message))
        else:
            self.logger.debug(f"TTS no activado - sender: {sender}, tts_enabled: {self.tts_enabled}, tts_available: {self.tts_engine and self.tts_engine.is_available()}")
    
    def toggle_mic(self, enabled: bool) -> None:
        """Activar/desactivar micrófono"""
        self.mic_enabled = enabled
        if self.mic_button:
            self.mic_button.setChecked(enabled)
            self.mic_button.setText(f"🎤 Micrófono: {'ON' if enabled else 'OFF'}")
    
    def toggle_tts(self, enabled: bool) -> None:
        """Activar/desactivar síntesis de voz"""
        self.tts_enabled = enabled

        # Detener síntesis actual si se desactiva TTS
        if not enabled and self.tts_engine:
            self.tts_engine.stop_synthesis()

        if self.tts_button:
            self.tts_button.setChecked(enabled)
            self.tts_button.setText(f"🔊 TTS: {'ON' if enabled else 'OFF'}")

    def set_tts_voice(self, voice_id: str) -> bool:
        """Cambiar voz del TTS"""
        if self.tts_engine:
            return self.tts_engine.set_voice(voice_id)
        return False

    def set_tts_rate(self, rate: int) -> bool:
        """Cambiar velocidad del TTS (palabras por minuto)"""
        if self.tts_engine:
            return self.tts_engine.set_rate(rate)
        return False

    def set_tts_volume(self, volume: float) -> bool:
        """Cambiar volumen del TTS (0.0 a 1.0)"""
        if self.tts_engine:
            return self.tts_engine.set_volume(volume)
        return False

    def stop_tts(self) -> None:
        """Detener síntesis TTS actual"""
        if self.tts_engine:
            self.tts_engine.stop_synthesis()

    def is_tts_available(self) -> bool:
        """Verificar si TTS está disponible"""
        return self.tts_engine and self.tts_engine.is_available()

    def set_status(self, status: UIState, message: str = "") -> None:
        """Actualizar estado de la interfaz"""
        self.current_status = status
        if not self.status_label:
            return
        
        status_messages = {
            UIState.IDLE: "🟢 Listo",
            UIState.LISTENING: "🎤 Escuchando...",
            UIState.THINKING: "🤔 Pensando...",
            UIState.SPEAKING: "🔊 Hablando...",
            UIState.ERROR: "❌ Error"
        }
        
        status_text = status_messages.get(status, "❓ Estado desconocido")
        if message:
            status_text += f" - {message}"
        
        self.status_label.setText(status_text)
    
    def set_user_input_callback(self, callback: Callable[[str], None]) -> None:
        """Establecer callback para entrada del usuario"""
        self.user_input_callback = callback

    def set_real_llm_callback(self, llm_callback: Callable[[str], str]) -> None:
        """Establecer callback que usa el LLM real"""
        self.llm_callback = llm_callback
    
    def show_error(self, error: str) -> None:
        """Mostrar error al usuario"""
        self.set_status(UIState.ERROR, error)
        self.append_message(f"❌ Error: {error}", "system")
    
    def run(self) -> None:
        """Ejecutar la interfaz PySide6"""
        if not self.app or not self.window:
            print("❌ Interfaz no inicializada correctamente")
            return
        
        # Mostrar ventana
        self.window.show()
        
        # Mensaje de bienvenida limpio
        self.append_message("¡Hola! Soy tu asistente de IA. ¿En qué puedo ayudarte hoy?", "assistant")
        
        # Ejecutar aplicación
        self.app.exec()

    def _on_tts_started(self, text: str) -> None:
        """Manejador cuando inicia síntesis TTS"""
        self.set_status(UIState.SPEAKING, "Sintetizando voz...")

    def _on_tts_completed(self, text: str) -> None:
        """Manejador cuando termina síntesis TTS"""
        self.set_status(UIState.IDLE)

    def _on_tts_error(self, error: str) -> None:
        """Manejador cuando hay error en síntesis TTS"""
        self.logger.error(f"Error TTS: {error}")
        self.set_status(UIState.ERROR, f"Error TTS: {error}")
        # Mostrar error al usuario después de un breve delay
        QTimer.singleShot(3000, lambda: self.set_status(UIState.IDLE))

    def _on_tts_ready(self) -> None:
        """Manejador cuando motor TTS está listo"""
        self.logger.info("Motor TTS listo para uso")


    def cleanup(self) -> None:
        """Limpiar recursos de la interfaz"""
        # Limpiar motor TTS moderno
        if self.tts_engine:
            self.tts_engine.cleanup()
            self.tts_engine = None

        if self.app:
            self.app.quit()

        self.components = None
        self.user_input_callback = None
        self.window = None
        self.app = None

