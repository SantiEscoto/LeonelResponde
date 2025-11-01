# Standard library imports
from contextlib import contextmanager
from functools import lru_cache
import os
import sys
import threading
from typing import Any, Dict, List, Optional
import weakref

# Third-party imports
# llama_cpp import is deferred to ModelWrapper._load_model to avoid import-time errors during tests

# Local imports
from pathlib import Path
current_file = Path(__file__)
project_root = current_file.parent.parent.parent
sys.path.append(str(project_root))

# Define cache_result decorator if not available
def cache_result(ttl=1800, cache_key=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Importar unified config una sola vez
try:
    from src.backend.utils.unified_config import get_config
    from src.backend.utils.performance_cache import get_global_cache
    from src.backend.utils.performance_optimizer import get_performance_optimizer

    config = get_config()
except ImportError:
    config = None

try:
    from src.backend.utils.unified_logger import get_unified_logger
except ImportError:
    # Fallback si no se puede importar el logger
    import logging

    def get_unified_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)


try:
    from src.backend.utils.memory_limiter import get_memory_limiter
except ImportError:
    get_memory_limiter = None

try:
    from src.backend.llm.model_versioning import get_version_manager, ModelStatus
except ImportError:
    get_version_manager = None
    ModelStatus = None

try:
    from src.backend.utils.tracing import PerformanceTracer
except ImportError:
    # Fallback if tracing import fails
    class PerformanceTracer:
        def __init__(self, enabled=False):
            self.enabled = enabled

        def span(self, name, metadata=None):
            from contextlib import nullcontext

            return nullcontext()


# Error handling imports
try:
    from src.backend.utils.error_handler import (
        ErrorCategory,
        ErrorContext,
        ErrorSeverity,
        get_error_handler,
        resilient_operation,
    )
except ImportError:
    # Fallback implementations
    @contextmanager
    def resilient_operation(component, operation, **kwargs):
        yield

    class ErrorContext:
        def __init__(self, **kwargs):
            pass

    class ErrorSeverity:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    class ErrorCategory:
        SYSTEM = "system"
        NETWORK = "network"
        DATA = "data"
        USER = "user"

    def get_error_handler():
        return None


logger = get_unified_logger("LLM")

# Global model cache with weak references to avoid memory leaks
_model_cache = weakref.WeakValueDictionary()
_cache_lock = threading.Lock()


def get_cache_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas del cache de modelos

    Returns:
        Diccionario con estadísticas del cache
    """
    with _cache_lock:
        cache_size = len(_model_cache)
        loaded_models = sum(1 for wrapper in _model_cache.values() if wrapper.is_loaded())

        return {
            "total_cached_models": cache_size,
            "loaded_models": loaded_models,
            "unloaded_models": cache_size - loaded_models,
            "cache_keys": list(_model_cache.keys()),
        }


def clear_model_cache():
    """
    Limpia completamente el cache de modelos
    """
    with _cache_lock:
        # Descargar todos los modelos antes de limpiar
        for wrapper in _model_cache.values():
            if wrapper.is_loaded():
                wrapper.unload()

        _model_cache.clear()
        import gc

        gc.collect()
        logger.info("🧹 Cache de modelos limpiado completamente")


@lru_cache(maxsize=3)
def _get_model_config_hash(model_path: str, n_ctx: int, n_threads: int, n_gpu_layers: int) -> str:
    """
    Genera un hash único para la configuración del modelo

    Args:
        model_path: Ruta al modelo
        n_ctx: Tamaño del contexto
        n_threads: Número de threads
        n_gpu_layers: Capas GPU

    Returns:
        Hash de configuración
    """
    import hashlib

    config_str = f"{model_path}_{n_ctx}_{n_threads}_{n_gpu_layers}"
    return hashlib.md5(config_str.encode()).hexdigest()


class ModelWrapper:
    """
    Wrapper para el modelo Llama que permite lazy loading y caching
    """

    def __init__(self, model_path: str, **kwargs):
        self.model_path = model_path
        self.kwargs = kwargs
        self._model = None
        self._load_lock = threading.Lock()
        self.config_hash = _get_model_config_hash(
            model_path,
            kwargs.get("n_ctx", 2048),
            kwargs.get("n_threads", 4),
            kwargs.get("n_gpu_layers", 0),
        )

    @property
    def model(self):
        """Lazy loading del modelo"""
        if self._model is None:
            with self._load_lock:
                if self._model is None:  # Double-check locking
                    self._load_model()
        return self._model

    def _load_model(self):
        """Carga el modelo de forma lazy con optimizaciones para Mac"""
        try:
            logger.info(f"🔄 Cargando modelo lazy: {self.model_path}")

            # Aplicar optimizaciones de rendimiento
            try:
                optimizer = get_performance_optimizer()
                optimizer.apply_all_optimizations()
                logger.info("🚀 Optimizaciones de rendimiento aplicadas")
            except Exception as e:
                logger.warning(f"⚠️ No se pudieron aplicar optimizaciones: {e}")

            # Optimizaciones específicas para Mac con MPS
            import platform

            if platform.system() == "Darwin":  # macOS
                # Verificar si MPS está deshabilitado en la configuración
                try:
                    from src.backend.utils.unified_config import get_config
                    config = get_config()
                    if config.llm.disable_mps:
                        logger.info("🍎 MPS deshabilitado por configuración")
                        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
                    else:
                        # Habilitar MPS si está disponible
                        try:
                            import torch

                            if torch.backends.mps.is_available():
                                logger.info("🚀 MPS detectado - habilitando aceleración GPU en Mac")
                                # Configurar para usar MPS cuando sea posible
                                os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
                            else:
                                logger.info("🍎 MPS no disponible - usando CPU")
                        except ImportError:
                            logger.info("🍎 PyTorch no disponible - usando CPU")
                except ImportError:
                    # Fallback si no se puede importar la configuración
                    logger.info("🍎 Configuración no disponible - usando configuración por defecto")

                # Optimizar para Apple Silicon
                if "n_threads" not in self.kwargs:
                    # En Apple Silicon, usar menos threads puede ser más eficiente
                    self.kwargs["n_threads"] = min(8, os.cpu_count() or 4)
                    logger.info(
                        f"🍎 Apple Silicon detectado - usando {self.kwargs['n_threads']} threads"
                    )

            # Lazy import here to avoid import-time failures in environments without llama_cpp
            try:
                from llama_cpp import Llama  # type: ignore
            except Exception as import_err:
                logger.error(f"❌ No se pudo importar llama_cpp: {import_err}")
                raise ImportError(
                    "llama_cpp (llama-cpp-python) es requerido para cargar el modelo local. "
                    "Instálalo o omite pruebas que requieren el modelo."
                ) from import_err

            # Cargar modelo directamente (sin timeout complejo por ahora)
            logger.info("🔄 Iniciando carga del modelo...")
            try:
                self._model = Llama(model_path=self.model_path, **self.kwargs)
                logger.info("✅ Modelo cargado exitosamente (lazy)")
            except Exception as load_err:
                logger.error(f"❌ Error al cargar el modelo: {load_err}")
                raise
        except Exception as e:
            logger.error(f"❌ Error en lazy loading: {e}")
            raise

    def is_loaded(self) -> bool:
        """Verifica si el modelo está cargado"""
        return self._model is not None

    def unload(self):
        """Descarga el modelo de memoria"""
        if self._model:
            del self._model
            self._model = None
            # Forzar garbage collection y limpieza de memoria GPU
            import gc

            gc.collect()

            # Limpiar cache de GPU si está disponible
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except ImportError:
                pass  # torch no disponible

            logger.info("🗑️ Modelo descargado (lazy)")

    def __getattr__(self, name):
        """Proxy para métodos del modelo"""
        return getattr(self.model, name)


class LLMManager:
    """
    Gestor de modelo LLM local usando llama-cpp-python
    Optimizado para modelos GGUF cuantizados
    """

    def __init__(self, model_path: str, preload_model: bool = False):
        """
        Inicializa el gestor de modelo LLM

        Args:
            model_path: Ruta al archivo del modelo GGUF
            preload_model: Si True, carga el modelo inmediatamente durante la inicialización
        """
        self.model_path = model_path
        self.model: Optional[Llama] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.is_loaded = False

        # Initialize tracer
        try:
            trace_enabled = config.system.trace_enabled if config else False
            self.tracer = PerformanceTracer(enabled=trace_enabled)
        except (ImportError, AttributeError):
            self.tracer = PerformanceTracer(enabled=False)

        # Initialize error handler
        self.error_handler = get_error_handler()

        # Parámetros de generación por defecto
        self.params = {
            "max_tokens": 512,
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 40,
            "repeat_penalty": 1.15,
            "n_ctx": 3072,
        }

        logger.info(f"🧠 Inicializando LLMManager con modelo: {model_path}")

        # Inicializar model versioning
        self.version_manager = None
        self.current_version_id = None
        if get_version_manager:
            try:
                self.version_manager = get_version_manager()
                logger.info("📚 Model Version Manager integrado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar version manager: {e}")

        # Integrar con memory limiter si está disponible
        self._register_with_memory_limiter()

        # Cargar modelo inmediatamente si se solicita
        if preload_model:
            logger.info("🚀 Cargando modelo durante inicialización...")
            if self.load_model():
                logger.info("✅ Modelo precargado exitosamente")
            else:
                logger.warning("⚠️ No se pudo precargar el modelo, se cargará en la primera consulta")

    def load_model(self) -> bool:
        """Carga el modelo GGUF con lazy loading y caching optimizado"""
        try:
            # Verificar que el archivo existe
            if not os.path.exists(self.model_path):
                logger.error(f"❌ Modelo no encontrado en: {self.model_path}")
                return False

            # Valores por defecto para parámetros optimizados
            n_ctx = self.params.get("n_ctx", 2048)
            n_threads = os.cpu_count() or 4  # Use all available CPU cores
            n_gpu_layers = -1  # Use all GPU layers by default for better performance

            # Intentar importar configuración global de forma segura
            try:
                # Obtener parámetros optimizados de la configuración unificada
                if config and hasattr(config, "llm"):
                    n_ctx = config.llm.n_ctx or n_ctx
                    n_threads = config.llm.n_threads or n_threads
                    n_gpu_layers = (
                        config.llm.n_gpu_layers
                        if config.llm.n_gpu_layers is not None
                        else n_gpu_layers
                    )

                    # Actualizar parámetros locales con los de la configuración unificada
                    self.params["n_ctx"] = n_ctx
                    self.params["max_tokens"] = config.llm.max_tokens or self.params.get(
                        "max_tokens", 256
                    )
                    self.params["temperature"] = config.llm.temperature or self.params.get(
                        "temperature", 0.7
                    )
                    self.params["top_p"] = config.llm.top_p or self.params.get("top_p", 0.95)
                    self.params["top_k"] = config.llm.top_k or self.params.get("top_k", 40)
            except (ImportError, AttributeError) as e:
                logger.warning(f"No se pudo importar configuración unificada: {e}")
                logger.warning("Usando valores por defecto para parámetros del modelo")

            # Generar hash de configuración para cache
            config_hash = _get_model_config_hash(self.model_path, n_ctx, n_threads, n_gpu_layers)

            # Verificar cache global
            with _cache_lock:
                if config_hash in _model_cache:
                    logger.info(f"🎯 Modelo encontrado en cache: {config_hash[:8]}...")
                    self.model = _model_cache[config_hash]
                    self.is_loaded = True
                    return True

            logger.info(f"📥 Preparando modelo GGUF con lazy loading: {self.model_path}...")
            logger.info(
                f"⚙️ Parámetros: n_ctx={n_ctx}, n_threads={n_threads}, n_gpu_layers={n_gpu_layers}"
            )

            # Crear wrapper con lazy loading y optimizaciones
            model_wrapper = ModelWrapper(
                model_path=self.model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                verbose=False,  # Reducir logs para mejor rendimiento
                # Optimizaciones adicionales
                use_mmap=True,  # Usar memory mapping para modelos grandes
                use_mlock=True,  # Bloquear memoria para evitar swapping
                n_batch=512,  # Batch size optimizado
                rope_scaling_type=1,  # RoPE scaling para mejor rendimiento
                flash_attn=True,  # Usar Flash Attention si está disponible
            )

            # Guardar en cache global
            with _cache_lock:
                _model_cache[config_hash] = model_wrapper

            self.model = model_wrapper
            self.is_loaded = True

            # Registrar modelo en version manager
            if self.version_manager:
                try:
                    # Configuración del modelo para registro
                    model_config = {
                        "n_ctx": n_ctx,
                        "n_threads": n_threads,
                        "n_gpu_layers": n_gpu_layers,
                        "model_file": os.path.basename(self.model_path)
                    }

                    # Registrar si no existe
                    active_version = self.version_manager.get_active_version()
                    if not active_version or active_version.model_path != self.model_path:
                        version = self.version_manager.register_model(
                            model_path=self.model_path,
                            description=f"Auto-registered model: {os.path.basename(self.model_path)}",
                            config=model_config,
                            set_as_active=True
                        )
                        self.current_version_id = version.version_id
                        logger.info(f"📌 Modelo registrado como versión: {version.version_id}")
                    else:
                        self.current_version_id = active_version.version_id
                        logger.info(f"📌 Usando versión activa: {active_version.version_id}")

                except Exception as e:
                    logger.warning(f"⚠️ Error registrando versión del modelo: {e}")

            # Calentar el modelo con retry logic mejorado
            warmup_success = self._warmup_model_with_retry(max_retries=3, retry_delay=1.0)
            if not warmup_success:
                logger.warning("⚠️ Warmup falló después de reintentos, modelo puede tardar en primera query")

            logger.info("✅ Modelo configurado con lazy loading exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error configurando modelo GGUF: {e}")
            print(f"❌ Error detallado: {e}")
            return False

    def _warmup_model_with_retry(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> bool:
        """
        Calienta el modelo con retry logic para optimizar futuras respuestas

        Args:
            max_retries: Número máximo de reintentos
            retry_delay: Delay entre reintentos en segundos

        Returns:
            True si el warmup fue exitoso
        """
        import time

        warmup_prompt = "Hola"

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔥 Intento {attempt}/{max_retries}: Calentando modelo...")

                start_time = time.time()

                # Acceder al modelo real a través del wrapper
                if hasattr(self.model, 'model') and hasattr(self.model.model, 'create_completion'):
                    result = self.model.model.create_completion(
                        prompt=warmup_prompt,
                        max_tokens=5,
                        temperature=0.1,
                        echo=False
                    )

                    # Verificar que la respuesta es válida
                    if result and "choices" in result and len(result["choices"]) > 0:
                        elapsed = time.time() - start_time
                        logger.info(f"✅ Modelo calentado exitosamente en {elapsed:.2f}s")
                        return True
                    else:
                        logger.warning(f"⚠️ Intento {attempt}: Respuesta de warmup inválida")

                elif hasattr(self.model, 'is_loaded') and not self.model.is_loaded():
                    # El modelo está en lazy loading y aún no se ha cargado
                    logger.info(f"ℹ️ Modelo en lazy loading, se cargará en primera query real")
                    return True  # Consideramos esto como éxito

                else:
                    logger.warning(f"⚠️ Intento {attempt}: Modelo no tiene interfaz esperada")

            except Exception as e:
                logger.warning(f"⚠️ Intento {attempt}/{max_retries} de warmup falló: {e}")

                # Si no es el último intento, esperar antes de reintentar
                if attempt < max_retries:
                    logger.info(f"⏳ Esperando {retry_delay}s antes de reintentar...")
                    time.sleep(retry_delay)
                    # Incrementar delay exponencialmente
                    retry_delay *= 1.5

        logger.error(f"❌ Warmup falló después de {max_retries} intentos")
        return False

    @cache_result(ttl=1800, cache_key=lambda self, text, **kwargs: f"query:{hash(text + str(kwargs.get('context', '')))}")
    def query(
        self, text: str, context: List[str] = None, timeout: int = 30, stream: bool = False
    ) -> str:
        """
        Procesa una consulta y devuelve respuesta con límite de tiempo

        Args:
            text: Texto de la consulta del usuario
            context: Lista opcional de textos de contexto para RAG
            timeout: Tiempo máximo en segundos para generar respuesta (default: 30s)
            stream: Si True, retorna un generador para streaming

        Returns:
            Respuesta generada por el modelo o generador si stream=True
        """
        import time

        with resilient_operation("llm_manager", "query"):
            if not self.is_loaded:
                logger.warning("⚠️ Modelo no cargado, intentando cargar...")
                if not self.load_model():
                    if self.error_handler:
                        self.error_handler.handle_error(
                            Exception("Failed to load LLM model"),
                            ErrorContext(
                                component="llm_manager",
                                operation="query",
                                metadata={"model_path": self.model_path},
                            ),
                            severity=ErrorSeverity.HIGH,
                            category=ErrorCategory.SYSTEM,
                        )
                    return "Error: No pude cargar el modelo LLM"

        try:
            logger.info(f"🤔 Procesando consulta: {text[:50]}... (timeout: {timeout}s)")
            start_time = time.time()

            # Preparar prompt con formato para chat (optimizado para concisión)
            with self.tracer.span(
                "prompt_build", {"query_length": len(text), "has_context": bool(context)}
            ):
                # Detectar si es el primer turno y si el usuario saludó
                def _is_greeting(user_text: str) -> bool:
                    try:
                        import re as _re
                        t = (user_text or "").strip().lower()
                        if not t:
                            return False
                        patterns = [
                            r"\bhola\b",
                            r"\bbuen[oa]s?\s+d[ií]as\b",
                            r"\bbuen[oa]s?\s+tardes\b",
                            r"\bbuen[oa]s?\s+noches\b",
                            r"\bbuen\s+d[ií]a\b",
                            r"\bqué\s+tal\b",
                            r"\bque\s+tal\b",
                        ]
                        return any(_re.search(p, t, flags=_re.IGNORECASE) for p in patterns)
                    except Exception:
                        return False

                is_first_turn = len(self.conversation_history) == 0
                user_greeted = _is_greeting(text)
                system_prompt = """
Eres un asistente conversacional inteligente en español mexicano.

PERSONALIDAD CORE:
- Conversacional y natural, como un amigo conocedor
- Memoria excelente: recuerdas detalles y contexto de conversaciones previas
- Adaptable: ajustas tu estilo según las preferencias del usuario
- Directo pero amable: respondes sin rodeos innecesarios

REGLAS FUNDAMENTALES:
1. IDIOMA: Solo español mexicano, nunca inglés
2. MEMORIA ACTIVA: Usa el contexto previo para dar respuestas más relevantes y personalizadas
3. PRECISIÓN: Admite cuando no sabes algo; nunca inventes información
4. RESPUESTA DIRECTA: Contesta la pregunta específica sin divagar
5. COHERENCIA: Mantén consistencia lógica y evita contradicciones
6. VARIEDAD: Cambia tu forma de iniciar respuestas para sonar natural
7. IDENTIDAD: NO tienes un nombre específico, eres simplemente un asistente útil

PERSONALIZACIÓN INTELIGENTE:
- PERFIL DEL USUARIO: Si hay información del perfil disponible en el contexto, úsala para personalizar respuestas
- Adapta ejemplos y explicaciones según los intereses y preferencias del usuario
- Considera la edad, profesión, hobbies y gustos mencionados en el perfil
- Ajusta el nivel de detalle técnico según el background del usuario
- Usa referencias culturales o profesionales relevantes al perfil
- Recuerda y construye sobre información personal previa

OPTIMIZACIONES DE CONVERSACIÓN:
- Construye sobre información previa mencionada en el contexto
- Evita repetir frases como "siempre", "por supuesto", "claro que sí"
- Para preguntas directas: responde inmediatamente, no preguntes de vuelta
- Para tareas creativas: completa la solicitud totalmente
- Conecta respuestas actuales con temas previos cuando sea relevante
- Usa el contexto para personalizar ejemplos y explicaciones

MANEJO INTELIGENTE DE CONTEXTO:
- Si hay información previa relevante, refiérela naturalmente
- Construye sobre preferencias y gustos mencionados anteriormente
- Mantén coherencia con decisiones o opiniones expresadas antes
- Usa detalles del contexto para hacer respuestas más específicas y útiles
- Integra información del perfil del usuario de manera natural en las respuestas

GESTIÓN DE ERRORES:
- Entradas confusas: pide clarificación específica
- Información faltante: explica qué necesitas saber
- Errores lógicos: corrige educativamente
- Mantén el español incluso al manejar errores
"""

                # Incluir contexto si existe (optimizado para mejor integración con LangChain)
                if context and len(context) > 0:
                    # Gestión inteligente de contexto mejorada
                    max_context_len = 2400  # Aumentado para aprovechar mejor el contexto de LangChain
                    context_text = "\n".join(context)
                    
                    # Truncado inteligente: mantener información más reciente y relevante
                    if len(context_text) > max_context_len:
                        # Dividir en líneas para truncado más inteligente
                        lines = context_text.split('\n')
                        truncated_lines = []
                        current_length = 0
                        
                        # Empezar desde el final (más reciente) y trabajar hacia atrás
                        for line in reversed(lines):
                            if current_length + len(line) + 1 <= max_context_len - 20:  # Reservar espacio para "..."
                                truncated_lines.insert(0, line)
                                current_length += len(line) + 1
                            else:
                                break
                        
                        if len(truncated_lines) < len(lines):
                            context_text = "[Contexto previo resumido]\n" + "\n".join(truncated_lines)
                        else:
                            context_text = "\n".join(truncated_lines)
                    
                    # Evitar saludos repetitivos si ya hay historial en la sesión
                    anti_greeting_rule = (
                        "\n- NO repitas saludos si la conversación ya está en curso; entra directo al punto."
                    )
                    
                    system_prompt += (
                        f"\n\nCONTEXTO DE CONVERSACIÓN PREVIA:\n{context_text}\n"
                        f"[Usa este contexto para dar respuestas más personalizadas y coherentes]{anti_greeting_rule}"
                    )

                # Crear prompt en formato chat para Llama, asegurando no exceder n_ctx
                # Reglas de saludo según primer turno
                if is_first_turn:
                    if user_greeted:
                        system_prompt += "\n- Si el usuario saluda, responde con un saludo breve y pasa al punto."
                    else:
                        system_prompt += "\n- En la PRIMERA respuesta de cada sesión: NO saludes, responde directo."
                prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{text} [/INST]"

                # Ajustar longitud del prompt para respetar n_ctx
                try:
                    ctx_limit = self.params.get("n_ctx", 1024)
                    # Reserva aproximada para la salida
                    max_tokens = min(self.params.get("max_tokens", 400), 512)
                    prompt_budget = max(256, ctx_limit - max_tokens - 32)
                    if len(prompt) > prompt_budget:
                        # recortar preservando inicio del system y el final de la instrucción
                        head = prompt[: int(prompt_budget * 0.6)]
                        tail = prompt[- int(prompt_budget * 0.4) :]
                        prompt = head + "\n...\n" + tail
                except Exception:
                    pass

            # Generar respuesta con o sin streaming
            if stream:
                return self._generate_streaming(prompt, timeout)
            else:
                # Generar respuesta directamente con el modelo (sin ThreadPoolExecutor)
                # Nota: Implementamos un timeout manual basado en tiempo transcurrido
                # Ajustar max_tokens dinámicamente según n_ctx y prompt
                ctx_limit = self.params.get("n_ctx", 1024)
                desired = self.params.get("max_tokens", 400)
                available = max(64, ctx_limit - len(prompt) - 32)
                max_tokens = max(64, min(desired, available, 512))

                with self.tracer.span(
                    "llm_generation", {"max_tokens": max_tokens, "prompt_length": len(prompt)}
                ):
                    # Configurar parámetros de generación optimizados para conversación natural
                    result = self.model.create_completion(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=self.params.get("temperature", 0.75),  # Ligeramente más creativo
                        top_p=self.params.get("top_p", 0.92),  # Más enfocado para coherencia
                        top_k=self.params.get("top_k", 35),  # Reducido para mejor calidad
                        repeat_penalty=self.params.get("repeat_penalty", 1.18),  # Aumentado para evitar repeticiones
                        frequency_penalty=0.1,  # Nuevo: reduce repetición de palabras frecuentes
                        presence_penalty=0.05,  # Nuevo: fomenta variedad en el vocabulario
                        stop=["</s>", "[INST]", "[/INST]", "\n\n👤", "Usuario:", "Tú:", "Human:", "Assistant:"],  # Mejorados stop tokens
                        echo=False,
                    )

                    # Extraer respuesta
                    raw_response = (
                        result["choices"][0]["text"].strip()
                        if result and "choices" in result and len(result["choices"]) > 0
                        else None
                    )

                    # Limpiar respuesta de posibles instrucciones del sistema filtradas
                    response = self._clean_response(raw_response) if raw_response else None

                    # Si ya hubo interacción previa, eliminar saludos iniciales repetitivos
                    try:
                        if response and len(self.conversation_history) > 0:
                            import re as _re
                            response = _re.sub(r"^(hola( [^,.!\n]*)?[!.,]?\s*)+", "", response, flags=_re.IGNORECASE)
                            response = response.lstrip()
                    except Exception:
                        pass

                    # En PRIMERA respuesta (sin historial):
                    # - Si el usuario NO saludó, quitar saludos automáticos
                    # - Si el usuario sí saludó, permitir un saludo breve
                    try:
                        if response and is_first_turn and not user_greeted:
                            import re as _re
                            response = _re.sub(r"^(hola( [^,.!\n]*)?[!.,]?\s*)+", "", response, flags=_re.IGNORECASE)
                            response = response.lstrip()
                    except Exception:
                        pass

                    # Sanitizar posibles tokens filtrados residuales
                    if response:
                        for tok in ("<SYS>", "</SYS>", "[INST]", "[/INST]", "<s>", "</s>"):
                            response = response.replace(tok, "").strip()

            # Si la respuesta está vacía, es None o muy corta, dar una por defecto
            if not response or len(response) < 5:
                response = "Entiendo tu mensaje. ¿Puedes darme más detalles?"

            # Verificar si se excedió el tiempo límite
            total_time = time.time() - start_time
            if total_time > timeout:
                logger.warning("⏱️ Tiempo de respuesta excedido: %.2fs > %ds", total_time, timeout)
                response += (
                    f"\n\n(Nota: Esta respuesta tomó {total_time:.2f}s, "
                    f"superando el límite recomendado de {timeout}s)"
                )

            # Actualizar historial siempre
            self.conversation_history.append({"role": "user", "content": text})
            self.conversation_history.append({"role": "assistant", "content": response})

            # Mantener historial limitado con gestión inteligente de memoria
            max_history_items = 8  # Reducido aún más para mejor rendimiento
            if len(self.conversation_history) > max_history_items:
                # Mantener los primeros 2 elementos (contexto inicial) y los últimos 6
                if len(self.conversation_history) > 2:
                    self.conversation_history = (
                        self.conversation_history[:2] + self.conversation_history[-(max_history_items-2):]
                    )
                else:
                    self.conversation_history = self.conversation_history[-max_history_items:]

            # Registrar tiempo total
            logger.info("💬 Respuesta generada en %.2fs: %s...", total_time, response[:50])

            # Actualizar métricas de versioning si está disponible
            if self.version_manager and self.current_version_id:
                try:
                    # Calcular tokens generados (aproximación)
                    tokens_generated = len(response.split())  # Aproximación simple

                    # Actualizar métricas
                    self.version_manager.update_metrics(
                        version_id=self.current_version_id,
                        latency_ms=total_time * 1000,
                        tokens_generated=tokens_generated,
                        success=True
                    )
                except Exception as e:
                    logger.debug(f"Error actualizando métricas de versión: {e}")

            return response

        except Exception as e:
            logger.error(f"❌ Error generando respuesta: {e}")

            # Actualizar métricas de error si está disponible
            if self.version_manager and self.current_version_id:
                try:
                    self.version_manager.update_metrics(
                        version_id=self.current_version_id,
                        latency_ms=0.0,
                        tokens_generated=0,
                        success=False
                    )
                except Exception:
                    pass

            return f"Lo siento, tuve un problema: {str(e)[:100]}"

    def _clean_response(self, response: str) -> str:
        """
        Limpia la respuesta del modelo eliminando posibles instrucciones del sistema
        que puedan haberse filtrado en la respuesta.

        Args:
            response: Respuesta cruda del modelo

        Returns:
            Respuesta limpia sin instrucciones del sistema
        """
        if not response:
            return response

        # Patrones a eliminar (instrucciones del sistema que se filtran)
        patterns_to_remove = [
            r"Eres Leonel.*?",
            r"Reglas ESTRICTAS:.*?",
            r"\d+\. IDIOMA:.*?",
            r"\d+\. BREVEDAD:.*?",
            r"\d+\. ESTILO:.*?",
            r"\d+\. FORMATO:.*?",
            r"Sé útil pero conciso.*?",
            r"No expliques lo que no te preguntan.*?",
            r"<<SYS>>.*?<</SYS>>",
            r"<</SYS>>",  # Limpiar token de cierre de sistema
            r"^<SYS>\s*",  # Limpiar <SYS> al inicio de respuesta
            r"\[INST\].*?\[/INST\]",
            r"<s>.*?</s>",
            r"^\s*<</SYS>>\s*",  # Limpiar <</SYS>> al inicio con espacios
        ]

        import re

        cleaned_response = response

        # Eliminar patrones de instrucciones del sistema
        for pattern in patterns_to_remove:
            cleaned_response = re.sub(
                pattern, "", cleaned_response, flags=re.DOTALL | re.IGNORECASE
            )

        # Limpiar espacios extra y saltos de línea
        cleaned_response = re.sub(r"\n\s*\n", "\n", cleaned_response)
        cleaned_response = cleaned_response.strip()

        # Si después de limpiar queda muy poco contenido, devolver la respuesta original
        if len(cleaned_response) < 10:
            return response

        return cleaned_response

    def _generate_streaming(self, prompt: str, timeout: int):
        """
        Genera respuesta con streaming

        Args:
            prompt: Prompt formateado para el modelo
            timeout: Tiempo máximo en segundos

        Yields:
            Tokens de respuesta uno por uno
        """
        import time

        try:
            start_time = time.time()
            max_tokens = min(self.params.get("max_tokens", 256), 256)

            with self.tracer.span(
                "llm_streaming", {"max_tokens": max_tokens, "prompt_length": len(prompt)}
            ):
                # Crear stream de tokens
                stream = self.model.create_completion(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=self.params.get("temperature", 0.7),
                    top_p=self.params.get("top_p", 0.95),
                    top_k=self.params.get("top_k", 40),
                    repeat_penalty=self.params.get("repeat_penalty", 1.1),
                    stop=["</s>", "[INST]", "[/INST]"],
                    echo=False,
                    stream=True,
                )

                full_response = ""
                first_token_time = None
                token_count = 0

                for chunk in stream:
                    # Verificar timeout
                    if time.time() - start_time > timeout:
                        logger.warning(f"⏱️ Streaming timeout después de {timeout}s")
                        yield "\n\n[Respuesta interrumpida por timeout]"
                        break

                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        token = chunk["choices"][0].get("text", "")
                        if token:
                            # Measure TTFT (Time To First Token)
                            if first_token_time is None:
                                first_token_time = time.time()
                                ttft = first_token_time - start_time
                                with self.tracer.span("ttft", {"time_seconds": ttft}):
                                    pass  # Just record the timing

                            token_count += 1
                            full_response += token
                            yield token

                # Measure TTLT (Time To Last Token)
                if token_count > 0:
                    ttlt = time.time() - start_time
                    tokens_per_second = token_count / ttlt if ttlt > 0 else 0
                    with self.tracer.span(
                        "ttlt",
                        {
                            "time_seconds": ttlt,
                            "token_count": token_count,
                            "tokens_per_second": tokens_per_second,
                        },
                    ):
                        pass  # Just record the timing

            # Actualizar historial al final del streaming
            if full_response.strip():
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append(
                    {"role": "assistant", "content": full_response.strip()}
                )

                # Mantener historial limitado
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]

                total_time = time.time() - start_time
                logger.info(f"🌊 Streaming completado en {total_time:.2f}s")

        except Exception as e:
            logger.error(f"❌ Error en streaming: {e}")
            yield f"Error en streaming: {str(e)[:100]}"

    def query_with_context(self, text: str, context_docs: str, timeout: int = 30) -> str:
        """Consulta con contexto para RAG (Retrieval Augmented Generation) con límite de tiempo

        Args:
            text: Texto de la consulta del usuario
            context_docs: Texto o lista de textos de contexto para RAG
            timeout: Tiempo máximo en segundos para generar respuesta

        Returns:
            Respuesta generada por el modelo con contexto
        """
        # Convertir a lista si es un string
        if isinstance(context_docs, str):
            context_docs = [context_docs]
        elif context_docs is None:
            context_docs = []

        # Verificar que timeout sea un número válido
        if not isinstance(timeout, int) or timeout <= 0:
            timeout = 30  # Valor por defecto

        return self.query(text, context=context_docs, timeout=timeout)

    def get_status(self) -> dict:
        """Devuelve el estado del modelo con información de optimización"""
        # Obtener timeout de configuración de forma segura
        timeout = 30  # Valor por defecto
        try:
            if config:
                timeout = config.llm.response_timeout or 30
        except AttributeError as e:
            logger.warning(f"No se pudo acceder a configuración: {e}")

        return {
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "conversation_length": len(self.conversation_history) // 2,  # Pares de mensajes
            "params": self.params,
            "timeout": timeout,
            "optimized": True,
            "max_tokens": self.params.get("max_tokens", 256),
            "context_size": self.params.get("n_ctx", 2048),
        }

    def clear_history(self):
        """Limpia el historial de conversación"""
        self.conversation_history.clear()
        logger.info("🧹 Historial de conversación limpiado")

    def _register_with_memory_limiter(self) -> None:
        """
        Registra el model manager con el memory limiter para gestión automática
        """
        if not get_memory_limiter:
            return

        try:
            limiter = get_memory_limiter()

            # Registrar cache del modelo
            limiter.register_cache(
                "llm_model",
                {
                    "size_func": self._get_model_memory_size,
                    "clear_func": self._unload_model,
                    "description": "LLM model cache",
                },
            )

            # Registrar cache del historial de conversación
            limiter.register_cache(
                "conversation_history",
                {
                    "size_func": self._get_history_size,
                    "clear_func": self.clear_history,
                    "description": "Conversation history cache",
                },
            )

            # Registrar callback de limpieza
            limiter.register_cleanup_callback("llm_manager", self._cleanup_callback)

            logger.info("🔗 LLMManager registrado con MemoryLimiter")

        except Exception as e:
            logger.warning(f"⚠️ No se pudo registrar con MemoryLimiter: {e}")

    def _get_model_memory_size(self) -> int:
        """
        Estima el tamaño de memoria del modelo cargado

        Returns:
            Tamaño estimado en bytes
        """
        if not self.is_loaded or not self.model:
            return 0

        try:
            # Verificar si el modelo wrapper está realmente cargado
            if hasattr(self.model, "is_loaded") and self.model.is_loaded():
                # Estimación basada en el tamaño del archivo del modelo
                file_size = os.path.getsize(self.model_path)
                # Los modelos GGUF suelen usar ~1.2x el tamaño del archivo en RAM
                return int(file_size * 1.2)
            else:
                # Si no está cargado, no usa memoria
                return 0
        except Exception:
            return 100 * 1024 * 1024  # 100MB como estimación por defecto

    def _get_history_size(self) -> int:
        """
        Calcula el tamaño del historial de conversación

        Returns:
            Tamaño en bytes
        """
        try:
            import sys

            return sys.getsizeof(self.conversation_history) + sum(
                sys.getsizeof(item) for item in self.conversation_history
            )
        except Exception:
            return len(self.conversation_history) * 512  # Estimación aproximada

    def _unload_model(self) -> None:
        """
        Descarga el modelo de memoria
        """
        if self.model:
            try:
                # Si es un ModelWrapper, usar su método unload
                if hasattr(self.model, "unload"):
                    self.model.unload()
                else:
                    del self.model
                self.model = None
                self.is_loaded = False

                # Forzar garbage collection y limpieza de memoria GPU
                import gc

                gc.collect()

                # Limpiar cache de GPU si está disponible
                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                        logger.info("🧹 Cache GPU limpiado")
                except ImportError:
                    pass  # torch no disponible

                logger.info("🗑️ Modelo descargado de memoria")
            except Exception as e:
                logger.error(f"❌ Error descargando modelo: {e}")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Obtiene información del cache y estado del modelo

        Returns:
            Información del cache y modelo actual
        """
        cache_stats = get_cache_stats()

        model_info = {
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "model_actually_loaded": False,
            "conversation_history_size": len(self.conversation_history),
            "memory_usage_mb": self._get_model_memory_size() / (1024 * 1024),
        }

        if self.model and hasattr(self.model, "is_loaded"):
            model_info["model_actually_loaded"] = self.model.is_loaded()

        return {"model_info": model_info, "global_cache": cache_stats}

    def force_lazy_load(self) -> bool:
        """
        Fuerza la carga lazy del modelo si no está cargado

        Returns:
            True si se cargó exitosamente
        """
        if self.model and hasattr(self.model, "model"):
            try:
                # Acceder a la propiedad model fuerza la carga lazy
                _ = self.model.model
                logger.info("🚀 Modelo cargado forzadamente (lazy)")
                return True
            except Exception as e:
                logger.error(f"❌ Error en carga forzada: {e}")
                return False
        return False

    def _cleanup_callback(self) -> None:
        """
        Callback de limpieza para el memory limiter
        """
        logger.info("🧹 Ejecutando limpieza de LLM Manager")

        # Limpiar historial si es muy largo
        if len(self.conversation_history) > 20:
            # Mantener solo las 10 conversaciones más recientes
            self.conversation_history = self.conversation_history[-10:]
            logger.info("🧹 Historial de conversación reducido a 10 entradas")

    def get_model_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del modelo y uso de memoria

        Returns:
            Diccionario con estadísticas
        """
        return {
            "model_loaded": self.is_loaded,
            "model_path": self.model_path,
            "conversation_history_count": len(self.conversation_history),
            "model_memory_size_bytes": self._get_model_memory_size(),
            "history_memory_size_bytes": self._get_history_size(),
            "parameters": self.params.copy(),
        }

    def unload(self) -> None:
        """Descarga el modelo y libera recursos asociados de forma segura."""
        self._unload_model()

    def get_version_info(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de la versión actual del modelo

        Returns:
            Diccionario con información de la versión o None
        """
        if not self.version_manager or not self.current_version_id:
            return None

        version = self.version_manager.get_version(self.current_version_id)
        if version:
            return version.to_dict()

        return None

    def list_model_versions(self) -> List[Dict[str, Any]]:
        """
        Lista todas las versiones de modelos disponibles

        Returns:
            Lista de diccionarios con información de versiones
        """
        if not self.version_manager:
            return []

        versions = self.version_manager.list_versions()
        return [v.to_dict() for v in versions]

    def compare_with_version(self, other_version_id: str) -> Optional[Dict[str, Any]]:
        """
        Compara la versión actual con otra versión

        Args:
            other_version_id: ID de la versión a comparar

        Returns:
            Diccionario con comparación o None
        """
        if not self.version_manager or not self.current_version_id:
            return None

        return self.version_manager.compare_versions(
            self.current_version_id,
            other_version_id
        )

    def get_versioning_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen del sistema de versioning

        Returns:
            Diccionario con resumen
        """
        if not self.version_manager:
            return {
                "enabled": False,
                "message": "Model versioning not available"
            }

        summary = self.version_manager.get_summary()
        summary["enabled"] = True
        summary["current_version"] = self.current_version_id

        return summary

    def __enter__(self) -> "LLMManager":
        """Permite usar el administrador como context manager."""
        return self

    def __exit__(self, exc_type, exc: Optional[BaseException], tb) -> None:
        """Al salir del contexto, liberar recursos del modelo."""
        try:
            self._unload_model()
        except Exception:
            # Mantener robustez en escenarios de apagado
            pass

    def __del__(self):
        """Intento best-effort de liberar el modelo al recolectarse el objeto."""
        try:
            # Evitar limpieza durante la finalización del intérprete o si nunca se cargó
            if getattr(sys, "is_finalizing", lambda: False)() or not getattr(self, "is_loaded", False):
                return
            self._unload_model()
        except Exception:
            # Evitar excepciones en el recolector
            pass


# Test de importación
if __name__ == "__main__":
    print("🧪 Testing LLMManager...")
    # Ruta de ejemplo para testing (usando configuración unificada)
    if config and hasattr(config, "paths"):
        test_model_path = str(config.paths.models_dir / "mistral-7b-instruct-v0.1.Q4_K_M.gguf")
    else:
        # Fallback para testing sin configuración
        test_model_path = "../models/mistral-7b-instruct-v0.1.Q4_K_M.gguf"
    llm = LLMManager(test_model_path)
    print(f"✅ LLMManager creado: {llm}")
    print(f"📊 Estado inicial: {llm.get_status()}")
