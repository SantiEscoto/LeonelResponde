# Standard library imports
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Third-party imports
from fastapi import FastAPI, HTTPException, Body, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Local imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from backend.llm.model_manager import LLMManager
from backend.llm.memory_manager import MemoryManager
from backend.llm.knowledge_base import KnowledgeBase
from backend.utils.logger import get_logger
import config

# Configurar logger
logger = get_logger("API")

# Modelos de datos para la API
class QueryRequest(BaseModel):
    query: str = Field(..., description="Texto de la consulta al LLM")
    context: Optional[str] = Field(None, description="Contexto adicional para la consulta")
    use_knowledge_base: bool = Field(False, description="Usar base de conocimiento para RAG")
    use_memory: bool = Field(True, description="Usar memoria de conversación")

class QueryResponse(BaseModel):
    response: str = Field(..., description="Respuesta del LLM")
    processing_time: float = Field(..., description="Tiempo de procesamiento en segundos")
    tokens_used: Optional[int] = Field(None, description="Tokens utilizados en la consulta")
    context_used: Optional[bool] = Field(None, description="Si se utilizó contexto adicional")

class StatusResponse(BaseModel):
    status: str = Field(..., description="Estado del sistema")
    llm: Dict[str, Any] = Field(..., description="Información del modelo LLM")
    memory: Optional[Dict[str, Any]] = Field(None, description="Información de la memoria")
    knowledge_base: Optional[Dict[str, Any]] = Field(None, description="Información de la base de conocimiento")
    uptime: float = Field(..., description="Tiempo de actividad en segundos")

# Crear aplicación FastAPI
app = FastAPI(
    title="Leonel Responde API",
    description="API REST para el asistente offline Leonel Responde",
    version="0.1.0"
)

# Configurar CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a orígenes específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales
start_time = time.time()
llm_manager = None
memory_manager = None
knowledge_base = None

@app.on_event("startup")
async def startup_event():
    """
    Inicializa los componentes del sistema al iniciar la API
    """
    global llm_manager, memory_manager, knowledge_base
    
    logger.info("🚀 Iniciando API de Leonel Responde...")
    
    # Inicializar LLM Manager
    try:
        # Configurar rutas para modelos
        models_dir = Path(config.MODELS_DIR)
        model_path = str(models_dir / config.LLM_CONFIG["model_name"])
        
        # Verificar si existe el modelo
        if not os.path.exists(model_path):
            logger.warning(f"⚠️ Modelo no encontrado en {model_path}")
            logger.warning("⚠️ Usando configuración de prueba")
            # Usar configuración de prueba si no existe el modelo
            llm_manager = LLMManager()
        else:
            # Inicializar con el modelo configurado
            llm_manager = LLMManager(model_path=model_path)
        
        logger.info("✅ LLM Manager inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando LLM Manager: {e}")
        llm_manager = None
    
    # Inicializar Memory Manager
    try:
        memory_dir = models_dir / "memory"
        memory_dir.mkdir(exist_ok=True, parents=True)
        
        memory_manager = MemoryManager(
            memory_file=str(memory_dir / "conversation_history.json")
        )
        
        logger.info("✅ Memory Manager inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando Memory Manager: {e}")
        memory_manager = None
    
    # Inicializar Knowledge Base
    try:
        kb_dir = models_dir / "knowledge"
        kb_dir.mkdir(exist_ok=True, parents=True)
        
        knowledge_base = KnowledgeBase(
            embedding_model="all-MiniLM-L6-v2",
            index_path=str(kb_dir / "faiss_index.bin"),
            documents_path=str(kb_dir / "documents.json")
        )
        
        # Inicializar índice
        knowledge_base.initialize_index()
        
        logger.info("✅ Knowledge Base inicializada")
    except Exception as e:
        logger.error(f"❌ Error inicializando Knowledge Base: {e}")
        knowledge_base = None
    
    logger.info("🌟 API lista para recibir peticiones")

@app.get("/", response_model=Dict[str, str])
async def root():
    """
    Endpoint raíz para verificar que la API está funcionando
    """
    return {"message": "Leonel Responde API está funcionando"}

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Devuelve el estado actual del sistema
    """
    global start_time, llm_manager, memory_manager, knowledge_base
    
    # Verificar que los componentes están inicializados
    if not llm_manager:
        raise HTTPException(status_code=503, detail="LLM Manager no inicializado")
    
    # Preparar respuesta
    response = {
        "status": "online",
        "llm": llm_manager.get_status(),
        "uptime": time.time() - start_time
    }
    
    # Agregar información de memoria si está disponible
    if memory_manager:
        response["memory"] = memory_manager.get_status()
    
    # Agregar información de base de conocimiento si está disponible
    if knowledge_base:
        response["knowledge_base"] = knowledge_base.get_status()
    
    return response

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Procesa una consulta al LLM o ejecuta comandos de memoria
    """
    global llm_manager, memory_manager, knowledge_base
    
    # Verificar que los componentes necesarios están inicializados
    if not llm_manager:
        raise HTTPException(status_code=503, detail="LLM Manager no inicializado")
    
    start_process = time.time()
    context_used = False
    retrieved_context = ""
    
    try:
        # Verificar si es un comando de memoria
        query_text = request.query.strip()
        
        # Comando /memory_count
        if query_text.lower() == "/memory_count":
            if memory_manager:
                short_count = len(memory_manager.short_term_memory)
                long_count = len(memory_manager.long_term_memory)
                response_text = f"📊 Estado de la memoria:\n  📝 Corto plazo: {short_count} interacciones\n  🧠 Largo plazo: {long_count} memorias\n  🔄 Límite auto-transición: {memory_manager.auto_transition_threshold}"
            else:
                response_text = "⚠️ Memoria no disponible"
            
            return {
                "response": response_text,
                "processing_time": time.time() - start_process,
                "tokens_used": None,
                "context_used": False
            }
        
        # Comando /memory_short
        elif query_text.lower() == "/memory_short":
            if memory_manager:
                if memory_manager.short_term_memory:
                    response_text = f"📝 Memorias a corto plazo ({len(memory_manager.short_term_memory)} items):\n"
                    for i, interaction in enumerate(memory_manager.short_term_memory, 1):
                        user_msg = interaction['user_message'][:50] + ('...' if len(interaction['user_message']) > 50 else '')
                        assistant_msg = interaction['assistant_response'][:50] + ('...' if len(interaction['assistant_response']) > 50 else '')
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(interaction['timestamp']))
                        response_text += f"  {i}. Usuario: {user_msg}\n     Asistente: {assistant_msg}\n     Tiempo: {timestamp}\n\n"
                else:
                    response_text = "📝 No hay memorias a corto plazo"
            else:
                response_text = "⚠️ Memoria no disponible"
            
            return {
                "response": response_text,
                "processing_time": time.time() - start_process,
                "tokens_used": None,
                "context_used": False
            }
        
        # Comando /clear_short
        elif query_text.lower() == "/clear_short":
            if memory_manager:
                memory_manager.clear_short_term()
                response_text = "🧹 Memoria a corto plazo limpiada"
            else:
                response_text = "⚠️ Memoria no disponible"
            
            return {
                "response": response_text,
                "processing_time": time.time() - start_process,
                "tokens_used": None,
                "context_used": False
            }
        
        # Comando /memory_groups
        elif query_text.lower() == "/memory_groups":
            if memory_manager:
                groups = memory_manager.list_memory_groups()
                if groups:
                    response_text = "📁 Grupos de memoria disponibles:\n"
                    for group, count in groups.items():
                        response_text += f"  • {group}: {count} memorias\n"
                else:
                    response_text = "📁 No hay grupos de memoria disponibles"
            else:
                response_text = "⚠️ Memoria no disponible"
            
            return {
                "response": response_text,
                "processing_time": time.time() - start_process,
                "tokens_used": None,
                "context_used": False
            }
        
        # Comando /memory_transition
        elif query_text.lower().startswith("/memory_transition "):
            if memory_manager:
                # Parsear argumentos del comando
                parts = query_text[len("/memory_transition "):].strip().split(" ", 1)
                if len(parts) >= 1:
                    concept_name = parts[0]
                    description = parts[1] if len(parts) > 1 else ""
                    
                    success = memory_manager.transition_short_to_long_manual(concept_name, description)
                    if success:
                        response_text = f"🔄 Transición manual completada: memoria organizada en concepto '{concept_name}'"
                    else:
                        response_text = "⚠️ No hay memoria a corto plazo para transferir"
                else:
                    response_text = "⚠️ Uso: /memory_transition <nombre_concepto> [descripción]"
            else:
                response_text = "⚠️ Memoria no disponible"
            
            return {
                "response": response_text,
                "processing_time": time.time() - start_process,
                "tokens_used": None,
                "context_used": False
            }
        
        # Procesamiento normal de consultas
        # Obtener contexto de la base de conocimiento si se solicita
        if request.use_knowledge_base and knowledge_base and request.query.strip():
            kb_results = knowledge_base.query(request.query, top_k=2)
            if kb_results:
                retrieved_context = "\n\n".join([r["content"] for r in kb_results])
                logger.info(f"📚 Contexto recuperado de la base de conocimiento: {len(retrieved_context)} caracteres")
                context_used = True
        
        # Obtener memoria de conversación si se solicita
        conversation_context = ""
        if request.use_memory and memory_manager:
            # Obtener memoria a corto plazo
            recent_context = memory_manager.get_recent_context()
            
            # Obtener memoria a largo plazo relevante
            relevant_memories = memory_manager.get_relevant_memory_contents(request.query, max_items=2)
            
            # Combinar ambos tipos de memoria
            all_memory = []
            if relevant_memories:
                all_memory.extend([f"Memoria relevante: {mem}" for mem in relevant_memories])
            if recent_context:
                all_memory.extend([f"Conversación reciente: {ctx}" for ctx in recent_context])
            
            if all_memory:
                conversation_context = "\n\n".join(all_memory)
                logger.info(f"🧠 Contexto de memoria recuperado: {len(conversation_context)} caracteres (memoria relevante: {len(relevant_memories)}, conversación reciente: {len(recent_context)})")
        
        # Combinar contexto proporcionado, recuperado y de memoria
        combined_context = ""
        if retrieved_context:
            combined_context += retrieved_context + "\n\n"
        if conversation_context:
            combined_context += conversation_context + "\n\n"
            context_used = True
        if request.context:
            combined_context += request.context
            context_used = True
        
        # Procesar consulta con o sin contexto
        if combined_context:
            response_text = llm_manager.query_with_context(
                text=request.query,
                context_docs=combined_context
            )
        else:
            response_text = llm_manager.query(request.query)
        
        # Guardar interacción en memoria si está habilitada
        if request.use_memory and memory_manager:
            memory_manager.add_interaction(
                user_message=request.query,
                assistant_response=response_text
            )
        
        # Calcular tiempo de procesamiento
        processing_time = time.time() - start_process
        
        # Preparar respuesta
        return {
            "response": response_text,
            "processing_time": processing_time,
            "tokens_used": None,  # No disponible en esta versión
            "context_used": context_used
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando consulta: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")

@app.post("/clear-memory")
async def clear_memory():
    """
    Limpia la memoria de conversación
    """
    global memory_manager
    
    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory Manager no inicializado")
    
    try:
        memory_manager.clear_memory()
        return {"status": "success", "message": "Memoria limpiada correctamente"}
    except Exception as e:
        logger.error(f"❌ Error limpiando memoria: {e}")
        raise HTTPException(status_code=500, detail=f"Error limpiando memoria: {str(e)}")

@app.post("/add-document")
async def add_document(content: str = Body(...), title: str = Body(None)):
    """
    Agrega un documento a la base de conocimiento
    """
    global knowledge_base
    
    if not knowledge_base:
        raise HTTPException(status_code=503, detail="Knowledge Base no inicializada")
    
    try:
        metadata = {"title": title} if title else {}
        success = knowledge_base.add_document(content, metadata)
        
        if success:
            return {"status": "success", "message": "Documento agregado correctamente"}
        else:
            raise HTTPException(status_code=500, detail="Error agregando documento")
    except Exception as e:
        logger.error(f"❌ Error agregando documento: {e}")
        raise HTTPException(status_code=500, detail=f"Error agregando documento: {str(e)}")

# Función para iniciar el servidor
def start_api(host: str = "0.0.0.0", port: int = 8000):
    """
    Inicia el servidor API
    
    Args:
        host: Host para el servidor
        port: Puerto para el servidor
    """
    uvicorn.run("backend.api:app", host=host, port=port, reload=config.DEBUG_MODE)

# Punto de entrada para ejecución directa
if __name__ == "__main__":
    # Usar configuración del archivo config.py
    start_api(host=config.API_HOST, port=config.API_PORT)