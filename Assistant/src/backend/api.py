# Standard library imports
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Third-party imports
from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# Import error handling system
try:
    from src.backend.utils.error_handler import (
        ErrorCategory,
        ErrorSeverity,
        get_error_handler,
        resilient_operation,
    )
except ImportError:
    from utils.error_handler import (
        ErrorCategory,
        ErrorSeverity,
        get_error_handler,
        resilient_operation,
    )

# Local imports
from pathlib import Path
current_file = Path(__file__)
project_root = current_file.parent.parent
sys.path.append(str(project_root))
try:
    from src.backend.llm.knowledge_base import KnowledgeBase
except Exception:
    KnowledgeBase = None
from src.backend.llm.model_manager import LLMManager
from src.backend.utils.unified_config import get_config
from src.backend.utils.unified_logger import get_unified_logger
from src.backend.utils.validators import (
    ValidationError,
    validate_query_input,
    validate_user_input,
)

try:
    from src.backend.utils.tracing import PerformanceTracer, span
except ImportError:
    # Fallback if tracing is not available
    class PerformanceTracer:
        def __init__(self, enabled: bool = False):
            self.enabled = enabled

        def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
            from contextlib import nullcontext

            return nullcontext()

    def span(name: str, attributes: Optional[Dict[str, Any]] = None):
        from contextlib import nullcontext

        return nullcontext()


# Setup structured logging
logger = get_unified_logger("API")

# Get unified configuration
config = get_config()

# Initialize performance tracer
tracer = PerformanceTracer(enabled=config.tracing.enabled)


# Modelos de datos para la API
class QueryRequest(BaseModel):
    query: str = Field(..., description="Texto de la consulta al LLM")
    context: Optional[str] = Field(None, description="Contexto adicional para la consulta")
    use_knowledge_base: bool = Field(False, description="Usar base de conocimiento para RAG")
    use_memory: bool = Field(True, description="Usar memoria de conversación")
    stream: bool = Field(False, description="Habilitar streaming de respuesta")


class QueryResponse(BaseModel):
    response: str = Field(..., description="Respuesta del LLM")
    processing_time: float = Field(..., description="Tiempo de procesamiento en segundos")
    tokens_used: Optional[int] = Field(None, description="Tokens utilizados en la consulta")
    context_used: Optional[bool] = Field(None, description="Si se utilizó contexto adicional")


class StatusResponse(BaseModel):
    status: str = Field(..., description="Estado del sistema")
    llm: Dict[str, Any] = Field(..., description="Información del modelo LLM")
    memory: Optional[Dict[str, Any]] = Field(None, description="Información de la memoria")
    knowledge_base: Optional[Dict[str, Any]] = Field(
        None, description="Información de la base de conocimiento"
    )
    uptime: float = Field(..., description="Tiempo de actividad en segundos")


# Crear aplicación FastAPI
app = FastAPI(
    title="Leonel Responde API",
    description="API REST para el asistente offline Leonel Responde",
    version="0.1.0",
)

# Configurar CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a orígenes específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware para timing de requests
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Middleware to measure request processing time."""
    start_time = time.perf_counter()

    # Extract request info for tracing
    method = request.method
    url_path = request.url.path
    client_ip = request.client.host if request.client else "unknown"

    # Create span for the entire request
    with tracer.span("request_total", {"method": method, "path": url_path, "client_ip": client_ip}):
        response = await call_next(request)

        # Calculate total time
        end_time = time.perf_counter()
        process_time = end_time - start_time

        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)

        # Record metrics if metrics collector is available
        if metrics_collector:
            metrics_collector.increment("api.requests_total")
            if response.status_code < 400:
                metrics_collector.increment("api.requests_success")
            else:
                metrics_collector.increment("api.requests_error")
            metrics_collector.record("api.latency_seconds", process_time)

        # Log request timing
        logger.info(
            f"Request processed: {method} {url_path}",
            extra={
                "method": method,
                "path": url_path,
                "client_ip": client_ip,
                "process_time_ms": process_time * 1000,
                "status_code": response.status_code,
            },
        )

        return response


# Middleware para rate limiting
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """Middleware para aplicar rate limiting a las peticiones."""
    if not rate_limiter:
        # Si no hay rate limiter, continuar sin restricciones
        return await call_next(request)

    # Obtener IP del cliente
    client_ip = request.client.host if request.client else "unknown"

    # Endpoints que no requieren rate limiting
    exempt_paths = {"/", "/health", "/metrics"}
    if request.url.path in exempt_paths:
        return await call_next(request)

    # Verificar rate limit
    allowed, reason, headers = rate_limiter.check_rate_limit(
        client_id=client_ip,
        endpoint=request.url.path
    )

    if not allowed:
        # Rate limit excedido
        logger.warning(
            f"🚫 Rate limit excedido - IP: {client_ip}, "
            f"Path: {request.url.path}, Reason: {reason}"
        )

        # Retornar error 429 Too Many Requests
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": reason,
                "retry_after": headers.get("Retry-After", "60")
            },
            headers=headers
        )

    # Request permitida, procesar normalmente
    response = await call_next(request)

    # Agregar headers de rate limiting a la respuesta
    for header_name, header_value in headers.items():
        response.headers[header_name] = header_value

    return response


# Variables globales
start_time = time.time()
llm_manager = None
memory_manager = None
knowledge_base = None
health_checker = None
metrics_collector = None
rate_limiter = None
auth_manager = None

# Thread pool para operaciones CPU-intensivas
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="api_worker")


# Async wrappers para operaciones síncronas
async def async_llm_query(query_text: str, context: str = None) -> str:
    """Wrapper asíncrono para consultas LLM"""
    loop = asyncio.get_event_loop()
    if context:
        # Usa el método especializado que convierte str->List[str]
        return await loop.run_in_executor(
            executor, llm_manager.query_with_context, query_text, context
        )
    else:
        return await loop.run_in_executor(executor, llm_manager.query, query_text)


async def async_knowledge_query(query_text: str, top_k: int = 2) -> List[Dict[str, Any]]:
    """Wrapper asíncrono para consultas a la base de conocimiento"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, knowledge_base.query, query_text, top_k)


async def async_memory_operations(operation: str, *args, **kwargs) -> Any:
    """Wrapper asíncrono para operaciones de memoria"""
    loop = asyncio.get_event_loop()

    def _memory_operation():
        if operation == "get_recent_context":
            return memory_manager.get_recent_context(*args, **kwargs)
        elif operation == "get_relevant_memory_contents":
            return memory_manager.get_relevant_memory_contents(*args, **kwargs)
        elif operation == "add_interaction":
            return memory_manager.add_interaction(*args, **kwargs)
        elif operation == "transition_short_to_long_manual":
            return memory_manager.transition_short_to_long_manual(*args, **kwargs)
        elif operation == "clear_memory":
            # Compatibilidad con MemoryService (usa reset)
            if hasattr(memory_manager, "clear_memory"):
                return memory_manager.clear_memory(*args, **kwargs)
            elif hasattr(memory_manager, "reset"):
                return memory_manager.reset(*args, **kwargs)
            else:
                raise AttributeError("Memory manager no soporta limpiar memoria")
        else:
            raise ValueError(f"Operación de memoria no soportada: {operation}")

    return await loop.run_in_executor(executor, _memory_operation)


async def async_knowledge_operations(operation: str, *args, **kwargs) -> Any:
    """Wrapper asíncrono para operaciones de base de conocimiento"""
    loop = asyncio.get_event_loop()

    def _knowledge_operation():
        if operation == "add_document":
            return knowledge_base.add_document(*args, **kwargs)
        else:
            raise ValueError(f"Operación de base de conocimiento no soportada: {operation}")

    return await loop.run_in_executor(executor, _knowledge_operation)


# Esquema de seguridad HTTP Bearer para JWT
security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Dependency para obtener el usuario actual desde el token JWT

    Args:
        credentials: Credenciales HTTP Bearer (token JWT)

    Returns:
        TokenPayload del usuario autenticado

    Raises:
        HTTPException: Si el token es inválido o no está presente
    """
    if not auth_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication system not available"
        )

    if not credentials or not credentials.scheme.lower() == "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")

    try:
        token = credentials.credentials
        user = auth_manager.verify_token(token)
        return user
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


async def require_permission(permission_name: str):
    """
    Dependency para verificar que el usuario actual tiene un permiso específico
    """
    user = await get_current_user()
    if not auth_manager.user_has_permission(user, permission_name):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@app.on_event("startup")
async def startup_event():
    """
    Inicializa los componentes del sistema al iniciar la API
    """
    global llm_manager, memory_manager, knowledge_base, health_checker, metrics_collector, rate_limiter, auth_manager

    logger.info("🚀 Iniciando API de Leonel Responde...")

    # Inicializar LLM Manager
    try:
        # Configurar rutas para modelos
        models_dir = Path(config.paths.models_dir)
        model_path = str(models_dir / config.llm.model_name)

        # Determinar si debemos precargar el modelo según configuración
        preload_flag = True
        try:
            preload_flag = bool(getattr(config.cache, "preload_models", True))
        except Exception:
            preload_flag = True
        # Permitir override por variable de entorno (DISABLE_LLM_PRELOAD=1/true/yes)
        env_preload_override = os.environ.get("DISABLE_LLM_PRELOAD")
        if env_preload_override is not None:
            if str(env_preload_override).lower() in {"1", "true", "yes"}:
                preload_flag = False

        # Verificar existencia del modelo y política de precarga
        model_exists = os.path.exists(model_path)
        if not model_exists or not preload_flag:
            if not model_exists:
                logger.warning(f"⚠️ Modelo no encontrado en {model_path}")
                logger.warning("⚠️ Usando configuración de prueba")
            else:
                logger.info("⏳ Precarga de LLM deshabilitada por configuración")
            # Inicializar sin precargar para inicialización rápida
            llm_manager = LLMManager(model_path=model_path, preload_model=False)
        else:
            # Cargar el modelo inmediatamente durante la inicialización para mejor UX
            logger.info("🚀 Precargando modelo LLM para mejorar tiempo de respuesta...")
            llm_manager = LLMManager(model_path=model_path, preload_model=True)

        logger.info("✅ LLM Manager inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando LLM Manager: {e}")
        llm_manager = None

    # Inicializar Memory Service unificado (reemplaza ConsolidatedMemoryManager)
    try:
        from src.backend.memory.memory_service import MemoryService
        memory_dir = models_dir / "memory"
        memory_dir.mkdir(exist_ok=True, parents=True)

        # Instanciar con firma actual (session_id, base_dir, ...)
        memory_manager = MemoryService(session_id="default", base_dir=str(memory_dir))

        logger.info("✅ MemoryService inicializado")
    except Exception as e:
        logger.error(f"❌ Error inicializando MemoryService: {e}")
        memory_manager = None

    # Inicializar Knowledge Base (si el módulo está disponible)
    if KnowledgeBase is None:
        logger.warning("⚠️ Knowledge Base no disponible; saltando inicialización (faiss/numpy ausente)")
        knowledge_base = None
    else:
        try:
            kb_dir = models_dir / "knowledge"
            kb_dir.mkdir(exist_ok=True, parents=True)

            knowledge_base = KnowledgeBase(
                embedding_model="all-MiniLM-L6-v2",
                index_path=str(kb_dir / "faiss_index.bin"),
                documents_path=str(kb_dir / "documents.json"),
            )

            # Inicializar índice
            knowledge_base.initialize_index()

            logger.info("✅ Knowledge Base inicializada")
        except Exception as e:
            logger.error(f"❌ Error inicializando Knowledge Base: {e}")
            knowledge_base = None

    # Inicializar Health Checker
    try:
        from src.backend.utils.health_checker import get_health_checker

        # Configurar umbrales de alerta
        alert_thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time": 5.0
        }

        health_checker = get_health_checker(alert_thresholds=alert_thresholds)

        # Ejecutar health check inicial
        components = {
            'llm_manager': llm_manager,
            'memory_manager': memory_manager,
            'knowledge_base': knowledge_base
        }
        initial_health = health_checker.check_system_health(components)
        logger.info(f"🏥 Health Checker inicializado - Estado: {initial_health.overall_status.value}")

    except Exception as e:
        logger.error(f"❌ Error inicializando Health Checker: {e}")

    # Inicializar Metrics Collector
    try:
        from src.backend.utils.metrics_collector import get_metrics_collector

        metrics_collector = get_metrics_collector(collection_interval=10.0)

        # Recolectar métricas del sistema al inicio
        metrics_collector.collect_system_metrics()

        # Registrar métricas de la API
        metrics_collector.increment("api.requests_total", 0)

        logger.info("📊 Metrics Collector inicializado")

    except Exception as e:
        logger.error(f"❌ Error inicializando Metrics Collector: {e}")
        metrics_collector = None

    # Inicializar Rate Limiter
    try:
        from src.backend.utils.rate_limiter import get_rate_limiter, RateLimitTier

        # Inicializar con tier FREE por defecto
        rate_limiter = get_rate_limiter(
            default_tier=RateLimitTier.FREE,
            enable_metrics=True
        )

        # Configurar IPs de desarrollo en whitelist si estamos en modo debug
        if config.system.debug_mode:
            rate_limiter.add_to_whitelist("127.0.0.1")
            rate_limiter.add_to_whitelist("localhost")
            logger.info("🔓 IPs de desarrollo agregadas a whitelist")

        logger.info("🚦 Rate Limiter inicializado")

    except Exception as e:
        logger.error(f"❌ Error inicializando Rate Limiter: {e}")
        rate_limiter = None

    # Inicializar JWT Auth Manager
    try:
        from src.backend.utils.jwt_auth import get_auth_manager

        # Inicializar con configuración
        auth_manager = get_auth_manager(
            secret_key=config.security.get("jwt_secret_key") if hasattr(config, 'security') else None,
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )

        logger.info("🔐 JWT Auth Manager inicializado")

    except Exception as e:
        logger.error(f"❌ Error inicializando JWT Auth Manager: {e}")
        auth_manager = None

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
        "uptime": time.time() - start_time,
    }

    # Agregar información de memoria si está disponible
    if memory_manager:
        if hasattr(memory_manager, "get_status"):
            response["memory"] = memory_manager.get_status()
        else:
            # Resumen mínimo para MemoryService
            try:
                recent = memory_manager.get_recent_context() or []
            except Exception:
                recent = []
            response["memory"] = {
                "type": "MemoryService",
                "recent_context_items": len(recent),
            }

    # Agregar información de base de conocimiento si está disponible
    if knowledge_base:
        response["knowledge_base"] = knowledge_base.get_status()

    return response


@app.get("/health")
async def get_health():
    """
    Endpoint de health check avanzado

    Retorna el estado de salud completo del sistema incluyendo:
    - Estado general del sistema
    - Estado de cada componente (LLM, memoria, base de conocimiento)
    - Recursos del sistema (CPU, memoria, disco)
    - Errores y advertencias
    - Historial de health checks
    - Métricas de disponibilidad
    """
    global health_checker, llm_manager, memory_manager, knowledge_base

    if not health_checker:
        # Si no hay health checker, devolver estado básico
        return {
            "overall_status": "unknown",
            "message": "Health checker not initialized",
            "timestamp": time.time(),
            "components": {
                "llm": "unknown" if not llm_manager else "online",
                "memory": "unknown" if not memory_manager else "online",
                "knowledge_base": "unknown" if not knowledge_base else "online"
            }
        }

    try:
        # Ejecutar health check
        components = {
            'llm_manager': llm_manager,
            'memory_manager': memory_manager,
            'knowledge_base': knowledge_base
        }

        health_status = health_checker.check_system_health(components)

        # Agregar métricas adicionales
        health_dict = health_status.to_dict()
        health_dict["uptime"] = health_checker.get_uptime()
        health_dict["availability"] = health_checker.get_availability_metrics()
        health_dict["history"] = health_checker.get_health_history(limit=5)

        return health_dict

    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@app.get("/metrics")
async def get_metrics(
    format: str = "prometheus",
    category: Optional[str] = None,
    window: Optional[int] = None,
    include_points: bool = False
):
    """
    Endpoint de métricas del sistema

    Retorna métricas completas del sistema con soporte para múltiples formatos.

    Args:
        format: Formato de salida ("json" o "prometheus")
        category: Filtrar por categoría (system, llm, api, memory, knowledge_base, custom)
        window: Ventana temporal en segundos para estadísticas (None = todas)
        include_points: Si incluir puntos históricos (solo JSON)

    Returns:
        Métricas del sistema en el formato especificado
    """
    global metrics_collector

    if not metrics_collector:
        return {
            "error": "Metrics collector not initialized",
            "timestamp": time.time(),
            "metrics": {}
        }

    try:
        # Recolectar métricas actuales del sistema
        metrics_collector.collect_system_metrics()

        # Filtrar por categoría si se especifica
        from src.backend.utils.metrics_collector import MetricCategory

        category_filter = None
        if category:
            try:
                category_filter = MetricCategory(category.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}. Valid categories: system, llm, api, memory, knowledge_base, custom"
                )

        # Formato Prometheus
        if format.lower() == "prometheus":
            prometheus_output = metrics_collector.export_prometheus()
            # Content-Type requerido por Prometheus: text/plain; version=0.0.4; charset=utf-8
            return PlainTextResponse(
                content=prometheus_output,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )

        # Formato JSON (default)
        elif format.lower() == "json":
            if window:
                # Resumen estadístico con ventana temporal
                stats_summary = metrics_collector.get_stats_summary(window_seconds=float(window))

                # Filtrar por categoría si se especifica
                if category_filter:
                    filtered_categories = {
                        category_filter.value: stats_summary["categories"].get(category_filter.value, {})
                    }
                    stats_summary["categories"] = filtered_categories

                return stats_summary
            else:
                # Exportación JSON completa
                json_export = metrics_collector.export_json(include_points=include_points)

                # Filtrar por categoría si se especifica
                if category_filter:
                    filtered_metrics = {
                        name: metric
                        for name, metric in json_export["metrics"].items()
                        if metrics_collector.get_metric(name).category == category_filter
                    }
                    json_export["metrics"] = filtered_metrics

                return json_export

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {format}. Valid formats: json, prometheus"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo métricas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Metrics retrieval failed: {str(e)}"
        )


async def stream_query(request: QueryRequest, http_request: Request):
    """
    Procesa una consulta con streaming de respuesta con manejo robusto de errores
    """
    global llm_manager, memory_manager, knowledge_base

    client_ip = http_request.client.host if http_request.client else "unknown"
    error_handler = get_error_handler()
    start_process = time.time()

    # Verificar que los componentes necesarios están inicializados
    if not llm_manager:
        raise HTTPException(status_code=503, detail="LLM Manager no inicializado")

    try:
        with resilient_operation(
            "api",
            "stream_query",
            request_id=http_request.headers.get("X-Request-ID"),
        ) as _ctx:
            # Validar entrada
            validated_query = validate_query_input(request.query)

            # Preparar contexto
            retrieved_context = ""
            conversation_context = ""
            context_used = False

            # Obtener contexto de la base de conocimiento si se solicita
            if request.use_knowledge_base and knowledge_base:
                with resilient_operation("knowledge_base", "query") as kb_ctx:
                    try:
                        kb_results = await async_knowledge_query(validated_query, top_k=2)
                        if kb_results:
                            retrieved_context = "\n\n".join([r["content"] for r in kb_results])
                            context_used = True
                    except Exception as e:
                        handled_error = error_handler.handle_error(
                            e, kb_ctx, ErrorSeverity.MEDIUM, ErrorCategory.SYSTEM
                        )
                        logger.warning(f"Knowledge base query failed: {handled_error.message}")

            # Obtener memoria de conversación si se solicita
            if request.use_memory and memory_manager:
                with resilient_operation("memory_manager", "get_context") as mem_ctx:
                    try:
                        # Obtener memoria a corto plazo
                        recent_context = await async_memory_operations("get_recent_context")

                        # Obtener memoria a largo plazo relevante (si existe el método)
                        relevant_memories = []
                        try:
                            relevant_memories = await async_memory_operations(
                                "get_relevant_memory_contents", validated_query, max_items=2
                            )
                        except Exception:
                            relevant_memories = []

                        # Combinar ambos tipos de memoria
                        all_memory = []
                        if relevant_memories:
                            all_memory.extend(
                                [f"Memoria relevante: {mem}" for mem in relevant_memories]
                            )
                        if recent_context:
                            all_memory.extend(
                                [f"Conversación reciente: {ctx}" for ctx in recent_context]
                            )

                        if all_memory:
                            conversation_context = "\n\n".join(all_memory)
                            logger.info(
                                "🧠 Contexto de memoria recuperado: "
                                f"{len(conversation_context)} caracteres "
                                f"(memoria relevante: {len(relevant_memories)}, "
                                f"conversación reciente: {len(recent_context)})"
                            )
                    except Exception as e:
                        handled_error = error_handler.handle_error(
                            e, mem_ctx, ErrorSeverity.MEDIUM, ErrorCategory.MEMORY
                        )
                        logger.warning(f"Memory context retrieval failed: {handled_error.message}")

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

            # Generar respuesta usando el LLM
            with span(
                "api_llm_generation",
                {
                    "query_length": len(validated_query),
                    "context_length": len(combined_context),
                    "has_context": bool(combined_context),
                },
            ):
                with logger.operation("llm_generation", context_length=len(combined_context)):
                    if combined_context:
                        response_text = await async_llm_query(validated_query, combined_context)
                    else:
                        response_text = await async_llm_query(validated_query)

            # Agregar interacción a la memoria si está habilitada
            if request.use_memory and memory_manager:
                with span(
                    "api_memory_storage",
                    {"query_length": len(validated_query), "response_length": len(response_text)},
                ):
                    with logger.operation("memory_storage"):
                        await async_memory_operations(
                            "add_interaction",
                            user_message=validated_query,
                            assistant_response=response_text,
                        )

            # Calcular tiempo de procesamiento
            processing_time = time.time() - start_process

            logger.info(
                "Query processed successfully",
                response_length=len(response_text),
                context_used=context_used,
            )

            # Preparar respuesta
            return {
                "response": response_text,
                "processing_time": processing_time,
                "tokens_used": None,  # No disponible en esta versión
                "context_used": context_used,
            }
    except Exception as e:
        logger.error(
            f"❌ Error procesando consulta: {e}",
            error_type="processing",
            client_ip=client_ip,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")


@app.post("/auth/register")
async def register(
    username: str = Body(...),
    password: str = Body(...),
    role: str = Body("user")
):
    """
    Registra un nuevo usuario

    Args:
        username: Nombre de usuario
        password: Contraseña
        role: Rol del usuario (user, premium) - solo admin puede crear admin

    Returns:
        Información del usuario creado
    """
    global auth_manager

    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not available"
        )

    try:
        from src.backend.utils.jwt_auth import UserRole

        # Validar rol
        try:
            user_role = UserRole(role.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role: {role}. Valid roles: user, premium"
            )

        # Solo permitir crear usuarios normales (no admin) por este endpoint
        if user_role in [UserRole.ADMIN, UserRole.SYSTEM]:
            raise HTTPException(
                status_code=403,
                detail="Cannot create admin or system users through this endpoint"
            )

        # Crear usuario
        user = auth_manager.create_user(
            username=username,
            password=password,
            role=user_role
        )

        return {
            "status": "success",
            "message": "User registered successfully",
            "user": user.to_dict()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error registrando usuario: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/auth/login")
async def login(
    username: str = Body(...),
    password: str = Body(...)
):
    """
    Autentica un usuario y devuelve tokens JWT

    Args:
        username: Nombre de usuario
        password: Contraseña

    Returns:
        Access token y refresh token
    """
    global auth_manager

    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not available"
        )

    # Autenticar usuario
    user = auth_manager.authenticate(username, password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Crear tokens
    access_token = auth_manager.create_access_token(user)
    refresh_token = auth_manager.create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60,
        "user": user.to_dict()
    }


@app.post("/auth/refresh")
async def refresh_token(
    refresh_token: str = Body(...)
):
    """
    Renueva tokens usando un refresh token

    Args:
        refresh_token: Refresh token válido

    Returns:
        Nuevos access token y refresh token
    """
    global auth_manager

    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not available"
        )

    # Renovar tokens
    result = auth_manager.refresh_access_token(refresh_token)
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    new_access_token, new_refresh_token = result

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60
    }


@app.post("/auth/logout")
async def logout(current_user = Depends(get_current_user)):
    """
    Cierra sesión revocando el token actual

    Args:
        current_user: Usuario autenticado (obtenido del token)

    Returns:
        Confirmación de logout
    """
    global auth_manager

    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not available"
        )

    # Revocar token
    auth_manager.revoke_token(current_user.jti)

    return {
        "status": "success",
        "message": "Logged out successfully"
    }


@app.get("/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Obtiene información del usuario autenticado

    Args:
        current_user: Usuario autenticado (obtenido del token)

    Returns:
        Información del usuario
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role.value,
        "permissions": [p.value for p in current_user.permissions],
        "token_type": current_user.token_type,
        "expires_at": current_user.expires_at
    }


@app.get("/rate-limit/status")
async def get_rate_limit_status(client_id: Optional[str] = None):
    """
    Endpoint para obtener el estado del rate limiting

    Args:
        client_id: ID del cliente específico (opcional)
                  Si no se proporciona, devuelve estadísticas globales

    Returns:
        Estado del rate limiting (global o por cliente)
    """
    global rate_limiter

    if not rate_limiter:
        return {
            "error": "Rate limiter not initialized",
            "timestamp": time.time()
        }

    try:
        if client_id:
            # Estadísticas de un cliente específico
            client_status = rate_limiter.get_client_status(client_id)
            if client_status:
                return client_status
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Client '{client_id}' not found"
                )
        else:
            # Estadísticas globales
            return rate_limiter.get_global_stats()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado de rate limiting: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Rate limit status retrieval failed: {str(e)}"
        )


@app.post("/rate-limit/set-tier")
async def set_rate_limit_tier(
    client_id: str = Body(...),
    tier: str = Body(...)
):
    """
    Configura el tier de rate limiting para un cliente

    **Nota:** En producción, este endpoint debería requerir autenticación de admin.
    Por ahora está abierto para facilitar el desarrollo.

    Args:
        client_id: ID del cliente
        tier: Tier a asignar (free, premium, admin, unlimited)

    Returns:
        Confirmación de la operación
    """
    global rate_limiter

    if not rate_limiter:
        raise HTTPException(
            status_code=503,
            detail="Rate limiter not initialized"
        )

    try:
        from src.backend.utils.rate_limiter import RateLimitTier

        # Validar tier
        try:
            tier_enum = RateLimitTier(tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tier: {tier}. Valid tiers: free, premium, admin, unlimited"
            )

        # Configurar tier
        rate_limiter.set_client_tier(client_id, tier_enum)

        return {
            "status": "success",
            "message": f"Tier '{tier}' assigned to client '{client_id}'",
            "client_id": client_id,
            "tier": tier
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error configurando tier de rate limiting: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Tier configuration failed: {str(e)}"
        )


@app.post("/clear-memory")
async def clear_memory():
    """
    Limpia la memoria de conversación
    """
    global memory_manager

    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory Manager no inicializado")

    try:
        await async_memory_operations("clear_memory")
        return {"status": "success", "message": "Memoria limpiada correctamente"}
    except Exception as e:
        logger.error(f"❌ Error limpiando memoria: {e}")
        raise HTTPException(status_code=500, detail=f"Error limpiando memoria: {str(e)}")


@app.post("/add-document")
async def add_document(http_request: Request, content: str = Body(...), title: str = Body(None)):
    """
    Agrega un documento a la base de conocimiento
    """
    global knowledge_base

    if not knowledge_base:
        raise HTTPException(status_code=503, detail="Knowledge Base no inicializada")

    client_ip = http_request.client.host if http_request.client else "unknown"

    # Log incoming request
    logger.log_request(
        "POST",
        "/add-document",
        client_ip=client_ip,
        content_length=len(content),
        has_title=bool(title),
    )

    with logger.operation("document_addition", client_ip=client_ip, content_length=len(content)):
        # Validar contenido del documento
        try:
            with logger.operation("content_validation"):
                from src.backend.utils.validators import validate_document_content

                validated_content = validate_document_content(content)
                logger.info(f"✅ Documento validado: {len(validated_content)} caracteres")

                # Validar título si se proporciona
                validated_title = None
                if title:
                    validated_title = validate_user_input(title)
                    logger.info(f"✅ Título validado: {validated_title}")

        except ValidationError as e:
            logger.error(
                f"Documento rechazado en API: {e}", error_type="validation", client_ip=client_ip
            )
            raise HTTPException(status_code=400, detail=f"Error de validación: {str(e)}")

        try:
            with logger.operation("knowledge_base_addition"):
                metadata = {"title": validated_title} if validated_title else {}
                success = await async_knowledge_operations(
                    "add_document",
                    validated_content,
                    metadata,
                )

            if success:
                logger.info(
                    "Documento agregado correctamente",
                    document_title=validated_title,
                    content_length=len(validated_content),
                )
                return {"status": "success", "message": "Documento agregado correctamente"}
            else:
                logger.error(
                    "Error agregando documento",
                    error_type="knowledge_base_error",
                    client_ip=client_ip,
                )
                raise HTTPException(status_code=500, detail="Error agregando documento")
        except Exception as e:
            logger.error(
                f"❌ Error agregando documento: {e}",
                error_type="processing",
                client_ip=client_ip,
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail=f"Error agregando documento: {str(e)}")


# Función para iniciar el servidor
def start_api(host: str = "0.0.0.0", port: int = 8000):
    """
    Inicia el servidor API

    Args:
        host: Host para el servidor
        port: Puerto para el servidor
    """
    uvicorn.run("backend.api:app", host=host, port=port, reload=config.system.debug_mode)


# Punto de entrada para ejecución directa
if __name__ == "__main__":
    # Usar configuración del archivo backend/utils/unified_config.py
    start_api(host=config.system.api_host, port=config.system.api_port)

# Endpoint no-streaming para desbloquear flujo
@app.post("/query", response_model=QueryResponse)
async def query_llm(request: QueryRequest, http_request: Request):
    # Si se solicita streaming, delegar al manejador de streaming existente
    if request.stream:
        return await stream_query(request, http_request)

    # Modo no-streaming: construir contexto, consultar LLM y devolver JSON
    start_process = time.time()

    # Validar entrada
    validated_query = validate_query_input(request.query)

    # Preparar contexto
    retrieved_context = ""
    conversation_context = ""
    context_used = False

    # Obtener contexto de la base de conocimiento si se solicita
    if request.use_knowledge_base and knowledge_base:
        try:
            kb_results = await async_knowledge_query(validated_query, top_k=2)
            if kb_results:
                retrieved_context = "\n\n".join([r["content"] for r in kb_results])
                context_used = True
        except Exception:
            # Si falla RAG, continuar sin contexto
            pass

    # Obtener contexto de conversación si está habilitado
    if request.use_memory and memory_manager:
        try:
            if hasattr(memory_manager, "get_recent_context"):
                recent_context = await async_memory_operations("get_recent_context")
                if recent_context:
                    conversation_context = "\n\n".join(recent_context)
        except Exception:
            # Fallos de memoria no deben romper la respuesta
            pass

    final_context = None
    if retrieved_context or conversation_context:
        final_context = "\n\n".join(filter(None, [retrieved_context, conversation_context]))

    # Consultar el LLM de forma síncrona (no streaming)
    response_text = await async_llm_query(validated_query, final_context)
    processing_time = time.time() - start_process

    # Almacenar interacción en memoria si corresponde
    if request.use_memory and memory_manager:
        try:
            await async_memory_operations("store_interaction", validated_query, response_text)
        except Exception:
            pass

    return QueryResponse(
        response=response_text,
        processing_time=processing_time,
        tokens_used=None,
        context_used=context_used,
    )

@app.post("/auth/register")
async def register(
    username: str = Body(...),
    password: str = Body(...),
    role: str = Body("user")
):
    """
    Registra un nuevo usuario

    Args:
        username: Nombre de usuario
        password: Contraseña
        role: Rol del usuario (user, premium) - solo admin puede crear admin

    Returns:
        Información del usuario creado
    """
    global auth_manager

    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not available"
        )

    try:
        from src.backend.utils.jwt_auth import UserRole

        # Validar rol
        try:
            user_role = UserRole(role.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role: {role}. Valid roles: user, premium"
            )

        # Solo permitir crear usuarios normales (no admin) por este endpoint
        if user_role in [UserRole.ADMIN, UserRole.SYSTEM]:
            raise HTTPException(
                status_code=403,
                detail="Cannot create admin or system users through this endpoint"
            )

        # Crear usuario
        user = auth_manager.create_user(
            username=username,
            password=password,
            role=user_role
        )

        return {
            "status": "success",
            "message": "User registered successfully",
            "user": user.to_dict()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error registrando usuario: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/auth/login")
async def login(
    username: str = Body(...),
    password: str = Body(...)
):
    """
    Autentica un usuario y devuelve tokens JWT

    Args:
        username: Nombre de usuario
        password: Contraseña

    Returns:
        Access token y refresh token
    """
    global auth_manager

    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not available"
        )

    # Autenticar usuario
    user = auth_manager.authenticate(username, password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Crear tokens
    access_token = auth_manager.create_access_token(user)
    refresh_token = auth_manager.create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60,
        "user": user.to_dict()
    }


@app.post("/auth/refresh")
async def refresh_token(
    refresh_token: str = Body(...)
):
    """
    Renueva tokens usando un refresh token

    Args:
        refresh_token: Refresh token válido

    Returns:
        Nuevos access token y refresh token
    """
    global auth_manager

    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not available"
        )

    # Renovar tokens
    result = auth_manager.refresh_access_token(refresh_token)
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token"
        )

    new_access_token, new_refresh_token = result

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": auth_manager.access_token_expire_minutes * 60
    }


@app.post("/auth/logout")
async def logout(current_user = Depends(get_current_user)):
    """
    Cierra sesión revocando el token actual

    Args:
        current_user: Usuario autenticado (obtenido del token)

    Returns:
        Confirmación de logout
    """
    global auth_manager

    if not auth_manager:
        raise HTTPException(
            status_code=503,
            detail="Authentication system not available"
        )

    # Revocar token
    auth_manager.revoke_token(current_user.jti)

    return {
        "status": "success",
        "message": "Logged out successfully"
    }


@app.get("/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Obtiene información del usuario autenticado

    Args:
        current_user: Usuario autenticado (obtenido del token)

    Returns:
        Información del usuario
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role.value,
        "permissions": [p.value for p in current_user.permissions],
        "token_type": current_user.token_type,
        "expires_at": current_user.expires_at
    }


@app.get("/rate-limit/status")
async def get_rate_limit_status(client_id: Optional[str] = None):
    """
    Endpoint para obtener el estado del rate limiting

    Args:
        client_id: ID del cliente específico (opcional)
                  Si no se proporciona, devuelve estadísticas globales

    Returns:
        Estado del rate limiting (global o por cliente)
    """
    global rate_limiter

    if not rate_limiter:
        return {
            "error": "Rate limiter not initialized",
            "timestamp": time.time()
        }

    try:
        if client_id:
            # Estadísticas de un cliente específico
            client_status = rate_limiter.get_client_status(client_id)
            if client_status:
                return client_status
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Client '{client_id}' not found"
                )
        else:
            # Estadísticas globales
            return rate_limiter.get_global_stats()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado de rate limiting: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Rate limit status retrieval failed: {str(e)}"
        )


@app.post("/rate-limit/set-tier")
async def set_rate_limit_tier(
    client_id: str = Body(...),
    tier: str = Body(...)
):
    """
    Configura el tier de rate limiting para un cliente

    **Nota:** En producción, este endpoint debería requerir autenticación de admin.
    Por ahora está abierto para facilitar el desarrollo.

    Args:
        client_id: ID del cliente
        tier: Tier a asignar (free, premium, admin, unlimited)

    Returns:
        Confirmación de la operación
    """
    global rate_limiter

    if not rate_limiter:
        raise HTTPException(
            status_code=503,
            detail="Rate limiter not initialized"
        )

    try:
        from src.backend.utils.rate_limiter import RateLimitTier

        # Validar tier
        try:
            tier_enum = RateLimitTier(tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tier: {tier}. Valid tiers: free, premium, admin, unlimited"
            )

        # Configurar tier
        rate_limiter.set_client_tier(client_id, tier_enum)

        return {
            "status": "success",
            "message": f"Tier '{tier}' assigned to client '{client_id}'",
            "client_id": client_id,
            "tier": tier
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error configurando tier de rate limiting: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Tier configuration failed: {str(e)}"
        )


@app.post("/clear-memory")
async def clear_memory():
    """
    Limpia la memoria de conversación
    """
    global memory_manager

    if not memory_manager:
        raise HTTPException(status_code=503, detail="Memory Manager no inicializado")

    try:
        await async_memory_operations("clear_memory")
        return {"status": "success", "message": "Memoria limpiada correctamente"}
    except Exception as e:
        logger.error(f"❌ Error limpiando memoria: {e}")
        raise HTTPException(status_code=500, detail=f"Error limpiando memoria: {str(e)}")


@app.post("/add-document")
async def add_document(http_request: Request, content: str = Body(...), title: str = Body(None)):
    """
    Agrega un documento a la base de conocimiento
    """
    global knowledge_base

    if not knowledge_base:
        raise HTTPException(status_code=503, detail="Knowledge Base no inicializada")

    client_ip = http_request.client.host if http_request.client else "unknown"

    # Log incoming request
    logger.log_request(
        "POST",
        "/add-document",
        client_ip=client_ip,
        content_length=len(content),
        has_title=bool(title),
    )

    with logger.operation("document_addition", client_ip=client_ip, content_length=len(content)):
        # Validar contenido del documento
        try:
            with logger.operation("content_validation"):
                from src.backend.utils.validators import validate_document_content

                validated_content = validate_document_content(content)
                logger.info(f"✅ Documento validado: {len(validated_content)} caracteres")

                # Validar título si se proporciona
                validated_title = None
                if title:
                    validated_title = validate_user_input(title)
                    logger.info(f"✅ Título validado: {validated_title}")

        except ValidationError as e:
            logger.error(
                f"Documento rechazado en API: {e}", error_type="validation", client_ip=client_ip
            )
            raise HTTPException(status_code=400, detail=f"Error de validación: {str(e)}")

        try:
            with logger.operation("knowledge_base_addition"):
                metadata = {"title": validated_title} if validated_title else {}
                success = await async_knowledge_operations(
                    "add_document",
                    validated_content,
                    metadata,
                )

            if success:
                logger.info(
                    "Documento agregado correctamente",
                    document_title=validated_title,
                    content_length=len(validated_content),
                )
                return {"status": "success", "message": "Documento agregado correctamente"}
            else:
                logger.error(
                    "Error agregando documento",
                    error_type="knowledge_base_error",
                    client_ip=client_ip,
                )
                raise HTTPException(status_code=500, detail="Error agregando documento")
        except Exception as e:
            logger.error(
                f"❌ Error agregando documento: {e}",
                error_type="processing",
                client_ip=client_ip,
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail=f"Error agregando documento: {str(e)}")


# Función para iniciar el servidor
def start_api(host: str = "0.0.0.0", port: int = 8000):
    """
    Inicia el servidor API

    Args:
        host: Host para el servidor
        port: Puerto para el servidor
    """
    uvicorn.run("backend.api:app", host=host, port=port, reload=config.system.debug_mode)


# Punto de entrada para ejecución directa
if __name__ == "__main__":
    # Usar configuración del archivo backend/utils/unified_config.py
    start_api(host=config.system.api_host, port=config.system.api_port)

# Endpoint no-streaming para desbloquear flujo
@app.post("/query", response_model=QueryResponse)
async def query_llm(request: QueryRequest, http_request: Request):
    # Si se solicita streaming, delegar al manejador de streaming existente
    if request.stream:
        return await stream_query(request, http_request)

    # Modo no-streaming: construir contexto, consultar LLM y devolver JSON
    start_process = time.time()

    # Validar entrada
    validated_query = validate_query_input(request.query)

    # Preparar contexto
    retrieved_context = ""
    conversation_context = ""
    context_used = False

    # Obtener contexto de la base de conocimiento si se solicita
    if request.use_knowledge_base and knowledge_base:
        try:
            kb_results = await async_knowledge_query(validated_query, top_k=2)
            if kb_results:
                retrieved_context = "\n\n".join([r["content"] for r in kb_results])
                context_used = True
        except Exception:
            # Si falla RAG, continuar sin contexto
            pass

    # Obtener contexto de conversación si está habilitado
    if request.use_memory and memory_manager:
        try:
            if hasattr(memory_manager, "get_recent_context"):
                recent_context = await async_memory_operations("get_recent_context")
                if recent_context:
                    conversation_context = "\n\n".join(recent_context)
        except Exception:
            # Fallos de memoria no deben romper la respuesta
            pass

    final_context = None
    if retrieved_context or conversation_context:
        final_context = "\n\n".join(filter(None, [retrieved_context, conversation_context]))

    # Consultar el LLM de forma síncrona (no streaming)
    response_text = await async_llm_query(validated_query, final_context)
    processing_time = time.time() - start_process

    # Almacenar interacción en memoria si corresponde
    if request.use_memory and memory_manager:
        try:
            await async_memory_operations("store_interaction", validated_query, response_text)
        except Exception:
            pass

    return QueryResponse(
        response=response_text,
        processing_time=processing_time,
        tokens_used=None,
        context_used=context_used,
    )
