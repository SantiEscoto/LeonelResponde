# 🧠 Fase 2: Backend LLM (Core)

## Estado Actual

- LLMManager inicializa y carga un modelo (Mistral) según logs recientes.
- Integración con el sistema de voz: flujo LLM → TTS probado vía WS.
- Health check degradado observado por memoria alta en host; pendiente optimización.
- Próximo: API REST formal con FastAPI, endpoints de chat/estado y testing.

## 🎯 Objetivos de esta Fase

- **Implementar motor LLM** funcional y optimizado
- **Sistema de memoria** avanzado por usuario
- **API REST** robusta y escalable
- **Detección automática de hardware** y optimización
- **Testing completo** del core del sistema

## ⏱️ Tiempo Estimado

**2 semanas** (10 días de trabajo)

## 📋 Checklist de Tareas

### **Semana 1: Core LLM y Memoria**
- [ ] Configurar Ollama
- [x] Configurar modelos LLM (local con llama-cpp)
- [x] Implementar sistema de memoria por usuario
- [x] Crear API REST básica
- [ ] Sistema de detección de hardware
- [ ] Testing del core LLM

### **Semana 2: Optimización y Testing**
- [ ] Optimizar rendimiento para hardware limitado
- [ ] Implementar sistema de atención social
- [ ] Testing completo del backend
- [ ] Documentación de la API
- [ ] Preparación para siguiente fase

## 🔧 Herramientas Necesarias

### **Backend Core**
- **Python 3.11+**: Lenguaje principal
- **FastAPI**: Framework web
- **SQLite**: Base de datos ligera
- **Ollama**: Gestión de modelos LLM
- **LangChain**: Framework para LLM

### **IA y ML**
- **Sentence Transformers**: Embeddings
- **FAISS**: Base de datos vectorial
- **PyTorch**: Deep learning
- **Transformers**: Modelos de Hugging Face

### **Testing y Calidad**
- **pytest**: Testing unitario
- **pytest-asyncio**: Testing asíncrono
- **black**: Formateo de código
- **flake8**: Linting
- **mypy**: Type checking

## 🏗️ Arquitectura del Backend

### **📐 Componentes Principales**

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND CORE                            │
├─────────────────────────────────────────────────────────────┤
│  FastAPI + SQLite + Redis + Ollama                        │
│  • API REST para atención social                         │
│  • Base de datos social por usuario                      │
│  • Cache de relaciones y memorias                        │
│  • Gestión de "atención" como persona real               │
└─────────────────────────────────────────────────────────────┘
                                ↕️
┌─────────────────────────────────────────────────────────────┐
│                    IA SOCIAL (Edge Optimized)             │
├─────────────────────────────────────────────────────────────┤
│  Ollama + LangChain + FAISS + Social Memory              │
│  • LLM con personalidad social                            │
│  • Memoria de relaciones entre usuarios                  │
│  • Sistema de "atención" y prioridades                   │
│  • Gestión natural de interrupciones                     │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Flujo de Datos**

```
User Input → API → LLM Service → Memory Service → Response → API → User
```

## 🚀 Implementación

### **1. Configuración del Proyecto**

```bash
# Crear estructura del proyecto
mkdir asistente-ia-universal
cd asistente-ia-universal

# Backend
mkdir -p backend/{app,models,tests}
mkdir -p backend/app/{api,core,services,utils}

# Frontend (para siguiente fase)
mkdir -p frontend/{src,public}
mkdir -p frontend/src/{components,pages,hooks,services,store,types}

# AI
mkdir -p ai/{llm,memory,knowledge,voice,vision}

# Configuración
mkdir -p config/{development,production,hardware}
```

### **2. Dependencias Python**

```python
# requirements.txt
# Core Backend
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.4.2
sqlalchemy==2.0.23
alembic==1.12.1

# AI/ML
ollama==0.1.7
langchain==0.0.350
sentence-transformers==2.2.2
faiss-cpu==1.7.4
torch==2.0.1
transformers==4.35.2

# Database
sqlite3
redis==5.0.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
mypy==1.7.1

# Utils
python-dotenv==1.0.0
psutil==5.9.6
```

### **3. Configuración Base**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./asistente.db"
    
    # AI Models
    llm_model: str = "mistral:7b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Hardware Detection
    auto_detect_hardware: bool = True
    max_users: int = 6
    
    # Security
    secret_key: str = "your-secret-key-here"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### **4. Sistema de Detección de Hardware**

```python
# backend/app/core/hardware_detector.py
import platform
import psutil
import torch
from typing import Dict, Any, Optional

class UniversalHardwareDetector:
    """Detector universal de hardware para optimización automática"""
    
    def __init__(self):
        self.system_info = self._detect_system()
        self.optimization_config = self._get_optimization_config()
    
    def _detect_system(self) -> Dict[str, Any]:
        """Detectar tipo de hardware y capacidades"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Detectar tipo de dispositivo
        if "jetson" in platform.platform().lower():
            device_type = "jetson_nano"
        elif "raspberry" in platform.platform().lower():
            device_type = "raspberry_pi"
        elif system == "linux" and "arm" in machine:
            device_type = "arm_linux"
        elif system == "windows" or system == "darwin":
            device_type = "desktop"
        else:
            device_type = "unknown"
        
        return {
            "device_type": device_type,
            "cpu_cores": psutil.cpu_count(),
            "total_memory": psutil.virtual_memory().total,
            "available_memory": psutil.virtual_memory().available,
            "has_gpu": torch.cuda.is_available(),
            "gpu_memory": torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else 0,
            "system": system,
            "architecture": machine
        }
    
    def _get_optimization_config(self) -> Dict[str, Any]:
        """Configuración optimizada según hardware detectado"""
        memory_gb = self.system_info["total_memory"] / (1024**3)
        cpu_cores = self.system_info["cpu_cores"]
        has_gpu = self.system_info["has_gpu"]
        
        if self.system_info["device_type"] == "jetson_nano":
            return {
                "llm_model": "mistral:7b",
                "quantization": "Q4_K_M",
                "max_users": 3,
                "batch_size": 1,
                "gpu_layers": 10,
                "threads": 2
            }
        elif self.system_info["device_type"] == "raspberry_pi":
            return {
                "llm_model": "phi3:medium",
                "quantization": "Q4_K_S",
                "max_users": 2,
                "batch_size": 1,
                "gpu_layers": 0,
                "threads": 1
            }
        elif memory_gb < 4:
            return {
                "llm_model": "phi3:medium",
                "quantization": "Q4_K_S",
                "max_users": 2,
                "batch_size": 1,
                "gpu_layers": 0,
                "threads": 1
            }
        elif memory_gb < 8:
            return {
                "llm_model": "mistral:7b",
                "quantization": "Q4_K_M",
                "max_users": 4,
                "batch_size": 2,
                "gpu_layers": 5 if has_gpu else 0,
                "threads": 2
            }
        else:
            return {
                "llm_model": "mistral:8b",
                "quantization": "Q4_K_M",
                "max_users": 6,
                "batch_size": 4,
                "gpu_layers": 20 if has_gpu else 0,
                "threads": 4
            }
```

### **5. Sistema de Memoria por Usuario**

```python
# backend/app/services/memory_service.py
from typing import Dict, List, Optional
import sqlite3
from datetime import datetime, timedelta

class UserMemoryService:
    """Servicio de memoria específico por usuario"""
    
    def __init__(self, db_path: str = "user_memories.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Inicializar base de datos de memorias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_memories 
            ON user_memories(user_id, memory_type, importance)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_memory(self, user_id: str, memory_type: str, content: str, importance: float = 0.5):
        """Agregar memoria para usuario específico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_memories (user_id, memory_type, content, importance)
            VALUES (?, ?, ?, ?)
        ''', (user_id, memory_type, content, importance))
        
        conn.commit()
        conn.close()
    
    def get_user_memories(self, user_id: str, memory_type: str = None, limit: int = 10) -> List[Dict]:
        """Obtener memorias de usuario específico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if memory_type:
            cursor.execute('''
                SELECT content, importance, created_at, last_accessed
                FROM user_memories
                WHERE user_id = ? AND memory_type = ?
                ORDER BY importance DESC, last_accessed DESC
                LIMIT ?
            ''', (user_id, memory_type, limit))
        else:
            cursor.execute('''
                SELECT content, importance, created_at, last_accessed
                FROM user_memories
                WHERE user_id = ?
                ORDER BY importance DESC, last_accessed DESC
                LIMIT ?
            ''', (user_id, limit))
        
        memories = []
        for row in cursor.fetchall():
            memories.append({
                "content": row[0],
                "importance": row[1],
                "created_at": row[2],
                "last_accessed": row[3]
            })
        
        conn.close()
        return memories
```

### **6. API REST con FastAPI**

```python
# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from ..services.chat_service import ChatService
from ..core.auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

class MessageRequest(BaseModel):
    content: str
    session_id: str = None

class MessageResponse(BaseModel):
    message: str
    session_id: str
    timestamp: str

@router.post("/send", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    current_user = Depends(get_current_user),
    chat_service: ChatService = Depends()
):
    """Enviar mensaje al asistente"""
    try:
        response = await chat_service.process_message(
            user_id=current_user.id,
            message=request.content,
            session_id=request.session_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### **7. Servicio de Chat**

```python
# backend/app/services/chat_service.py
from ..ai.llm.llm_service import LLMService
from ..ai.memory.memory_service import MemoryService
from ..ai.knowledge.rag_service import RAGService
from ..models.database import get_db
from sqlalchemy.orm import Session

class ChatService:
    def __init__(self):
        self.llm = LLMService()
        self.memory = MemoryService()
        self.rag = RAGService("knowledge/")
    
    async def process_message(
        self, 
        user_id: str, 
        message: str, 
        session_id: str = None
    ) -> dict:
        """Procesar mensaje completo con RAG y memoria"""
        
        # 1. Recuperar contexto relevante
        relevant_memories = self.memory.retrieve_relevant_memories(message)
        relevant_docs = self.rag.retrieve_relevant_docs(message)
        
        # 2. Construir contexto completo
        context = self._build_context(relevant_memories, relevant_docs)
        
        # 3. Generar respuesta con LLM
        response = await self.llm.generate_response(message, context)
        
        # 4. Guardar en memoria
        self.memory.add_conversation(message, response)
        
        return {
            "message": response,
            "session_id": session_id or f"session_{user_id}_{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _build_context(self, memories: List[str], docs: List[str]) -> str:
        """Construir contexto completo"""
        context_parts = []
        
        if memories:
            context_parts.append("Memorias relevantes:")
            context_parts.extend(memories)
        
        if docs:
            context_parts.append("Documentos relevantes:")
            context_parts.extend(docs)
        
        return "\n\n".join(context_parts)
```

## 🧪 Testing del Backend

### **1. Tests Unitarios**

```python
# backend/tests/test_chat_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_send_message():
    response = client.post(
        "/api/chat/send",
        json={"content": "Hola, ¿cómo estás?"}
    )
    assert response.status_code == 200
    assert "message" in response.json()

def test_chat_with_context():
    # Enviar mensaje inicial
    response1 = client.post(
        "/api/chat/send",
        json={"content": "Mi nombre es Juan"}
    )
    
    # Enviar mensaje de seguimiento
    response2 = client.post(
        "/api/chat/send",
        json={"content": "¿Cuál es mi nombre?"}
    )
    
    assert "Juan" in response2.json()["message"]
```

### **2. Tests de Rendimiento**

```python
# backend/tests/test_performance.py
import pytest
import time
from app.services.chat_service import ChatService

def test_response_time():
    """Test que las respuestas sean < 2 segundos"""
    chat_service = ChatService()
    
    start_time = time.time()
    response = chat_service.process_message("user1", "Hola")
    end_time = time.time()
    
    assert (end_time - start_time) < 2.0
    assert response["message"] is not None
```

## 📊 Métricas de Éxito

### **🎯 Objetivos Técnicos**
- **Tiempo de Respuesta**: < 2 segundos
- **Disponibilidad**: 99.9% uptime
- **Memoria**: < 512MB RAM
- **CPU**: < 25% uso promedio
- **Precisión**: > 95% respuestas relevantes

### **🎯 Objetivos de Funcionalidad**
- **Sistema de Memoria**: Funcional por usuario
- **API REST**: Todos los endpoints funcionando
- **Detección de Hardware**: Automática y optimizada
- **Testing**: > 90% cobertura de código
- **Documentación**: 100% de funciones documentadas

## ✅ Criterios de Éxito

### **📋 Checklist de Validación**
- [ ] **Ollama funcionando** con modelo cargado
- [x] **API REST** respondiendo correctamente
- [x] **Sistema de memoria** por usuario funcional
- [ ] **Detección de hardware** automática
- [ ] **Testing completo** pasando
- [ ] **Documentación** de la API completa
- [ ] **Rendimiento** dentro de métricas objetivo
- [ ] **Preparación** para siguiente fase

### **🎯 Entregables de esta Fase**
- [ ] **Backend LLM** completamente funcional
- [ ] **API REST** robusta y documentada
- [ ] **Sistema de memoria** por usuario
- [ ] **Detección de hardware** automática
- [ ] **Testing suite** completa
- [ ] **Documentación** técnica
- [ ] **Configuración** optimizada
- [ ] **Preparación** para RAG

## 🚀 Siguiente Fase

Una vez completada esta fase, continuar con [**Fase 3: Base de Conocimiento RAG**](./03-conocimiento-rag.md)

### **📋 Preparación para Fase 3**
- [ ] Backend LLM funcionando
- [ ] API REST estable
- [ ] Sistema de memoria operativo
- [ ] Testing completo
- [ ] Documentación actualizada

---

**🎉 ¡Con esta fase tendrás el motor principal de tu asistente funcionando!**

*Recuerda: El backend es el corazón del sistema. Tómate el tiempo necesario para hacerlo robusto y escalable.* 🚀
