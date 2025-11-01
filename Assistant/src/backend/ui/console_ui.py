"""
Implementación de interfaz de consola para el asistente.
Mantiene la funcionalidad actual del modo interactivo.
"""

import sys
from typing import Dict, Any, Optional, Callable
from .ui_abstraction import UIInterface, UIState


class ConsoleUI(UIInterface):
    """Interfaz de consola para el asistente"""
    
    def __init__(self):
        self.components: Optional[Dict[str, Any]] = None
        self.user_input_callback: Optional[Callable[[str], None]] = None
        self.mic_enabled = False
        self.tts_enabled = False
        self.current_status = UIState.IDLE
    
    def initialize(self, components: Dict[str, Any]) -> None:
        """Inicializar la interfaz con los componentes del sistema"""
        self.components = components
        print("\n🤖 Asistente Personal Leonel - Modo Interactivo")
        print("=" * 50)
        print("📋 Comandos disponibles:")
        print("  /help - Mostrar ayuda completa")
        print("  /status - Ver estado del sistema")
        print("  /mic on|off - Activar/desactivar micrófono")
        print("  /tts on|off - Activar/desactivar síntesis de voz")
        print("  /salir - Terminar sesión")
        print("=" * 50)
        print("💬 Escribe tu mensaje o usa un comando:")
    
    def append_message(self, message: str, sender: str = "assistant") -> None:
        """Agregar mensaje a la conversación"""
        if sender == "assistant":
            print(f"\n🤖 Asistente: {message}")
        else:
            print(f"\n👤 Tú: {message}")
    
    def toggle_mic(self, enabled: bool) -> None:
        """Activar/desactivar micrófono"""
        self.mic_enabled = enabled
        status = "activado" if enabled else "desactivado"
        print(f"\n🎤 Micrófono {status}")
    
    def toggle_tts(self, enabled: bool) -> None:
        """Activar/desactivar síntesis de voz"""
        self.tts_enabled = enabled
        status = "activado" if enabled else "desactivado"
        print(f"\n🔊 Síntesis de voz {status}")
    
    def set_status(self, status: UIState, message: str = "") -> None:
        """Actualizar estado de la interfaz"""
        self.current_status = status
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
        
        print(f"\n📊 Estado: {status_text}")
    
    def set_user_input_callback(self, callback: Callable[[str], None]) -> None:
        """Establecer callback para entrada del usuario"""
        self.user_input_callback = callback
    
    def show_error(self, error: str) -> None:
        """Mostrar error al usuario"""
        print(f"\n❌ Error: {error}")
    
    def run(self) -> None:
        """Ejecutar la interfaz de consola"""
        if not self.user_input_callback:
            print("❌ No se ha establecido callback para entrada del usuario")
            return
        
        try:
            while True:
                try:
                    user_input = input("\n👤 Tú: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n\n👋 ¡Hasta luego! Sesión terminada.")
                    break
                
                if not user_input:
                    continue
                
                # Procesar comandos especiales
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue
                
                # Procesar entrada normal
                self.user_input_callback(user_input)
                
        except Exception as e:
            print(f"\n❌ Error en interfaz de consola: {e}")
    
    def _handle_command(self, command: str) -> None:
        """Manejar comandos especiales de la consola"""
        cmd_lower = command.lower()
        
        if cmd_lower in ["/salir", "/exit", "/quit"]:
            print("\n👋 ¡Hasta luego! Sesión terminada.")
            sys.exit(0)
        
        elif cmd_lower == "/help":
            self._show_help()
        
        elif cmd_lower == "/status":
            self._show_status()
        
        elif cmd_lower.startswith("/mic "):
            self._handle_mic_command(command)
        
        elif cmd_lower.startswith("/tts "):
            self._handle_tts_command(command)
        
        else:
            # Delegar comando al sistema principal si está disponible
            if self.user_input_callback:
                self.user_input_callback(command)
            else:
                print(f"❌ Comando no reconocido: {command}")
                print("💡 Usa /help para ver todos los comandos disponibles")
    
    def _show_help(self) -> None:
        """Mostrar ayuda completa"""
        print("\n🔧 SISTEMA:")
        print("  /help        - Mostrar esta ayuda")
        print("  /salir       - Salir del programa")
        print("  /status      - Ver estado de todos los componentes")
        print("  /resources   - Ver información detallada de recursos")
        print("\n💾 MEMORIA:")
        print("  /clear       - Limpiar toda la memoria")
        print("  /memory      - Ver estado de la memoria")
        print("  /list_short  - Ver interacciones de memoria a corto plazo")
        print("  /list_long   - Ver interacciones de memoria a largo plazo")
        print("  /delete_short [índice] - Borrar interacción específica (corto plazo)")
        print("  /delete_long [índice]  - Borrar interacción específica (largo plazo)")
        print("\n📚 CONOCIMIENTO:")
        print("  /rag on|off  - Activar/desactivar búsqueda RAG")
        print("  /add <texto> - Agregar texto a la base de conocimiento")
        print("\n🎤 AUDIO:")
        print("  /mic on|off  - Activar/desactivar micrófono")
        print("  /tts on|off  - Activar/desactivar síntesis de voz")
        print("\n💬 Para chatear, simplemente escribe tu mensaje")
    
    def _show_status(self) -> None:
        """Mostrar estado del sistema"""
        print(f"\n📊 Estado del sistema:")
        print(f"  🎤 Micrófono: {'Activado' if self.mic_enabled else 'Desactivado'}")
        print(f"  🔊 TTS: {'Activado' if self.tts_enabled else 'Desactivado'}")
        print(f"  📊 Estado actual: {self.current_status.value}")
        
        if self.components:
            print(f"  🧠 Componentes cargados: {len(self.components)}")
            for name, component in self.components.items():
                status = "✅" if component else "❌"
                print(f"    {status} {name}")
    
    def _handle_mic_command(self, command: str) -> None:
        """Manejar comando de micrófono"""
        parts = command.split()
        if len(parts) != 2:
            print("❌ Uso: /mic on|off")
            return
        
        action = parts[1].lower()
        if action == "on":
            self.toggle_mic(True)
        elif action == "off":
            self.toggle_mic(False)
        else:
            print("❌ Uso: /mic on|off")
    
    def _handle_tts_command(self, command: str) -> None:
        """Manejar comando de TTS"""
        parts = command.split()
        if len(parts) != 2:
            print("❌ Uso: /tts on|off")
            return
        
        action = parts[1].lower()
        if action == "on":
            self.toggle_tts(True)
        elif action == "off":
            self.toggle_tts(False)
        else:
            print("❌ Uso: /tts on|off")
    
    def cleanup(self) -> None:
        """Limpiar recursos de la interfaz"""
        print("\n🧹 Limpiando interfaz de consola...")
        self.components = None
        self.user_input_callback = None

