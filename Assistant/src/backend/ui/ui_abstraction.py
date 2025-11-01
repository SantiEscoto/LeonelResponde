"""
Capa de abstracción para UI del asistente.
Permite cambiar entre diferentes interfaces (consola, PySide6, etc.) sin modificar la lógica de negocio.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from enum import Enum


class UIState(Enum):
    """Estados posibles de la interfaz de usuario"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class UIInterface(ABC):
    """Interfaz abstracta para diferentes tipos de UI"""
    
    @abstractmethod
    def initialize(self, components: Dict[str, Any]) -> None:
        """Inicializar la interfaz con los componentes del sistema"""
        pass
    
    @abstractmethod
    def append_message(self, message: str, sender: str = "assistant") -> None:
        """Agregar mensaje a la conversación"""
        pass
    
    @abstractmethod
    def toggle_mic(self, enabled: bool) -> None:
        """Activar/desactivar micrófono"""
        pass
    
    @abstractmethod
    def toggle_tts(self, enabled: bool) -> None:
        """Activar/desactivar síntesis de voz"""
        pass
    
    @abstractmethod
    def set_status(self, status: UIState, message: str = "") -> None:
        """Actualizar estado de la interfaz"""
        pass
    
    @abstractmethod
    def set_user_input_callback(self, callback: Callable[[str], None]) -> None:
        """Establecer callback para entrada del usuario"""
        pass
    
    @abstractmethod
    def show_error(self, error: str) -> None:
        """Mostrar error al usuario"""
        pass
    
    @abstractmethod
    def run(self) -> None:
        """Ejecutar la interfaz"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Limpiar recursos de la interfaz"""
        pass


class UIManager:
    """Gestor de interfaz de usuario que permite cambiar entre diferentes tipos"""
    
    def __init__(self):
        self.current_ui: Optional[UIInterface] = None
        self.components: Optional[Dict[str, Any]] = None
        self.user_input_callback: Optional[Callable[[str], None]] = None
    
    def set_ui(self, ui: UIInterface) -> None:
        """Establecer la interfaz de usuario actual"""
        if self.current_ui:
            self.current_ui.cleanup()
        
        self.current_ui = ui
        
        if self.components:
            ui.initialize(self.components)
        
        if self.user_input_callback:
            ui.set_user_input_callback(self.user_input_callback)
    
    def initialize(self, components: Dict[str, Any]) -> None:
        """Inicializar el gestor con los componentes del sistema"""
        self.components = components
        if self.current_ui:
            self.current_ui.initialize(components)
    
    def set_user_input_callback(self, callback: Callable[[str], None]) -> None:
        """Establecer callback para entrada del usuario"""
        self.user_input_callback = callback
        if self.current_ui:
            self.current_ui.set_user_input_callback(callback)
    
    def append_message(self, message: str, sender: str = "assistant") -> None:
        """Agregar mensaje a la conversación"""
        if self.current_ui:
            self.current_ui.append_message(message, sender)
    
    def toggle_mic(self, enabled: bool) -> None:
        """Activar/desactivar micrófono"""
        if self.current_ui:
            self.current_ui.toggle_mic(enabled)
    
    def toggle_tts(self, enabled: bool) -> None:
        """Activar/desactivar síntesis de voz"""
        if self.current_ui:
            self.current_ui.toggle_tts(enabled)
    
    def set_status(self, status: UIState, message: str = "") -> None:
        """Actualizar estado de la interfaz"""
        if self.current_ui:
            self.current_ui.set_status(status, message)
    
    def show_error(self, error: str) -> None:
        """Mostrar error al usuario"""
        if self.current_ui:
            self.current_ui.show_error(error)
    
    def run(self) -> None:
        """Ejecutar la interfaz actual"""
        if self.current_ui:
            self.current_ui.run()
    
    def cleanup(self) -> None:
        """Limpiar recursos"""
        if self.current_ui:
            self.current_ui.cleanup()
            self.current_ui = None

