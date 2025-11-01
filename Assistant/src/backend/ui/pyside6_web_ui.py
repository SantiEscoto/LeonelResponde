"""
PySide6 Web UI - Interfaz híbrida moderna con QWebEngineView
Combina PySide6 con HTML/CSS/JavaScript para una experiencia tipo ChatGPT
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QApplication
)
from PySide6.QtCore import QObject, Signal, Slot, QUrl, QTimer, QThread, QMutex, QMutexLocker
from PySide6.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect

# Importar componentes existentes
from .pyside6_ui import TTSEngine, TTSSynthesisThread, LLMResponseThread, TTS_AVAILABLE
from .ui_abstraction import UIInterface, UIState


class WebBridge(QObject):
    """Puente de comunicación entre Python y JavaScript"""
    
    # Señales que van de Python a JavaScript
    message_received = Signal(str)  # Mensaje del asistente
    system_message_received = Signal(str)  # Mensaje del sistema
    status_updated = Signal(bool, bool)  # (conexión, TTS)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger('WebBridge')
    
    @Slot(str)
    def send_message(self, message: str):
        """Recibe mensaje del usuario desde JavaScript"""
        self.logger.info(f"Mensaje recibido desde web: {message}")
        if hasattr(self.parent(), 'on_user_message'):
            self.parent().on_user_message(message)
    
    @Slot(str)
    def receiveMessage(self, message: str):
        """Alias para compatibilidad con JavaScript"""
        self.send_message(message)
    
    @Slot(str)
    def receiveSystemMessage(self, message: str):
        """Recibe mensaje del sistema desde JavaScript"""
        self.logger.info(f"Mensaje del sistema desde web: {message}")
        if hasattr(self.parent(), '_on_web_system_message'):
            self.parent()._on_web_system_message(message)
    
    @Slot(str)
    def addAssistantMessage(self, message: str):
        """Agregar mensaje del asistente a la interfaz"""
        self.logger.info(f"Agregando mensaje del asistente: {message}")
        if hasattr(self.parent(), '_send_assistant_message'):
            self.parent()._send_assistant_message(message)
    
    @Slot(str)
    def addSystemMessage(self, message: str):
        """Agregar mensaje del sistema a la interfaz"""
        self.logger.info(f"Agregando mensaje del sistema: {message}")
        if hasattr(self.parent(), '_send_system_message'):
            self.parent()._send_system_message(message)
    
    @Slot()
    def get_status(self):
        """Obtiene el estado actual del sistema"""
        if hasattr(self.parent(), 'get_system_status'):
            return self.parent().get_system_status()
        return {"connected": True, "tts_enabled": True}

    @Slot(bool)
    def toggleTTS(self, enabled: bool):
        """Activar/desactivar TTS desde la web"""
        if hasattr(self.parent(), 'toggle_tts'):
            self.parent().toggle_tts(enabled)
            self.status_updated.emit(True, enabled)

    @Slot(bool)
    def toggleMic(self, enabled: bool):
        """Activar/desactivar micrófono desde la web"""
        if hasattr(self.parent(), 'toggle_mic'):
            self.parent().toggle_mic(enabled)


class PySide6WebUI(QMainWindow):
    """
    Interfaz híbrida moderna que combina PySide6 con QWebEngineView
    Proporciona una experiencia tipo ChatGPT con comunicación bidireccional
    """
    
    def __init__(self, llm_callback=None, config=None):
        super().__init__()
        
        self.logger = logging.getLogger('PySide6WebUI')
        self.llm_callback = llm_callback
        self.config = config or {}
        
        # Estado del sistema
        self.tts_enabled = False  # Desactivado por defecto; se puede activar si disponible
        self.is_connected = True
        self.message_count = 0
        
        # Referencias UI inferiores (se crean en _setup_ui)
        self.connection_label = None
        self.message_count_label = None
        self.tts_button = None
        
        # Motores y hilos
        self.tts_engine = None
        self.llm_thread = None
        
        # Configurar UI
        self._setup_ui()
        self._setup_tts()
        
        # Timer para actualizaciones de estado
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_web_status)
        self.status_timer.start(1000)  # Actualizar cada segundo
        
        self.logger.info("PySide6WebUI inicializada con interfaz híbrida")
    
    def _setup_ui(self):
        """Configurar la interfaz principal"""
        self.setWindowTitle("🦁 Leonel Responde")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # WebEngineView para la interfaz de chat
        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(600)
        
        # Configurar para suprimir advertencias de Skia
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.JavascriptEnabled, True)
        self.web_view.settings().setAttribute(self.web_view.settings().WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # Permisos de captura de audio/vídeo para getUserMedia
        try:
            self.web_view.page().featurePermissionRequested.connect(self._on_feature_permission_requested)
        except Exception:
            pass
        
        # Cargar la interfaz HTML
        html_path = Path(__file__).parent.parent.parent.parent / "chat_interface.html"
        if html_path.exists():
            self.web_view.load(QUrl.fromLocalFile(str(html_path.absolute())))
            self.logger.info(f"Interfaz web cargada desde: {html_path}")
        else:
            self.logger.error(f"Archivo HTML no encontrado: {html_path}")
            # Crear interfaz de fallback
            self._create_fallback_ui()
        
        # Configurar el canal web DESPUÉS de cargar la página
        self._setup_web_bridge()
        
        main_layout.addWidget(self.web_view)
        
        # Barra inferior con información
        bottom_bar = QFrame()
        bottom_bar.setObjectName("bottomBar")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 10, 16, 10)
        bottom_layout.setSpacing(12)
        
        self.connection_label = QLabel("🟢 Listo")
        self.message_count_label = QLabel("0 mensajes")
        self.tts_button = QPushButton("🔇 TTS")
        self.tts_button.setCheckable(True)
        self.tts_button.setChecked(False)
        self.tts_button.clicked.connect(self._toggle_tts)
        
        bottom_layout.addWidget(self.connection_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.message_count_label)
        bottom_layout.addWidget(self.tts_button)
        
        main_layout.addWidget(bottom_bar)
        
        # Aplicar estilos modernos
        self._apply_modern_styling()
    
    def _create_fallback_ui(self):
        """Crear interfaz de fallback si no se encuentra el HTML"""
        # Para QWebEngineView, cargar una página HTML simple
        fallback_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - Interfaz Web</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: #f8f9fa;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .error-container {
                    text-align: center;
                    padding: 40px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }
                .error-icon {
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                .error-title {
                    color: #dc3545;
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 10px;
                }
                .error-message {
                    color: #666;
                    font-size: 16px;
                }
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">❌</div>
                <div class="error-title">Error de Interfaz</div>
                <div class="error-message">No se pudo cargar la interfaz web moderna.<br>Usando interfaz de fallback.</div>
            </div>
        </body>
        </html>
        """
        
        self.web_view.setHtml(fallback_html)
    
    def _setup_web_bridge(self):
        """Configurar el puente de comunicación web"""
        # Configurar QWebChannel para comunicación bidireccional
        self.web_bridge = WebBridge(self)
        self.web_channel = QWebChannel()
        self.web_channel.registerObject("web_bridge", self.web_bridge)
        self.web_view.page().setWebChannel(self.web_channel)
        
        # Conectar señales
        self.web_bridge.message_received.connect(self._on_web_message)
        
        # Wait for page to load before injecting JavaScript
        self.web_view.loadFinished.connect(self._on_page_loaded)
        
        self.logger.info("Puente web configurado correctamente")
    
    def _on_page_loaded(self, success):
        """Called when the web page has finished loading"""
        if success:
            self.logger.info("Página web cargada, configurando JavaScript...")
            # Small delay to ensure all HTML scripts are executed
            QTimer.singleShot(100, self._setup_javascript_communication)
        else:
            self.logger.error("Error cargando página web")
    
    def _setup_javascript_communication(self):
        """Configurar comunicación JavaScript directa"""
        # Inyectar JavaScript para conectar con QWebChannel
        host = os.environ.get('VOICE_WS_HOST', '127.0.0.1')
        port = os.environ.get('VOICE_WS_PORT', '8765')
        voice_ws_url = f"ws://{host}:{port}"
        # Configurar backend HTTP desde config o variables de entorno
        try:
            from src.backend.utils.unified_config import get_config
            cfg = get_config()
            api_host = cfg.system.api_host
            api_port = cfg.system.api_port
        except Exception:
            api_host = os.environ.get('API_HOST', '127.0.0.1')
            api_port = os.environ.get('API_PORT', '8000')
        backend_http_url = f"http://{api_host}:{api_port}"
        js_code = f"""
        // Configurar comunicación con QWebChannel
        if (typeof QWebChannel !== 'undefined' && qt && qt.webChannelTransport) {{
            console.log('🔍 [DEBUG] Configurando QWebChannel...');
            new QWebChannel(qt.webChannelTransport, function(channel) {{
                console.log('🔍 [DEBUG] QWebChannel conectado');
                window.qtwebchannel = channel.objects.web_bridge;
                window.voiceServerUrl = '{voice_ws_url}';
                window.backendHttp = '{backend_http_url}';
                
                // Configurar pyBridge para usar QWebChannel
                window.pyBridge = {{
                    sendMessage: (message) => {{
                        // Garantizar desbloqueo de autoplay antes del envío
                        try {{
                            if (typeof window.unlockTTS === 'function') {{
                                window.unlockTTS();
                            }}
                        }} catch (e) {{
                            console.warn('⚠️ [DEBUG] unlockTTS() falló o no existe:', e);
                        }}
                        console.log('🔍 [DEBUG] Enviando mensaje via QWebChannel:', message);
                        if (window.qtwebchannel && window.qtwebchannel.send_message) {{
                            window.qtwebchannel.send_message(message);
                        }} else {{
                            console.error('❌ [DEBUG] qtwebchannel.send_message no disponible');
                        }}
                    }},
                    // Mostrar/ocultar indicador de escritura
                    showTypingIndicator: () => {{
                        if (window.chatInterface && window.chatInterface.showTypingIndicator) {{
                            window.chatInterface.showTypingIndicator();
                        }}
                    }},
                    hideTypingIndicator: () => {{
                        if (window.chatInterface && window.chatInterface.hideTypingIndicator) {{
                            window.chatInterface.hideTypingIndicator();
                        }}
                    }},
                    // Agregar mensaje de usuario a la vista web
                    addUserMessage: (message) => {{
                        if (window.chatInterface && window.chatInterface.addUserMessage) {{
                            window.chatInterface.addUserMessage(message);
                        }}
                    }},
                    // Mensajes de respuesta del asistente y del sistema
                    receiveMessage: (message) => {{
                        console.log('🔍 [DEBUG] pyBridge.receiveMessage llamado con:', message);
                        if (window.chatInterface) {{
                            // Transformar typing → assistant si existe (no ocultar indicador aquí)
                            window.chatInterface.addAssistantMessage?.(message);
                        }}
                    }},
                    receiveSystemMessage: (message) => {{
                        console.log('🔍 [DEBUG] pyBridge.receiveSystemMessage llamado con:', message);
                        if (window.chatInterface) {{
                            window.chatInterface.addSystemMessage?.(message);
                        }}
                    }},
                    toggleTTS: (enabled) => {{
                        if (window.qtwebchannel && window.qtwebchannel.toggleTTS) {{
                            window.qtwebchannel.toggleTTS(enabled);
                        }}
                    }},
                    toggleMic: (enabled) => {{
                        if (window.qtwebchannel && window.qtwebchannel.toggleMic) {{
                            window.qtwebchannel.toggleMic(enabled);
                        }}
                    }}
                }};
                
                console.log('✅ [DEBUG] QWebChannel communication setup complete');
            }});
        }} else {{
            console.log('❌ [DEBUG] QWebChannel no disponible, usando fallback');
        }}
        """
        
        self.web_view.page().runJavaScript(js_code)
    
    def _apply_modern_styling(self):
        """Aplicar estilos modernos a la ventana"""
        self.setStyleSheet("""
            QMainWindow {
                background: #f8f9fa;
            }
            QWebEngineView {
                border: none;
                background: white;
            }
            #bottomBar {
                background: #ffffff;
                border-top: 1px solid #e9ecef;
            }
            QLabel {
                color: #495057;
            }
            QPushButton {
                background: #f1f3f5;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QPushButton:checked {
                background: #e7f5ff;
                border-color: #74c0fc;
            }
        """)
    
    def _toggle_tts(self):
        """Alternar estado del TTS"""
        self.tts_enabled = not self.tts_enabled
        button_text = "🔊 TTS" if self.tts_enabled else "🔇 TTS"
        if self.tts_button:
            self.tts_button.setText(button_text)
        self.logger.info(f"TTS {'activado' if self.tts_enabled else 'desactivado'}")
    
    def _update_web_status(self):
        """Actualizar estado en la interfaz web"""
        if hasattr(self, 'web_bridge'):
            self.web_bridge.status_updated.emit(self.is_connected, self.tts_enabled)
    
    def on_user_message(self, message: str):
        """Manejar mensaje del usuario"""
        self.logger.info(f"Procesando mensaje del usuario: {message}")
        self.message_count += 1
        self.message_count_label.setText(f"{self.message_count} mensajes")
        
        # NO volver a agregar el mensaje en la interfaz web (ya lo hace JS)
        # self._send_to_web('addUserMessage', message)
        
        # Procesar con LLM si está disponible
        if self.llm_callback:
            self._process_llm_async(message)
        else:
            # Respuesta de fallback
            self._send_assistant_message("Mensaje recibido: " + message)
    
    def _process_llm_async(self, message: str):
        """Procesar mensaje con LLM de forma asíncrona"""
        if self.llm_thread and self.llm_thread.isRunning():
            self.logger.warning("LLM thread ya está ejecutándose")
            return
        
        self.llm_thread = LLMResponseThread(self.llm_callback, message)
        self.llm_thread.response_ready.connect(self._on_llm_response)
        self.llm_thread.error_occurred.connect(self._on_llm_error)
        self.llm_thread.start()
        
        # Mostrar indicador de escritura
        self._send_to_web('showTypingIndicator')
    
    def _on_llm_response(self, response: str):
        """Manejar respuesta del LLM"""
        self.logger.info(f"Respuesta del LLM recibida: {response}")
        self._send_assistant_message(response)
    
    def _on_llm_error(self, error: str):
        """Manejar error del LLM"""
        self.logger.error(f"Error del LLM: {error}")
        self._send_system_message(f"Error: {error}")
    
        
    def _send_assistant_message(self, message: str):
        """Enviar mensaje del asistente a la interfaz web"""
        self._send_to_web('receiveMessage', message)
        
        # Reproducir con TTS si está habilitado
        if self.tts_enabled and self.tts_engine:
            try:
                self.tts_engine.speak_async(message)
            except Exception as e:
                self.logger.error(f"Error en TTS: {e}")
    
    def _send_system_message(self, message: str):
        """Enviar mensaje del sistema a la interfaz web"""
        self._send_to_web('receiveSystemMessage', message)
    
    def _send_to_web(self, method: str, *args):
        """Enviar comando a JavaScript"""
        try:
            # Construir comando JavaScript con verificación de existencia
            if args:
                args_str = ', '.join(json.dumps(arg) for arg in args)
                js_command = f"""
                if (window.pyBridge && window.pyBridge.{method}) {{
                    window.pyBridge.{method}({args_str});
                }} else {{
                    console.log('❌ [DEBUG] pyBridge.{method} no disponible');
                }}
                """
            else:
                js_command = f"""
                if (window.pyBridge && window.pyBridge.{method}) {{
                    window.pyBridge.{method}();
                }} else {{
                    console.log('❌ [DEBUG] pyBridge.{method} no disponible');
                }}
                """
            
            # Ejecutar en la página web
            self.web_view.page().runJavaScript(js_command)
            self.logger.debug(f"Comando JS enviado: {method}")
            
        except Exception as e:
            self.logger.error(f"Error enviando comando a web: {e}")
    
    def get_system_status(self):
        """Obtener estado del sistema"""
        return {
            "connected": self.is_connected,
            "tts_enabled": self.tts_enabled,
            "message_count": self.message_count
        }
    
    # Implementar métodos requeridos por UIInterface
    def initialize(self, components: Dict[str, Any]) -> None:
        """Inicializar la interfaz con los componentes del sistema"""
        self.logger.info("Inicializando interfaz web con componentes del sistema")
        
        # Configurar callback LLM
        if 'llm' in components:
            self.llm_callback = components['llm'].query
            self.logger.info("Callback LLM configurado")
        
        # Programar mensaje de bienvenida para después de que todo esté configurado
        QTimer.singleShot(2000, self._send_welcome_messages)
    
    def _send_welcome_messages(self):
        """Enviar mensajes de bienvenida después de que todo esté configurado"""
        self._send_system_message("✅ ¡Listo para chatear!")
        self._send_assistant_message("¡Hola! Soy tu asistente de IA. ¿En qué puedo ayudarte hoy?")
        
        # Reproducir mensaje de bienvenida con TTS
        if self.tts_enabled and self.tts_engine:
            self.tts_engine.speak_async("¡Hola! Soy tu asistente de IA. ¿En qué puedo ayudarte hoy?")
    
    def append_message(self, message: str, sender: str = "assistant") -> None:
        """Agregar mensaje a la conversación"""
        if sender == "user":
            self._send_to_web('addUserMessage', message)
        elif sender == "assistant":
            self._send_assistant_message(message)
        elif sender == "system":
            self._send_system_message(message)
    
    def toggle_mic(self, enabled: bool) -> None:
        """Activar/desactivar micrófono"""
        self.logger.info(f"Micrófono {'activado' if enabled else 'desactivado'}")
        # TODO: Implementar funcionalidad de micrófono
    
    def toggle_tts(self, enabled: bool) -> None:
        """Activar/desactivar síntesis de voz"""
        self.tts_enabled = enabled
        button_text = "🔊 TTS" if enabled else "🔇 TTS"
        if self.tts_button:
            self.tts_button.setText(button_text)
        self.logger.info(f"TTS {'activado' if enabled else 'desactivado'}")
    
    def set_status(self, status: UIState, message: str = "") -> None:
        """Actualizar estado de la interfaz"""
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
        
        if self.connection_label:
            self.connection_label.setText(status_text)
        self.logger.info(f"Estado actualizado: {status_text}")
    
    def set_user_input_callback(self, callback: Callable[[str], None]) -> None:
        """Establecer callback para entrada del usuario"""
        self.user_input_callback = callback
        self.logger.info("Callback de entrada del usuario configurado")
    
    def _on_web_message(self, message: str):
        """Manejar mensaje recibido desde la interfaz web"""
        self.logger.info(f"Mensaje recibido desde web: {message}")
        self.on_user_message(message)
    
    def _on_web_system_message(self, message: str):
        """Manejar mensaje del sistema desde la interfaz web"""
        self.logger.info(f"Mensaje del sistema desde web: {message}")
        self._send_system_message(message)
    
    def _on_web_status_update(self, connection: bool, tts: bool):
        """Manejar actualización de estado desde la interfaz web"""
        self.logger.info(f"Estado actualizado desde web: conexión={connection}, TTS={tts}")
        self.is_connected = connection
        self.tts_enabled = tts
    
    def cleanup(self):
        """Limpiar recursos y cerrar"""
        self.logger.info("Iniciando limpieza de recursos...")
        
        # Detener timer
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        
        # Limpiar TTS
        if self.tts_engine:
            try:
                self.tts_engine.cleanup()
            except Exception as e:
                self.logger.error(f"Error limpiando TTS: {e}")
        
        # Detener threads
        if self.llm_thread and self.llm_thread.isRunning():
            self.llm_thread.quit()
            self.llm_thread.wait()
        
        self.logger.info("Limpieza completada")
        self.close()
    
    
    def _setup_tts(self):
        """Inicializar el motor TTS y estado de botón.
        Usa el TTSEngine (pyttsx3) si está disponible y deja el TTS
        desactivado por defecto para que el usuario lo active cuando quiera.
        """
        # Desactivar por defecto
        self.tts_enabled = False
        try:
            if TTS_AVAILABLE:
                self.tts_engine = TTSEngine(self)
                # Intentar aplicar voz/velocidad desde variables de entorno
                voice_id = os.environ.get('PYTTSX3_VOICE_ID')
                rate = os.environ.get('PYTTSX3_RATE')
                if voice_id:
                    ok = False
                    try:
                        ok = self.tts_engine.set_voice(voice_id)
                    except Exception:
                        ok = False
                    self.logger.info(f"Voz preferida (PYTTSX3_VOICE_ID={voice_id}) {'aplicada' if ok else 'no encontrada'}")
                if rate:
                    try:
                        r = int(rate)
                        self.tts_engine.set_rate(r)
                        self.logger.info(f"Velocidad TTS aplicada: {r} WPM")
                    except Exception:
                        self.logger.warning(f"PYTTSX3_RATE inválido: {rate}")
                # Mantener el botón habilitado; el usuario puede activarlo
                if self.tts_button:
                    self.tts_button.setEnabled(True)
                self.logger.info("Motor TTS inicializado correctamente en WebUI")
            else:
                # Sin TTS disponible, deshabilitar el botón
                self.tts_engine = None
                if self.tts_button:
                    self.tts_button.setEnabled(False)
                self.logger.warning("TTS no disponible (pyttsx3 no instalado)")
        except Exception as e:
            # En caso de error al inicializar, deshabilitar TTS de forma segura
            self.tts_engine = None
            if self.tts_button:
                self.tts_button.setEnabled(False)
            self.logger.error(f"Error inicializando TTS en WebUI: {e}")
    
    
    
    
    def _on_feature_permission_requested(self, security_origin, feature):
        """Conceder permisos de micrófono/cámara para getUserMedia en QWebEngine."""
        try:
            # Asegurar referencia a QWebEnginePage
            _ = QWebEnginePage
        except Exception:
            return
        try:
            if feature in (
                QWebEnginePage.Feature.MediaAudioCapture,
                QWebEnginePage.Feature.MediaVideoCapture,
                QWebEnginePage.Feature.MediaAudioVideoCapture,
            ):
                self.web_view.page().setFeaturePermission(
                    security_origin, feature, QWebEnginePage.PermissionGrantedByUser
                )
                try:
                    origin_str = security_origin.toString()
                except Exception:
                    origin_str = str(security_origin)
                self.logger.info(f"Permiso de media concedido: {feature} para {origin_str}")
            else:
                self.web_view.page().setFeaturePermission(
                    security_origin, feature, QWebEnginePage.PermissionDeniedByUser
                )
                self.logger.info(f"Permiso de media denegado: {feature}")
        except Exception as e:
            self.logger.warning(f"Error concediendo permiso de media: {e}")
    
    
    
    
    def closeEvent(self, event):
        """Manejar cierre de ventana"""
        self.cleanup()
        event.accept()


# Función de conveniencia para crear la interfaz
def create_web_ui(llm_callback=None, config=None):
    """Crear y retornar una instancia de PySide6WebUI"""
    return PySide6WebUI(llm_callback, config)
