"""
Component initialization and management for the assistant application.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

def _get_config():
    """Lazy import of config to avoid circular imports"""
    from src.backend.utils.unified_config import get_config
    return get_config()

def _get_logger():
    """Lazy import of logger to avoid circular imports"""
    from src.backend.utils.unified_logger import get_unified_logger
    logger = get_unified_logger("ComponentInitializer")
    # Reduce console noise during interactive sessions
    try:
        logger.set_console_level(logging.ERROR)
    except Exception:
        pass
    return logger

def _get_memory_service():
    """Lazy import of MemoryService to avoid circular imports"""
    try:
        from src.backend.memory.memory_service import MemoryService
        return MemoryService
    except Exception:
        return None


def initialize_component(
    component_name: str, operation_name: str, init_func, components: dict, component_key: str
):
    """Helper function to initialize components with resilient error handling"""
    from src.backend.utils.error_handler import (
        ErrorCategory,
        ErrorSeverity,
        get_error_handler,
        resilient_operation,
    )
    
    logger = _get_logger()
    
    with resilient_operation(component_key, operation_name):
        try:
            with logger.operation(operation_name):
                component = init_func()
                components[component_key] = component
                logger.info(f"✅ {component_name} inicializado", component=component_key)
                return component
        except Exception as e:
            error_handler = get_error_handler()
            from src.backend.utils.error_handler import ErrorContext

            # Determine error category based on component
            category_map = {
                "llm": ErrorCategory.MODEL,
                "memory": ErrorCategory.MEMORY,
                "knowledge_base": ErrorCategory.SYSTEM,
                "backup": ErrorCategory.SYSTEM,
            }
            category = category_map.get(component_key, ErrorCategory.SYSTEM)

            handled_error = error_handler.handle_error(
                e, ErrorContext(component_name, operation_name), ErrorSeverity.HIGH, category
            )

            logger.error(
                f"❌ Error inicializando {component_name}: {handled_error.message}",
                error_type="initialization",
                component=component_key,
                exc_info=True,
            )
            components[component_key] = None
            return None


def validate_configuration():
    """Valida la configuración del sistema al inicio para detectar problemas temprano"""
    config = _get_config()
    logger = _get_logger()
    
    validation_errors = []
    warnings = []

    # Validar configuración LLM
    if not config.llm.model_name:
        validation_errors.append("Nombre del modelo LLM no especificado")

    if config.llm.max_tokens <= 0:
        validation_errors.append("max_tokens debe ser mayor que 0")

    if not (0.0 <= config.llm.temperature <= 2.0):
        validation_errors.append("temperature debe estar entre 0.0 y 2.0")

    if config.llm.response_timeout < 5:
        warnings.append("response_timeout muy bajo (< 5s), puede causar timeouts frecuentes")

    # Validar rutas críticas
    models_dir = Path(config.paths.models_dir)
    if not models_dir.exists():
        validation_errors.append(f"Directorio de modelos no existe: {models_dir}")

    # Validar configuración de memoria
    memory_dir = Path(config.paths.memory_dir)
    if not memory_dir.exists():
        warnings.append(f"Directorio de memoria no existe: {memory_dir}")

    # Validar configuración de base de conocimiento
    kb_dir = Path(config.paths.knowledge_dir)
    if not kb_dir.exists():
        warnings.append(f"Directorio de base de conocimiento no existe: {kb_dir}")

    # Validar configuración del sistema
    if not (1024 <= config.system.api_port <= 65535):
        validation_errors.append("api_port debe estar entre 1024 y 65535")

    # Mostrar resultados
    if validation_errors:
        from src.backend.ui.display_utils import display_error_with_help
        display_error_with_help(
            "Errores críticos en la configuración",
            "Revisa y corrige backend/utils/unified_config.py antes de continuar",
            "\n".join([f"• {error}" for error in validation_errors]),
        )
        return False

    if warnings:
        print("\n⚠️  Advertencias de configuración:")
        for warning in warnings:
            print(f"   • {warning}")
        print()

    logger.info("✅ Configuración validada correctamente", warnings_count=len(warnings))
    return True


def initialize_components(dry_init: bool = False) -> Dict[str, Any]:
    """Inicializa los componentes del sistema"""
    config = _get_config()
    logger = _get_logger()
    
    logger.info("🧩 Inicializando componentes...", system_startup=True)

    components = {}
    models_dir = Path(config.paths.models_dir)

    with logger.operation("system_initialization"):
        # Inicializar LLM Manager
        def init_llm():
            from src.backend.llm.model_manager import LLMManager
            
            model_path = str(models_dir / config.llm.model_name)
            # In dry mode, skip heavy preload to accelerate smoke checks
            if dry_init:
                logger.info("🧪 Dry init: creando LLMManager sin precargar el modelo")
                return LLMManager(model_path=model_path, preload_model=False)
            if not os.path.exists(model_path):
                logger.warning(f"⚠️ Modelo no encontrado en {model_path}")
                logger.warning(
                    "⚠️ Creando LLMManager con ruta de modelo (se cargará cuando esté disponible)"
                )
                # Crear LLMManager con la ruta configurada aunque el archivo no exista aún
                # El modelo se puede descargar después
                return LLMManager(model_path=model_path, preload_model=False)
            else:
                # Cargar el modelo inmediatamente durante la inicialización para mejor UX
                print("🚀 Cargando modelo LLM...")
                print("   ⏳ Esto puede tomar unos momentos la primera vez...")
                logger.info("🚀 Precargando modelo LLM para mejorar tiempo de respuesta...")
                llm_manager = LLMManager(model_path=model_path, preload_model=True)
                print("   ✅ Modelo cargado exitosamente")
                return llm_manager

        initialize_component("LLM Manager", "llm_manager_init", init_llm, components, "llm")

        # Inicializar Memory Service con LangChain (reemplaza Unified Memory Manager)
        def init_memory_service():
            memory_dir = models_dir / config.paths.memory_dir
            memory_dir.mkdir(exist_ok=True, parents=True)
            
            # Rehabilitar LangChain MemoryService
            MemoryService = _get_memory_service()
            if MemoryService is not None:
                try:
                    mem = MemoryService(
                        session_id="default_session",
                        base_dir=str(memory_dir),
                        window_k=config.memory.max_token_limit if hasattr(config.memory, 'max_token_limit') else 6,
                        enable_summaries=True,
                        summary_threshold_tokens=4000
                    )
                    # Garantizar que la sesión default inicie limpia (sin memoria de corto plazo)
                    try:
                        mem.reset()
                    except Exception:
                        pass
                    return mem
                except Exception as e:
                    logger.warning(f"Error inicializando MemoryService: {e}")
                    return None
            else:
                logger.warning("MemoryService no disponible, usando memoria básica")
                return None

        initialize_component(
            "Memory Service (LangChain)",
            "memory_service_init",
            init_memory_service,
            components,
            "memory",
        )

        # Crear alias para compatibilidad con código existente
        components["enhanced_memory"] = components.get("memory")

        # Ensure LangChain MemoryService key exists; initialize later when session is available
        try:
            lc_mem_cfg = getattr(config.memory, "langchain", None)
        except Exception:
            lc_mem_cfg = None
        if lc_mem_cfg and getattr(lc_mem_cfg, "enable", False) and MemoryService is None:
            logger.warning(
                (
                    "LangChain MemoryService is enabled in config but dependencies are missing "
                    "or incompatible; skipping initialization"
                )
            )
        components["lc_memory"] = None

        # Inicializar Knowledge Base
        def init_knowledge_base():
            from src.backend.llm.knowledge_base import KnowledgeBase
            
            kb_dir = Path(config.paths.models_dir) / config.paths.knowledge_dir
            kb_dir.mkdir(exist_ok=True, parents=True)
            kb = KnowledgeBase(
                embedding_model=config.knowledge_base.embedding_model,
                index_path=str(kb_dir / config.knowledge_base.faiss_index_filename),
                documents_path=str(kb_dir / config.knowledge_base.documents_filename),
            )
            if dry_init:
                logger.info("🧪 Dry init: omitiendo inicialización del índice de KnowledgeBase")
            else:
                kb.initialize_index()
            return kb

        # Permitir desactivar Knowledge Base en entornos mínimos (Jetson/RPi)
        disable_kb_env = str(os.environ.get("DISABLE_KNOWLEDGE_BASE", "")).lower()
        if disable_kb_env in {"1", "true", "yes", "y"}:
            logger.info("⏭️ Knowledge Base desactivada por entorno (DISABLE_KNOWLEDGE_BASE)")
            components["kb"] = None
        else:
            initialize_component(
                "Knowledge Base", "knowledge_base_init", init_knowledge_base, components, "kb"
            )

        # Inicializar Resource Monitor
        def init_resource_monitor():
            from src.backend.utils.resource_monitor import get_resource_monitor
            
            monitor = get_resource_monitor(
                monitoring_interval=config.resource_monitor.monitor_interval,
                history_size=config.resource_monitor.history_size,
                cpu_threshold=config.system.cpu_threshold,
                memory_threshold=config.system.memory_threshold,
                gpu_threshold=config.system.gpu_threshold,
            )

            # Add alert callback for resource warnings
            def resource_alert_handler(message: str, snapshot):
                # Log as info to avoid polluting interactive console
                logger.info(
                    f"🚨 Resource Alert: {message}",
                    alert_type="resource_threshold",
                    cpu_percent=snapshot.cpu_percent,
                    memory_percent=snapshot.memory_percent,
                )

            monitor.add_alert_callback(resource_alert_handler)
            monitor.start_monitoring()

            # Log system info
            system_info = monitor.get_system_info()
            logger.info(
                "Resource Monitor system info",
                cpu_count=system_info.get("cpu_count"),
                memory_total_gb=round(system_info.get("memory_total_gb", 0), 2),
                gpu_count=system_info.get("gpu_count", 0),
            )

            return monitor

        initialize_component(
            "Resource Monitor",
            "resource_monitor_init",
            init_resource_monitor,
            components,
            "resource_monitor",
        )

        # Inicializar Backup Manager
        def init_backup_manager():
            from src.backend.utils.backup_manager import create_backup_manager
            
            backup_manager = create_backup_manager(
                config_obj=config,
                backup_interval_hours=config.backup.interval_hours,
                max_backups=config.backup.max_backups,
                compress_backups=config.backup.compress_backups,
            )

            backup_manager.start_automatic_backup()

            # Log backup status
            status = backup_manager.get_backup_status()
            logger.info(
                "Backup Manager status",
                backup_dir=status["backup_dir"],
                backup_interval_hours=status["config"]["backup_interval_hours"],
                max_backups=status["config"]["max_backups"],
                total_backups=status["total_backups"],
            )
            return backup_manager

        initialize_component(
            "Backup Manager",
            "backup_manager_init",
            init_backup_manager,
            components,
            "backup_manager",
        )

        # Aliases para compatibilidad con otros módulos (health checker, etc.)
        components["llm_manager"] = components.get("llm")
        components["memory_manager"] = components.get("memory")
        components["knowledge_base"] = components.get("kb")

    return components


def cleanup_components(components: Dict[str, Any]):
    """Limpia y cierra todos los componentes del sistema"""
    logger = _get_logger()
    logger.info("🧹 Iniciando limpieza de componentes...")

    cleanup_actions = [
        ("llm", "unload", "LLM descargado"),
        ("backup_manager", "stop_automatic_backup", "Backup Manager detenido"),
        ("resource_monitor", "stop_monitoring", "Resource Monitor detenido"),
        ("memory", "save_memory", "Memoria guardada"),
    ]

    for component_key, method_name, success_msg in cleanup_actions:
        component = components.get(component_key)
        if component:
            try:
                getattr(component, method_name)()
                logger.info(f"✅ {success_msg}")
            except Exception as e:
                handle_component_error(component_key, method_name, e)

    # Special handling for KB (multiple methods)
    if components.get("kb"):
        try:
            components["kb"]._save_index_and_docs()
            components["kb"].save_embedding_cache()
            logger.info("✅ Knowledge Base guardada")
        except Exception as e:
            handle_component_error("Knowledge Base", "save", e)

    logger.info("🏁 Limpieza completada")


def handle_component_error(
    component_name: str, operation: str, error: Exception, fallback_action=None
):
    """Maneja errores de componentes de forma genérica con sistema unificado de errores"""
    error_handler = get_error_handler()

    # Determinar categoría de error basada en el componente
    category_map = {
        "llm": ErrorCategory.MODEL,
        "memory": ErrorCategory.MEMORY,
        "knowledge_base": ErrorCategory.SYSTEM,
        "backup": ErrorCategory.SYSTEM,
    }
    category = category_map.get(component_name.lower(), ErrorCategory.SYSTEM)

    # Manejar error con el sistema unificado
    from src.backend.utils.error_handler import ErrorContext

    handled_error = error_handler.handle_error(
        error, ErrorContext(component_name, operation), ErrorSeverity.MEDIUM, category
    )

    logger.error(f"❌ Error en {component_name} durante {operation}: {handled_error.message}")

    if fallback_action:
        try:
            fallback_action()
            logger.info(f"✅ Acción de fallback ejecutada para {component_name}")
        except Exception as fallback_error:
            fallback_handled = error_handler.handle_error(
                fallback_error,
                ErrorContext(component_name, f"{operation}_fallback"),
                ErrorSeverity.LOW,
                category,
            )
            logger.error(f"❌ Error en fallback para {component_name}: {fallback_handled.message}")
    else:
        from src.backend.ui.display_utils import display_error_with_help
        display_error_with_help(
            f"Error en {component_name}",
            f"Verifica la configuración de {component_name} o reinicia el sistema",
            handled_error.message,
        )

