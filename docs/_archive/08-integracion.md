# 🔗 Fase 8: Integración (FULL STACK)
## Estado Actual
- Integración parcial operativa: LLMManager + voz WS conectados y probados (TTS/STT verificados).
- Frontend aún sin UI; conexión mock descrita en documento, REST API formal pendiente.
- Endpoints de voz expuestos vía WS local `ws://127.0.0.1:8765`; Docker listo pero no instalado en host.
- Próximos pasos: EventBus real, sincronización de estados, API REST `/query`, testing e2e.

## 🎯 Objetivos de esta Fase

- **Integrar todos los sistemas** en una solución cohesiva
- **Sincronización perfecta** entre componentes
- **Gestión de estados** mutuamente excluyentes
- **Testing end-to-end** completo
- **Documentación** de la integración

## ⏱️ Tiempo Estimado

**2 semanas** (10 días de trabajo)

## 🧩 Endpoints Clave (MVP)

- `POST /query` — Consulta principal al asistente
  - Body: `{ query: string, context?: string, use_knowledge_base?: boolean, use_memory?: boolean, stream?: boolean }`
  - Nota: Para UI estándar se usa `stream: false` (no streaming)
  - Respuesta: `{ response: string, processing_time: number, tokens_used?: number, context_used?: boolean }`
- `POST /clear-memory` — Limpia la memoria conversacional
- `POST /add-document` — Agrega contenido a la base de conocimiento
- `GET /status` — Estado del sistema (LLM, memoria, KB, uptime)

## 📋 Checklist de Tareas

### **Semana 1: Integración Core**
- [x] Integrar Backend LLM con RAG
- [x] Conectar Frontend con Backend (mock backend en `http://localhost:8001`)
- [ ] Sincronizar estados entre sistemas
- [ ] Implementar sistema de eventos centralizado
- [ ] Testing de integración básica

### **Semana 2: Características Avanzadas**
- [x] Integrar sistema de voz (opcional)
- [ ] Integrar sistema de visión (opcional)
- [ ] Implementar fine-tuning en producción
- [ ] Testing end-to-end completo
- [ ] Documentación de integración

## 🔧 Herramientas Necesarias

### **Integración**
- **EventBus**: Sistema de eventos centralizado
- **StateManager**: Gestión de estados globales
- **MessageQueue**: Cola de mensajes
- **CircuitBreaker**: Patrón de resilencia

### **Testing**
- **Playwright**: Testing e2e
- **Jest**: Testing unitario
- **Supertest**: Testing de API
- **MSW**: Mock de servicios

### **Monitoreo**
- **Prometheus**: Métricas
- **Grafana**: Dashboards
- **ELK Stack**: Logs
- **Health Checks**: Monitoreo de salud

## 🏗️ Arquitectura de Integración

### **📐 Sistema Integrado**

```
┌─────────────────────────────────────────────────────────────┐
│                    INTEGRATED SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│  EventBus + StateManager + MessageQueue + CircuitBreaker  │
│  • Gestión centralizada de eventos                        │
│  • Estados mutuamente excluyentes                         │
│  • Comunicación asíncrona entre componentes               │
│  • Resilencia y recuperación automática                   │
└─────────────────────────────────────────────────────────────┘
                                ↕️
┌─────────────────────────────────────────────────────────────┐
│                    COMPONENT INTEGRATION                   │
├─────────────────────────────────────────────────────────────┤
│  Backend LLM + RAG + Frontend + Voice + Vision            │
│  • Sincronización perfecta entre sistemas                 │
│  • Gestión de prioridades                                 │
│  • Manejo de conflictos                                   │
│  • Optimización de recursos                               │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Flujo de Integración**

```
User Input → EventBus → StateManager → Component Processing → Response → UI Update
```

## 🚀 Implementación

### **1. Sistema de Eventos Centralizado**

```python
# backend/app/core/event_bus.py
import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
import uuid
from datetime import datetime

class EventType(Enum):
    # Chat Events
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    TYPING_STARTED = "typing_started"
    TYPING_STOPPED = "typing_stopped"
    
    # Voice Events
    AUDIO_RECEIVED = "audio_received"
    AUDIO_PROCESSED = "audio_processed"
    TTS_STARTED = "tts_started"
    TTS_STOPPED = "tts_stopped"
    
    # Vision Events
    IMAGE_RECEIVED = "image_received"
    IMAGE_PROCESSED = "image_processed"
    OBJECT_DETECTED = "object_detected"
    
    # System Events
    USER_CONNECTED = "user_connected"
    USER_DISCONNECTED = "user_disconnected"
    SYSTEM_ERROR = "system_error"
    RESOURCE_LOW = "resource_low"

class Event:
    def __init__(self, event_type: EventType, data: Dict[str, Any], user_id: str = None):
        self.id = str(uuid.uuid4())
        self.type = event_type
        self.data = data
        self.user_id = user_id
        self.timestamp = datetime.utcnow()
        self.processed = False

class EventBus:
    """Sistema de eventos centralizado"""
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        self.logger = logging.getLogger(__name__)
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Suscribirse a un tipo de evento"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        self.logger.info(f"Subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Desuscribirse de un tipo de evento"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(handler)
                self.logger.info(f"Unsubscribed from {event_type.value}")
            except ValueError:
                pass
    
    async def publish(self, event: Event):
        """Publicar evento"""
        await self.event_queue.put(event)
        self.logger.debug(f"Published event {event.type.value}")
    
    async def start(self):
        """Iniciar procesamiento de eventos"""
        self.is_running = True
        self.logger.info("EventBus started")
        
        while self.is_running:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                await self._process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
    
    async def stop(self):
        """Detener procesamiento de eventos"""
        self.is_running = False
        self.logger.info("EventBus stopped")
    
    async def _process_event(self, event: Event):
        """Procesar evento"""
        if event.type in self.subscribers:
            handlers = self.subscribers[event.type]
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}")
        
        event.processed = True
        self.logger.debug(f"Processed event {event.type.value}")
```

### **2. Gestor de Estados Globales**

```python
# backend/app/core/state_manager.py
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio
import logging
from datetime import datetime, timedelta

class SystemState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    LISTENING = "listening"
    VISION_ACTIVE = "vision_active"
    ERROR = "error"

class UserState:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.current_state = SystemState.IDLE
        self.last_activity = datetime.utcnow()
        self.priority = 0
        self.active_sessions = []
        self.resource_usage = {
            "cpu": 0.0,
            "memory": 0.0,
            "gpu": 0.0
        }

class StateManager:
    """Gestor de estados globales del sistema"""
    
    def __init__(self):
        self.user_states: Dict[str, UserState] = {}
        self.global_state = SystemState.IDLE
        self.state_lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        self.state_history: List[Dict[str, Any]] = []
    
    async def get_user_state(self, user_id: str) -> UserState:
        """Obtener estado de usuario"""
        async with self.state_lock:
            if user_id not in self.user_states:
                self.user_states[user_id] = UserState(user_id)
            return self.user_states[user_id]
    
    async def set_user_state(self, user_id: str, state: SystemState, priority: int = 0):
        """Establecer estado de usuario"""
        async with self.state_lock:
            user_state = await self.get_user_state(user_id)
            old_state = user_state.current_state
            user_state.current_state = state
            user_state.priority = priority
            user_state.last_activity = datetime.utcnow()
            
            # Registrar cambio de estado
            self._log_state_change(user_id, old_state, state)
            
            # Actualizar estado global
            await self._update_global_state()
    
    async def can_transition(self, user_id: str, new_state: SystemState) -> bool:
        """Verificar si es posible transicionar a nuevo estado"""
        user_state = await self.get_user_state(user_id)
        current_state = user_state.current_state
        
        # Reglas de transición
        transitions = {
            SystemState.IDLE: [SystemState.PROCESSING, SystemState.LISTENING, SystemState.VISION_ACTIVE],
            SystemState.PROCESSING: [SystemState.IDLE, SystemState.SPEAKING, SystemState.ERROR],
            SystemState.SPEAKING: [SystemState.IDLE, SystemState.PROCESSING],
            SystemState.LISTENING: [SystemState.PROCESSING, SystemState.IDLE],
            SystemState.VISION_ACTIVE: [SystemState.PROCESSING, SystemState.IDLE],
            SystemState.ERROR: [SystemState.IDLE]
        }
        
        return new_state in transitions.get(current_state, [])
    
    async def get_available_actions(self, user_id: str) -> List[SystemState]:
        """Obtener acciones disponibles para usuario"""
        user_state = await self.get_user_state(user_id)
        current_state = user_state.current_state
        
        transitions = {
            SystemState.IDLE: [SystemState.PROCESSING, SystemState.LISTENING, SystemState.VISION_ACTIVE],
            SystemState.PROCESSING: [SystemState.IDLE, SystemState.SPEAKING, SystemState.ERROR],
            SystemState.SPEAKING: [SystemState.IDLE, SystemState.PROCESSING],
            SystemState.LISTENING: [SystemState.PROCESSING, SystemState.IDLE],
            SystemState.VISION_ACTIVE: [SystemState.PROCESSING, SystemState.IDLE],
            SystemState.ERROR: [SystemState.IDLE]
        }
        
        return transitions.get(current_state, [])
    
    async def _update_global_state(self):
        """Actualizar estado global del sistema"""
        if not self.user_states:
            self.global_state = SystemState.IDLE
            return
        
        # Determinar estado global basado en estados de usuarios
        active_states = [user.current_state for user in self.user_states.values()]
        
        if SystemState.ERROR in active_states:
            self.global_state = SystemState.ERROR
        elif SystemState.SPEAKING in active_states:
            self.global_state = SystemState.SPEAKING
        elif SystemState.PROCESSING in active_states:
            self.global_state = SystemState.PROCESSING
        elif SystemState.LISTENING in active_states:
            self.global_state = SystemState.LISTENING
        elif SystemState.VISION_ACTIVE in active_states:
            self.global_state = SystemState.VISION_ACTIVE
        else:
            self.global_state = SystemState.IDLE
    
    def _log_state_change(self, user_id: str, old_state: SystemState, new_state: SystemState):
        """Registrar cambio de estado"""
        change = {
            "user_id": user_id,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.state_history.append(change)
        
        # Mantener solo últimos 1000 cambios
        if len(self.state_history) > 1000:
            self.state_history = self.state_history[-1000:]
        
        self.logger.info(f"State change: {user_id} {old_state.value} -> {new_state.value}")
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema"""
        async with self.state_lock:
            return {
                "global_state": self.global_state.value,
                "active_users": len(self.user_states),
                "user_states": {
                    user_id: {
                        "state": user.current_state.value,
                        "priority": user.priority,
                        "last_activity": user.last_activity.isoformat(),
                        "active_sessions": len(user.active_sessions),
                        "resource_usage": user.resource_usage
                    }
                    for user_id, user in self.user_states.items()
                },
                "state_history_count": len(self.state_history)
            }
```

### **3. Sistema de Cola de Mensajes**

```python
# backend/app/core/message_queue.py
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import uuid

class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class Message:
    def __init__(self, content: str, priority: MessagePriority = MessagePriority.NORMAL, 
                 user_id: str = None, metadata: Dict[str, Any] = None):
        self.id = str(uuid.uuid4())
        self.content = content
        self.priority = priority
        self.user_id = user_id
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.processed = False
        self.retry_count = 0
        self.max_retries = 3

class MessageQueue:
    """Sistema de cola de mensajes"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queues: Dict[MessagePriority, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=max_size // 4)
            for priority in MessagePriority
        }
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        self.processors: List[Callable] = []
    
    async def enqueue(self, message: Message):
        """Agregar mensaje a la cola"""
        try:
            await self.queues[message.priority].put(message)
            self.logger.debug(f"Enqueued message {message.id} with priority {message.priority.value}")
        except asyncio.QueueFull:
            self.logger.warning(f"Queue full for priority {message.priority.value}")
            # Intentar con cola de menor prioridad
            await self._fallback_enqueue(message)
    
    async def _fallback_enqueue(self, message: Message):
        """Encolar en cola de menor prioridad si la principal está llena"""
        for priority in [MessagePriority.HIGH, MessagePriority.NORMAL, MessagePriority.LOW]:
            if priority != message.priority:
                try:
                    await self.queues[priority].put(message)
                    self.logger.info(f"Fallback enqueued message {message.id} in {priority.value}")
                    return
                except asyncio.QueueFull:
                    continue
        
        self.logger.error(f"Failed to enqueue message {message.id}")
    
    async def dequeue(self) -> Optional[Message]:
        """Desencolar mensaje de mayor prioridad"""
        # Procesar en orden de prioridad
        for priority in [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                        MessagePriority.NORMAL, MessagePriority.LOW]:
            try:
                message = self.queues[priority].get_nowait()
                return message
            except asyncio.QueueEmpty:
                continue
        
        return None
    
    async def start_processing(self):
        """Iniciar procesamiento de mensajes"""
        self.is_running = True
        self.logger.info("MessageQueue processing started")
        
        while self.is_running:
            try:
                message = await self.dequeue()
                if message:
                    await self._process_message(message)
                else:
                    await asyncio.sleep(0.1)  # Evitar CPU alto
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
    
    async def stop_processing(self):
        """Detener procesamiento de mensajes"""
        self.is_running = False
        self.logger.info("MessageQueue processing stopped")
    
    async def _process_message(self, message: Message):
        """Procesar mensaje individual"""
        try:
            for processor in self.processors:
                await processor(message)
            
            message.processed = True
            self.logger.debug(f"Processed message {message.id}")
        except Exception as e:
            message.retry_count += 1
            self.logger.error(f"Error processing message {message.id}: {e}")
            
            if message.retry_count < message.max_retries:
                # Reencolar para reintento
                await self.enqueue(message)
            else:
                self.logger.error(f"Message {message.id} failed after {message.max_retries} retries")
    
    def add_processor(self, processor: Callable):
        """Agregar procesador de mensajes"""
        self.processors.append(processor)
        self.logger.info(f"Added message processor: {processor.__name__}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de las colas"""
        stats = {}
        for priority, queue in self.queues.items():
            stats[priority.value] = {
                "size": queue.qsize(),
                "max_size": queue.maxsize
            }
        return stats
```

### **4. Circuit Breaker Pattern**

```python
# backend/app/core/circuit_breaker.py
import asyncio
import time
import logging
from typing import Callable, Any, Optional
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Implementación del patrón Circuit Breaker"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60, 
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.logger = logging.getLogger(__name__)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Ejecutar función con circuit breaker"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Verificar si se debe intentar reset"""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.timeout
    
    async def _on_success(self):
        """Manejar éxito"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.logger.info("Circuit breaker reset to CLOSED")
    
    async def _on_failure(self):
        """Manejar fallo"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Obtener estado del circuit breaker"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout
        }
```

### **5. Integración de Componentes**

```python
# backend/app/core/integration_manager.py
from typing import Dict, Any, Optional
import asyncio
import logging
from .event_bus import EventBus, Event, EventType
from .state_manager import StateManager, SystemState
from .message_queue import MessageQueue, Message, MessagePriority
from .circuit_breaker import CircuitBreaker

class IntegrationManager:
    """Gestor de integración de componentes"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.message_queue = MessageQueue()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logging.getLogger(__name__)
        
        # Configurar circuit breakers
        self._setup_circuit_breakers()
        
        # Configurar procesadores de mensajes
        self._setup_message_processors()
        
        # Configurar suscripciones de eventos
        self._setup_event_subscriptions()
    
    def _setup_circuit_breakers(self):
        """Configurar circuit breakers para cada componente"""
        components = ["llm", "rag", "voice", "vision", "finetuning"]
        
        for component in components:
            self.circuit_breakers[component] = CircuitBreaker(
                failure_threshold=3,
                timeout=30
            )
    
    def _setup_message_processors(self):
        """Configurar procesadores de mensajes"""
        self.message_queue.add_processor(self._process_chat_message)
        self.message_queue.add_processor(self._process_voice_message)
        self.message_queue.add_processor(self._process_vision_message)
    
    def _setup_event_subscriptions(self):
        """Configurar suscripciones de eventos"""
        self.event_bus.subscribe(EventType.MESSAGE_RECEIVED, self._handle_message_received)
        self.event_bus.subscribe(EventType.AUDIO_RECEIVED, self._handle_audio_received)
        self.event_bus.subscribe(EventType.IMAGE_RECEIVED, self._handle_image_received)
        self.event_bus.subscribe(EventType.SYSTEM_ERROR, self._handle_system_error)
    
    async def start(self):
        """Iniciar sistema de integración"""
        self.logger.info("Starting integration manager")
        
        # Iniciar componentes
        await self.event_bus.start()
        await self.message_queue.start_processing()
        
        self.logger.info("Integration manager started")
    
    async def stop(self):
        """Detener sistema de integración"""
        self.logger.info("Stopping integration manager")
        
        # Detener componentes
        await self.event_bus.stop()
        await self.message_queue.stop_processing()
        
        self.logger.info("Integration manager stopped")
    
    async def process_user_input(self, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Procesar entrada de usuario integrada"""
        try:
            # Verificar estado del usuario
            user_state = await self.state_manager.get_user_state(user_id)
            
            if not await self.state_manager.can_transition(user_id, SystemState.PROCESSING):
                return {
                    "success": False,
                    "error": "User is not in a state that allows processing",
                    "current_state": user_state.current_state.value
                }
            
            # Transicionar a estado de procesamiento
            await self.state_manager.set_user_state(user_id, SystemState.PROCESSING)
            
            # Publicar evento
            event = Event(
                EventType.MESSAGE_RECEIVED,
                {"user_id": user_id, "input": input_data},
                user_id
            )
            await self.event_bus.publish(event)
            
            # Procesar según tipo de entrada
            if "text" in input_data:
                return await self._process_text_input(user_id, input_data["text"])
            elif "audio" in input_data:
                return await self._process_audio_input(user_id, input_data["audio"])
            elif "image" in input_data:
                return await self._process_image_input(user_id, input_data["image"])
            else:
                return {"success": False, "error": "Unknown input type"}
                
        except Exception as e:
            self.logger.error(f"Error processing user input: {e}")
            await self.state_manager.set_user_state(user_id, SystemState.ERROR)
            return {"success": False, "error": str(e)}
    
    async def _process_text_input(self, user_id: str, text: str) -> Dict[str, Any]:
        """Procesar entrada de texto"""
        try:
            # Usar circuit breaker para LLM
            llm_breaker = self.circuit_breakers["llm"]
            result = await llm_breaker.call(self._call_llm, user_id, text)
            
            # Transicionar a estado idle
            await self.state_manager.set_user_state(user_id, SystemState.IDLE)
            
            return {"success": True, "result": result}
        except Exception as e:
            await self.state_manager.set_user_state(user_id, SystemState.ERROR)
            return {"success": False, "error": str(e)}
    
    async def _process_audio_input(self, user_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Procesar entrada de audio"""
        try:
            # Usar circuit breaker para voz
            voice_breaker = self.circuit_breakers["voice"]
            result = await voice_breaker.call(self._call_voice_service, user_id, audio_data)
            
            await self.state_manager.set_user_state(user_id, SystemState.IDLE)
            return {"success": True, "result": result}
        except Exception as e:
            await self.state_manager.set_user_state(user_id, SystemState.ERROR)
            return {"success": False, "error": str(e)}
    
    async def _process_image_input(self, user_id: str, image_data: bytes) -> Dict[str, Any]:
        """Procesar entrada de imagen"""
        try:
            # Usar circuit breaker para visión
            vision_breaker = self.circuit_breakers["vision"]
            result = await vision_breaker.call(self._call_vision_service, user_id, image_data)
            
            await self.state_manager.set_user_state(user_id, SystemState.IDLE)
            return {"success": True, "result": result}
        except Exception as e:
            await self.state_manager.set_user_state(user_id, SystemState.ERROR)
            return {"success": False, "error": str(e)}
    
    async def _call_llm(self, user_id: str, text: str) -> Dict[str, Any]:
        """Llamar servicio LLM"""
        # Implementación simplificada
        return {"response": f"Processed: {text}", "user_id": user_id}
    
    async def _call_voice_service(self, user_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Llamar servicio de voz"""
        # Implementación simplificada
        return {"transcript": "Audio processed", "user_id": user_id}
    
    async def _call_vision_service(self, user_id: str, image_data: bytes) -> Dict[str, Any]:
        """Llamar servicio de visión"""
        # Implementación simplificada
        return {"objects": ["object1", "object2"], "user_id": user_id}
    
    async def _handle_message_received(self, event: Event):
        """Manejar evento de mensaje recibido"""
        self.logger.info(f"Handling message received event for user {event.user_id}")
    
    async def _handle_audio_received(self, event: Event):
        """Manejar evento de audio recibido"""
        self.logger.info(f"Handling audio received event for user {event.user_id}")
    
    async def _handle_image_received(self, event: Event):
        """Manejar evento de imagen recibida"""
        self.logger.info(f"Handling image received event for user {event.user_id}")
    
    async def _handle_system_error(self, event: Event):
        """Manejar evento de error del sistema"""
        self.logger.error(f"Handling system error event: {event.data}")
    
    async def _process_chat_message(self, message: Message):
        """Procesar mensaje de chat"""
        self.logger.info(f"Processing chat message: {message.content}")
    
    async def _process_voice_message(self, message: Message):
        """Procesar mensaje de voz"""
        self.logger.info(f"Processing voice message: {message.content}")
    
    async def _process_vision_message(self, message: Message):
        """Procesar mensaje de visión"""
        self.logger.info(f"Processing vision message: {message.content}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema integrado"""
        return {
            "state_manager": await self.state_manager.get_system_stats(),
            "message_queue": await self.message_queue.get_queue_stats(),
            "circuit_breakers": {
                name: breaker.get_state()
                for name, breaker in self.circuit_breakers.items()
            }
        }
```

## 🧪 Testing de Integración

### **1. Tests End-to-End**

```python
# backend/tests/test_integration.py
import pytest
import asyncio
from app.core.integration_manager import IntegrationManager
from app.core.event_bus import Event, EventType
from app.core.state_manager import SystemState

@pytest.mark.asyncio
async def test_integration_manager():
    """Test del gestor de integración"""
    manager = IntegrationManager()
    
    # Iniciar sistema
    await manager.start()
    
    try:
        # Test procesamiento de texto
        result = await manager.process_user_input("user1", {"text": "Hello"})
        assert result["success"] is True
        
        # Test procesamiento de audio
        result = await manager.process_user_input("user1", {"audio": b"fake_audio"})
        assert result["success"] is True
        
        # Test procesamiento de imagen
        result = await manager.process_user_input("user1", {"image": b"fake_image"})
        assert result["success"] is True
        
    finally:
        await manager.stop()

@pytest.mark.asyncio
async def test_event_bus():
    """Test del sistema de eventos"""
    from app.core.event_bus import EventBus, Event, EventType
    
    bus = EventBus()
    events_received = []
    
    async def handler(event):
        events_received.append(event)
    
    bus.subscribe(EventType.MESSAGE_RECEIVED, handler)
    
    # Iniciar bus
    await bus.start()
    
    try:
        # Publicar evento
        event = Event(EventType.MESSAGE_RECEIVED, {"test": "data"}, "user1")
        await bus.publish(event)
        
        # Esperar procesamiento
        await asyncio.sleep(0.1)
        
        assert len(events_received) == 1
        assert events_received[0].type == EventType.MESSAGE_RECEIVED
        
    finally:
        await bus.stop()

@pytest.mark.asyncio
async def test_state_manager():
    """Test del gestor de estados"""
    from app.core.state_manager import StateManager, SystemState
    
    manager = StateManager()
    
    # Test transición de estado
    await manager.set_user_state("user1", SystemState.PROCESSING)
    user_state = await manager.get_user_state("user1")
    assert user_state.current_state == SystemState.PROCESSING
    
    # Test acciones disponibles
    actions = await manager.get_available_actions("user1")
    assert SystemState.IDLE in actions
    assert SystemState.SPEAKING in actions
```

### **2. Tests de Performance**

```python
# backend/tests/test_performance.py
import pytest
import asyncio
import time
from app.core.integration_manager import IntegrationManager

@pytest.mark.asyncio
async def test_performance_under_load():
    """Test de rendimiento bajo carga"""
    manager = IntegrationManager()
    await manager.start()
    
    try:
        # Simular carga
        start_time = time.time()
        tasks = []
        
        for i in range(100):
            task = manager.process_user_input(f"user{i}", {"text": f"Message {i}"})
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verificar que todos los resultados sean exitosos
        success_count = sum(1 for result in results if result["success"])
        assert success_count == 100
        
        # Verificar tiempo de procesamiento
        processing_time = end_time - start_time
        assert processing_time < 10.0  # Menos de 10 segundos
        
    finally:
        await manager.stop()

@pytest.mark.asyncio
async def test_memory_usage():
    """Test de uso de memoria"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    manager = IntegrationManager()
    await manager.start()
    
    try:
        # Procesar muchos mensajes
        for i in range(1000):
            await manager.process_user_input(f"user{i}", {"text": f"Message {i}"})
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Verificar que el aumento de memoria sea razonable
        assert memory_increase < 100 * 1024 * 1024  # Menos de 100MB
        
    finally:
        await manager.stop()
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Tiempo de Respuesta**: < 2s para operaciones integradas
- **Disponibilidad**: 99.9% uptime
- **Throughput**: > 100 requests/minuto
- **Latencia**: < 500ms entre componentes
- **Memoria**: < 1GB para sistema completo

### **🎯 Objetivos de Funcionalidad**
- **Integración**: Todos los componentes funcionando juntos
- **Estados**: Transiciones correctas entre estados
- **Eventos**: Comunicación asíncrona funcionando
- **Resilencia**: Recuperación automática de fallos
- **Testing**: > 95% cobertura de código

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [ ] **Sistema integrado** completamente funcional
- [ ] **Estados mutuamente excluyentes** funcionando
- [ ] **Sistema de eventos** operativo
- [ ] **Cola de mensajes** funcionando
- [ ] **Circuit breakers** implementados
- [ ] **Testing end-to-end** pasando
- [ ] **Rendimiento** dentro de métricas objetivo
- [ ] **Preparación** para optimización

### **🎯 Entregables de esta Fase**
- [ ] **Sistema integrado** completamente funcional
- [ ] **Gestión de estados** robusta
- [ ] **Sistema de eventos** centralizado
- [ ] **Cola de mensajes** operativa
- [ ] **Circuit breakers** implementados
- [ ] **Testing suite** completa
- [ ] **Documentación** de integración
- [ ] **Preparación** para optimización

## 🚀 Siguiente Fase

Una vez completada esta fase, continuar con [**Fase 9: Optimización**](./09-optimizacion.md)

### **📋 Preparación para Fase 9**
- [ ] Sistema integrado funcionando
- [ ] Todos los componentes sincronizados
- [ ] Testing end-to-end pasando
- [ ] Documentación completa
- [ ] Métricas de rendimiento

---

**🎉 ¡Con esta fase tendrás un sistema completamente integrado y funcional!**

*Recuerda: La integración es la clave del éxito. Asegúrate de que todos los componentes trabajen en armonía.* 🚀

## Estado actual de endpoints (MVP)
- `GET /status` — operativo (mock backend y servidor de voz)
- `POST /query` — camino no streaming activo (`{"stream": false}`) retorna JSON
- `POST /clear-memory` — definido (pendiente validación e2e)
- `POST /add-document` — definido (pendiente prueba con archivos locales)
- WebSocket de voz — `ws://localhost:8010/ws/stt` operativo con Vosk pequeño
- WebSocket TTS — `ws://localhost:8010/ws/tts` operativo vía Coqui XTTS v2 (speaker_wav temporal; fallback pyttsx3)

## Checklist (avance)
- [x] Conectar Frontend (Axios) con `/query` no streaming
- [x] Validar `VoiceWsClient` con `ws://localhost:8010/ws/stt`
- [ ] Validar `/clear-memory` y `/add-document`
- [ ] Integrar WebSocket de chat general (mensajería)
