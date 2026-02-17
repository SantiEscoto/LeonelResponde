#!/usr/bin/env python3
"""
🤖 Asistente Multimodal Offline - Fase 1
=========================================

Motor principal del asistente de IA local con capacidades de:
- Procesamiento de lenguaje natural (LLM)
- Memoria conversacional persistente
- Base de conocimiento vectorial (RAG)
- Interfaz interactiva y API REST
- Monitoreo de recursos y protección del sistema

Autor: Assistant
Fecha: 2024
Versión: 1.0.0
"""

# =============================================================================
# IMPORTS Y CONFIGURACIÓN INICIAL
# =============================================================================

# Imports de la librería estándar
import argparse
import os
import sys
import warnings
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess


# Configuración de warnings para reducir ruido en logs
# Esto mejora el rendimiento al evitar procesamiento innecesario de warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", module="urllib3")
warnings.filterwarnings("ignore", module="transformers")
warnings.filterwarnings("ignore", message=".*urllib3 v2 only supports OpenSSL.*")
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")
warnings.filterwarnings("ignore", message=".*torch.utils._pytree._register_pytree_node.*")

# =============================================================================
# LAZY IMPORTS - OPTIMIZACIÓN DE RENDIMIENTO
# =============================================================================


def _get_config():
    """
    Importación perezosa de la configuración unificada.

    Evita imports circulares y reduce el tiempo de inicio del sistema.
    La configuración se carga solo cuando es necesaria.

    Returns:
        UnifiedConfig: Instancia de configuración del sistema
    """
    from src.backend.utils.unified_config import get_config

    return get_config()


def _get_logger():
    """
    Importación perezosa del sistema de logging unificado.

    Proporciona logging estructurado y optimizado para el módulo principal.

    Returns:
        Logger: Instancia del logger configurado
    """
    from src.backend.utils.unified_logger import get_unified_logger

    return get_unified_logger("MAIN")


def _get_optimized_initializer():
    """
    Importación perezosa del inicializador optimizado del sistema.

    Aplica optimizaciones de rendimiento y configuración automática
    basada en el hardware detectado.

    Returns:
        function: Función de inicialización optimizada
    """
    from src.backend.utils.optimized_initializer import initialize_optimized_system

    return initialize_optimized_system


def _get_component_initializer():
    """
    Importación perezosa del gestor de componentes del sistema.

    Maneja la inicialización, validación y limpieza de todos los
    componentes del asistente (LLM, memoria, base de conocimiento, etc.).

    Returns:
        tuple: (initialize_components, cleanup_components, validate_configuration)
    """
    from src.backend.core.component_initializer import (
        initialize_components,
        cleanup_components,
        validate_configuration,
    )

    return initialize_components, cleanup_components, validate_configuration


def _get_system_protection():
    """
    Importación perezosa del sistema de protección contra kernel panics.

    Monitorea recursos del sistema y previene sobrecargas que puedan
    causar reinicios o cuelgues del sistema.

    Returns:
        tuple: (start_system_protection, stop_system_protection)
    """
    from src.backend.utils.system_protection import start_system_protection, stop_system_protection

    return start_system_protection, stop_system_protection


def _get_health_checker():
    """
    Importación perezosa del health checker del sistema.

    Proporciona verificación avanzada de salud de componentes,
    monitoreo de recursos y alertas.

    Returns:
        function: Función para obtener el health checker
    """
    from src.backend.utils.health_checker import get_health_checker

    return get_health_checker


def _get_shutdown_manager():
    """
    Importación perezosa del gestor de graceful shutdown.

    Proporciona manejo avanzado de shutdown con señales del sistema,
    timeouts configurables y limpieza ordenada de recursos.

    Returns:
        function: Función para obtener el shutdown manager
    """
    from src.backend.utils.graceful_shutdown import get_shutdown_manager

    return get_shutdown_manager


def _get_metrics_collector():
    """
    Importación perezosa del recolector de métricas.

    Proporciona recolección, almacenamiento y reporte de métricas
    del sistema, LLM, API y componentes.

    Returns:
        function: Función para obtener el metrics collector
    """
    from src.backend.utils.metrics_collector import get_metrics_collector

    return get_metrics_collector


# =============================================================================
# CONFIGURACIÓN DEL ENTORNO
# =============================================================================


def _configure_environment():
    """
    Configura las variables de entorno necesarias para el funcionamiento óptimo.

    Establece directorios temporales, configuración de PyTorch para Mac,
    y otros ajustes específicos del sistema operativo.

    Returns:
        tuple: (config, logger) - Configuración y logger inicializados
    """
    # Obtener configuración y logger
    config = _get_config()
    logger = _get_logger()

    # Configurar variables de entorno para Mac
    os.environ.update(
        {
            "TMPDIR": config.environment.tmp_dir,
            "TEMP": config.environment.tmp_dir,
            "PYTORCH_ENABLE_MPS_FALLBACK": config.environment.pytorch_mps_fallback,
        }
    )

    # Agregar rutas del proyecto al sys.path
    current_dir = Path(__file__).parent
    sys.path.insert(config.environment.sys_path_index, str(current_dir))

    # Logging de configuración inicial
    logger.info("🔧 Configurando entorno del sistema...")
    logger.info(f"📁 Directorio de trabajo: {current_dir}")
    logger.info(f"🗂️ Directorio temporal: {os.environ.get('TMPDIR', 'No definido')}")
    logger.info(f"🧠 Modelo LLM configurado: {config.llm.model_name}")
    logger.info(f"💻 Dispositivo de procesamiento: {config.llm.device}")

    if config.tracing.enabled:
        logger.info(
            f"📊 Trazado de rendimiento habilitado: {config.paths.logs_dir}/trace_data.jsonl"
        )

    return config, logger


# =============================================================================
# FUNCIONES PRINCIPALES
# =============================================================================


def start_api_server(components: Dict[str, Any]) -> None:
    """
    Inicia el servidor API REST del asistente.

    Proporciona endpoints HTTP para interactuar con el asistente
    de forma programática, incluyendo chat, consultas a la base de
    conocimiento y gestión de memoria.

    Args:
        components (Dict[str, Any]): Diccionario con todos los componentes
                                   inicializados del sistema
    """
    logger = _get_logger()

    try:
        # Importación perezosa del servidor API
        from src.backend.api import start_api

        logger.info("🚀 Iniciando servidor API REST...")

        # Obtener configuración para host y puerto
        config = _get_config()
        start_api(host=config.system.api_host, port=config.system.api_port)

    except ImportError as e:
        logger.error(f"❌ Error importando módulo API: {e}")
        print("❌ El servidor API no está disponible. Verifique la instalación.")
    except Exception as e:
        logger.error(f"❌ Error iniciando servidor API: {e}")
        print(f"❌ No se pudo iniciar el servidor API: {e}")
    finally:
        # Limpieza garantizada de componentes
        try:
            _, cleanup_components, _ = _get_component_initializer()
            cleanup_components(components)
        except Exception as cleanup_error:
            logger.error(f"❌ Error en limpieza de componentes: {cleanup_error}")


def run_integration_tests() -> bool:
    """
    Ejecuta los tests de integración del sistema mediante import directo.

    Returns:
        bool: True si todos los tests pasan, False en caso contrario
    """
    logger = _get_logger()
    try:
        from tests.validate_improvements import main as validate_main

        exit_code = int(validate_main())
        return exit_code == 0
    except ImportError as e:
        logger.error(f"❌ No se pudo importar módulo de tests: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error ejecutando tests de integración: {e}")
        return False


def initialize_system_protection() -> Optional[Any]:
    """
    Inicializa el sistema de protección contra kernel panics.

    Monitorea continuamente el uso de recursos del sistema y
    previene sobrecargas que puedan causar reinicios o cuelgues.

    Returns:
        SystemProtection: Instancia del sistema de protección o None si falla
    """
    logger = _get_logger()

    try:
        start_system_protection, _ = _get_system_protection()
        protection = start_system_protection()
        logger.info("✅ Sistema de protección contra kernel panics activado")
        return protection
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema de protección: {e}")
        print(f"⚠️ Sistema de protección no disponible: {e}")
        return None


def initialize_optimized_system() -> Dict[str, Any]:
    """
    Inicializa el sistema con optimizaciones de rendimiento.

    Aplica configuraciones automáticas basadas en el hardware detectado
    y optimiza parámetros para el mejor rendimiento posible.

    Returns:
        Dict[str, Any]: Estadísticas de inicialización y optimizaciones aplicadas
    """
    logger = _get_logger()

    try:
        initialize_optimized_system = _get_optimized_initializer()
        init_stats = initialize_optimized_system()

        logger.info(
            f"✅ Sistema optimizado inicializado en {init_stats['initialization_time_seconds']:.2f}s"
        )
        logger.info(f"📊 Optimizaciones aplicadas: {init_stats['optimizations_applied']}")

        return init_stats

    except Exception as e:
        logger.warning(f"⚠️ Error en inicialización optimizada: {e}")
        logger.info("🔄 Continuando con inicialización estándar...")
        return {"initialization_time_seconds": 0.0, "optimizations_applied": 0}


def validate_system_configuration() -> bool:
    """
    Valida la configuración del sistema antes del inicio.

    Verifica que todos los archivos necesarios existan, que las
    configuraciones sean válidas y que el sistema esté listo para funcionar.

    Returns:
        bool: True si la configuración es válida, False en caso contrario
    """
    logger = _get_logger()

    try:
        _, _, validate_configuration = _get_component_initializer()

        if validate_configuration():
            logger.info("✅ Configuración del sistema validada correctamente")
            return True
        else:
            logger.error("❌ Configuración del sistema inválida")
            return False
    except Exception as e:
        logger.error(f"❌ Error validando configuración: {e}")
        return False


def initialize_system_components(dry_init: bool = False) -> Dict[str, Any]:
    """
    Inicializa todos los componentes del sistema.

    Carga y configura el LLM, memoria, base de conocimiento,
    monitor de recursos y gestor de respaldos.

    Args:
        dry_init (bool): Si True, inicializa en modo ligero sin precargar modelos

    Returns:
        Dict[str, Any]: Diccionario con todos los componentes inicializados
    """
    logger = _get_logger()

    try:
        initialize_components, _, _ = _get_component_initializer()
        components = initialize_components(dry_init=dry_init)

        logger.info("✅ Todos los componentes del sistema inicializados")
        return components
    except Exception as e:
        logger.error(f"❌ Error inicializando componentes: {e}")
        raise


def initialize_graceful_shutdown(
    components: Dict[str, Any], metrics_collector: Optional[Any] = None
) -> Optional[Any]:
    """
    Inicializa el sistema de graceful shutdown.

    Configura manejadores de señales y callbacks de limpieza
    para un apagado ordenado del sistema.

    Args:
        components: Componentes del sistema que requieren limpieza
        metrics_collector: Colector de métricas para reporte final

    Returns:
        GracefulShutdownManager: Instancia del shutdown manager o None si falla
    """
    logger = _get_logger()

    try:
        get_shutdown_manager_func = _get_shutdown_manager()

        # Configurar timeouts
        shutdown_timeout = 30.0  # 30 segundos para shutdown graceful
        force_timeout = 5.0  # 5 segundos adicionales antes de forzar

        shutdown_manager = get_shutdown_manager_func(
            timeout=shutdown_timeout, force_timeout=force_timeout
        )

        # Registrar callbacks de limpieza por prioridad
        # Prioridad alta (10): Detener servicios activos
        if components.get("api_server"):
            shutdown_manager.register_callback(
                name="stop_api_server",
                callback=lambda: logger.info("🛑 API server detenido"),
                priority=10,
                timeout=3.0,
            )

        # Prioridad media (5): Limpiar componentes principales
        if components.get("llm_manager"):
            shutdown_manager.register_callback(
                name="cleanup_llm_manager",
                callback=lambda: components["llm_manager"].unload()
                if hasattr(components["llm_manager"], "unload")
                else None,
                priority=5,
                timeout=5.0,
                critical=True,  # Crítico: esperar finalización
            )

        if components.get("memory_manager"):
            shutdown_manager.register_callback(
                name="save_memory_state",
                callback=lambda: logger.info("💾 Estado de memoria guardado"),
                priority=5,
                timeout=3.0,
                critical=True,
            )

        if components.get("knowledge_base"):
            shutdown_manager.register_callback(
                name="cleanup_knowledge_base",
                callback=lambda: logger.info("🗑️ Base de conocimiento limpiada"),
                priority=4,
                timeout=2.0,
            )

        # Prioridad media-baja (2): Reporte final de métricas
        if metrics_collector:

            def _final_metrics_report():
                try:
                    metrics_collector.collect_system_metrics()
                    final_summary = metrics_collector.get_stats_summary(window_seconds=60.0)
                    logger.info("📊 Resumen final de métricas (shutdown):")
                    if final_summary.get("categories", {}).get("system"):
                        system_metrics = final_summary["categories"]["system"]
                        cpu = system_metrics.get("system.cpu.percent", {})
                        mem = system_metrics.get("system.memory.percent", {})
                        logger.info(
                            f"  💻 CPU - actual: {cpu.get('current', 0):.1f}%, "
                            f"promedio: {cpu.get('mean', 0):.1f}%, "
                            f"máx: {cpu.get('max', 0):.1f}%"
                        )
                        logger.info(
                            f"  🧠 Memoria - actual: {mem.get('current', 0):.1f}%, "
                            f"promedio: {mem.get('mean', 0):.1f}%, "
                            f"máx: {mem.get('max', 0):.1f}%"
                        )

                    # Resumen de métricas de API
                    api_metrics = final_summary.get("categories", {}).get("api")
                    if api_metrics:
                        req_total = api_metrics.get("api.requests_total", {})
                        req_ok = api_metrics.get("api.requests_success", {})
                        req_err = api_metrics.get("api.requests_error", {})
                        lat_stats = api_metrics.get("api.latency_seconds", {})

                        total = int(req_total.get("current", 0) or 0)
                        ok = int(req_ok.get("current", 0) or 0)
                        err = int(req_err.get("current", 0) or 0)
                        success_rate = (ok / total * 100) if total > 0 else 0.0

                        logger.info(
                            f"  🌐 API - requests: total={total}, ok={ok}, error={err}, "
                            f"success_rate={success_rate:.1f}%"
                        )

                        if lat_stats:
                            avg = float(lat_stats.get("mean", 0) or 0)
                            p50 = float(lat_stats.get("median", 0) or 0)
                            mx = float(lat_stats.get("max", 0) or 0)
                            samples = int(lat_stats.get("count", 0) or 0)
                            logger.info(
                                f"  ⏱️ Latencia API - avg={avg:.3f}s, p50={p50:.3f}s, max={mx:.3f}s, samples={samples}"
                            )
                    else:
                        logger.info("  🌐 API - sin métricas registradas en la ventana")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Error recolectando métricas finales via shutdown manager: {e}"
                    )

            shutdown_manager.register_callback(
                name="finalize_metrics_report",
                callback=_final_metrics_report,
                priority=2,
                timeout=4.0,
            )

        # Prioridad baja (1): Limpieza final
        shutdown_manager.register_callback(
            name="finalize_shutdown",
            callback=lambda: logger.info("🏁 Finalización completada"),
            priority=1,
            timeout=1.0,
        )

        # Configurar manejadores de señales
        shutdown_manager.setup_signal_handlers()

        logger.info("✅ Graceful Shutdown Manager inicializado")
        logger.info(f"⏱️ Timeouts: graceful={shutdown_timeout}s, force={force_timeout}s")

        return shutdown_manager

    except Exception as e:
        logger.error(f"❌ Error inicializando shutdown manager: {e}")
        print(f"⚠️ Shutdown manager no disponible: {e}")
        return None


# --- en main(), actualizar la llamada ---
# 8. Inicialización del graceful shutdown
# logger.info("🛡️ Inicializando graceful shutdown...")
# shutdown_manager = initialize_graceful_shutdown(components)

# --- añadir reporte al finalizar API ---
# if args.api:
#     logger.info("🌐 Iniciando servidor API...")
#     start_api_server(components)
#     # Reporte final de métricas y shutdown (simétrico al modo interactivo)
#     if metrics_collector:
#         try:
#             metrics_collector.collect_system_metrics()
#             final_summary = metrics_collector.get_stats_summary(window_seconds=60.0)
#             logger.info("📊 Resumen final de métricas:")
#             if final_summary.get('categories', {}).get('system'):
#                 system_metrics = final_summary['categories']['system']
#                 cpu = system_metrics.get('system.cpu.percent', {})
#                 mem = system_metrics.get('system.memory.percent', {})
#                 logger.info(
#                     f"  💻 CPU - actual: {cpu.get('current', 0):.1f}%, "
#                     f"promedio: {cpu.get('mean', 0):.1f}%, "
#                     f"máx: {cpu.get('max', 0):.1f}%"
#                 )
#                 logger.info(
#                     f"  🧠 Memoria - actual: {mem.get('current', 0):.1f}%, "
#                     f"promedio: {mem.get('mean', 0):.1f}%, "
#                     f"máx: {mem.get('max', 0):.1f}%"
#                 )
#         except Exception as e:
#             logger.warning(f"⚠️ Error recolectando métricas finales: {e}")
#     if shutdown_manager:
#         try:
#             stats = shutdown_manager.get_stats()
#             if stats.duration > 0:
#                 logger.info(
#                     f"📊 Estadísticas de shutdown: "
#                     f"duración={stats.duration:.2f}s, "
#                     f"callbacks_ok={stats.callbacks_executed}, "
#                     f"callbacks_fail={stats.callbacks_failed}, "
#                     f"fase={stats.phase.value if hasattr(stats, 'phase') else 'unknown'}"
#                 )
#         except Exception as e:
#             logger.warning(f"⚠️ Error obteniendo estadísticas de shutdown: {e}")


def initialize_metrics_collector() -> Optional[Any]:
    """
    Inicializa el sistema de recolección de métricas.

    Configura recolección automática de métricas del sistema,
    LLM, API y componentes personalizados.

    Returns:
        MetricsCollector: Instancia del metrics collector o None si falla
    """
    logger = _get_logger()

    try:
        get_metrics_collector_func = _get_metrics_collector()

        # Intervalo de recolección automática (segundos)
        collection_interval = 10.0

        metrics_collector = get_metrics_collector_func(collection_interval=collection_interval)

        # Recolectar métricas iniciales del sistema
        logger.info("📊 Recolectando métricas iniciales del sistema...")
        metrics_collector.collect_system_metrics()

        # Log de métricas iniciales
        summary = metrics_collector.get_stats_summary(window_seconds=5.0)
        if summary.get("categories", {}).get("system"):
            system_metrics = summary["categories"]["system"]
            cpu = system_metrics.get("system.cpu.percent", {}).get("current", 0)
            mem = system_metrics.get("system.memory.percent", {}).get("current", 0)
            logger.info(f"📊 Métricas iniciales - CPU: {cpu:.1f}%, Memoria: {mem:.1f}%")

        logger.info(f"✅ Metrics Collector inicializado (interval: {collection_interval}s)")

        return metrics_collector

    except Exception as e:
        logger.error(f"❌ Error inicializando metrics collector: {e}")
        print(f"⚠️ Metrics collector no disponible: {e}")
        return None


def initialize_health_checker(components: Dict[str, Any]) -> Optional[Any]:
    """
    Inicializa el sistema de health checks.

    Configura verificaciones automáticas de salud del sistema,
    monitoreo de componentes y sistema de alertas.

    Args:
        components: Componentes del sistema a monitorear

    Returns:
        HealthChecker: Instancia del health checker o None si falla
    """
    logger = _get_logger()

    try:
        get_health_checker_func = _get_health_checker()

        # Configurar umbrales de alerta personalizados
        alert_thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time": 5.0,
        }

        health_checker = get_health_checker_func(alert_thresholds=alert_thresholds)

        # Ejecutar primer health check
        logger.info("🏥 Ejecutando health check inicial del sistema...")
        initial_health = health_checker.check_system_health(components)

        logger.info(
            f"🏥 Health Checker inicializado - Estado: {initial_health.overall_status.value}"
        )

        return health_checker
    except Exception as e:
        logger.error(f"❌ Error inicializando health checker: {e}")
        print(f"⚠️ Health checker no disponible: {e}")
        return None


def run_health_check(health_checker: Optional[Any], components: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta una verificación de salud del sistema.

    Args:
        health_checker: Instancia del health checker
        components: Componentes del sistema a verificar

    Returns:
        Dict con el resultado del health check
    """
    logger = _get_logger()

    if not health_checker:
        logger.warning("⚠️ Health checker no disponible")
        return {"status": "unknown", "message": "Health checker not initialized"}

    try:
        health_status = health_checker.check_system_health(components)
        return health_status.to_dict()
    except Exception as e:
        logger.error(f"❌ Error ejecutando health check: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "timestamp": __import__("time").time(),
        }


def cleanup_system_resources(
    components: Dict[str, Any],
    protection: Optional[Any] = None,
    health_checker: Optional[Any] = None,
) -> None:
    """
    Limpia todos los recursos del sistema de forma segura.

    Cierra conexiones, guarda datos, libera memoria y detiene
    todos los procesos en segundo plano.

    Args:
        components (Dict[str, Any]): Componentes del sistema a limpiar
        protection (Optional[Any]): Sistema de protección a detener
        health_checker (Optional[Any]): Health checker a detener
    """
    logger = _get_logger()

    try:
        # Ejecutar health check final antes de cerrar
        if health_checker and components:
            logger.info("🏥 Ejecutando health check final...")
            try:
                final_health = run_health_check(health_checker, components)
                logger.info(
                    f"📊 Estado final del sistema: {final_health.get('overall_status', 'unknown')}"
                )
            except Exception as e:
                logger.warning(f"⚠️ Error en health check final: {e}")

        # Limpiar componentes del sistema
        _, cleanup_components, _ = _get_component_initializer()
        cleanup_components(components)

        # Detener sistema de protección
        if protection:
            protection.stop_monitoring()

        logger.info("✅ Limpieza de recursos completada")
    except Exception as e:
        logger.error(f"❌ Error en limpieza de recursos: {e}")


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================


def start_voice_ws_server_process(
    host: Optional[str] = None, port: Optional[int] = None, model_path: Optional[str] = None
):
    """Start the Voice WebSocket server as a background process using unified config."""
    logger = _get_logger()
    try:
        config = _get_config()
        env = os.environ.copy()
        effective_host = host or getattr(config.voice, "ws_host", "127.0.0.1")
        effective_port = port or getattr(config.voice, "ws_port", 8010)
        env["VOICE_WS_HOST"] = str(effective_host)
        env["VOICE_WS_PORT"] = str(effective_port)

        # Model path resolution: prefer config.voice.vosk_model_path, else small-es fallback under project root
        if model_path:
            env["VOSK_MODEL_PATH"] = model_path
        else:
            cfg_model = getattr(config.voice, "vosk_model_path", None)
            if cfg_model:
                env["VOSK_MODEL_PATH"] = str(cfg_model)
            else:
                root = config.paths.project_root
                small = root / "models" / "voice" / "vosk-model-small-es-0.42"
                full = root / "models" / "voice" / "vosk-model-es-0.42"
                chosen = small if small.exists() else full
                env["VOSK_MODEL_PATH"] = str(chosen)

        cmd = [sys.executable, "-m", "Assistant.src.mcp_servers.voice_ws_server"]
        proc = subprocess.Popen(cmd, env=env, cwd=str(config.paths.project_root))
        logger.info(
            f"🔊 Voice WS server lanzado en ws://{env.get('VOICE_WS_HOST')}:{env.get('VOICE_WS_PORT')}"
        )
        return proc
    except Exception as e:
        logger.error(f"❌ No se pudo iniciar Voice WS server: {e}")
        return None


def main() -> None:
    """
    Función principal del asistente multimodal.

    Maneja la inicialización del sistema, procesamiento de argumentos
    de línea de comandos, y ejecución del modo solicitado (interactivo o API).

    Flujo de ejecución:
    1. Configuración del entorno
    2. Procesamiento de argumentos
    3. Inicialización optimizada del sistema
    4. Activación del sistema de protección
    5. Validación de configuración
    6. Ejecución de tests (si se solicita)
    7. Inicialización de componentes
    8. Ejecución del modo solicitado
    9. Limpieza de recursos
    """
    # Configurar entorno y obtener logger
    config, logger = _configure_environment()

    # Configurar parser de argumentos de línea de comandos
    parser = argparse.ArgumentParser(
        description="🤖 Asistente Multimodal Offline - Motor de IA local con memoria y base de conocimiento",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                    # Modo interactivo consola (por defecto)
  python main.py --interactive      # Modo interactivo explícito
  python main.py --ui pyside6       # Interfaz gráfica moderna
  python main.py --api              # Servidor API REST
  python main.py --test             # Ejecutar tests de integración
  python main.py --dry-init         # Inicialización ligera para pruebas
        """,
    )

    parser.add_argument(
        "--api", action="store_true", help="Iniciar servidor API REST en lugar del modo interactivo"
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Iniciar modo interactivo de chat (por defecto)"
    )
    parser.add_argument("--test", action="store_true", help="Ejecutar tests de integración y salir")
    parser.add_argument(
        "--dry-init",
        action="store_true",
        help="Inicialización ligera sin precargar modelos pesados (útil para pruebas)",
    )
    parser.add_argument(
        "--ui",
        choices=["console", "pyside6", "pyside6-web"],
        default="console",
        help="Tipo de interfaz de usuario (console, pyside6 o pyside6-web)",
    )

    parser.add_argument(
        "--voice-ws",
        action="store_true",
        help="Iniciar servidor Voice WebSocket junto con el asistente",
    )

    args = parser.parse_args()

    # Banner de inicio
    print("🤖 ASISTENTE MULTIMODAL OFFLINE - FASE 1")
    print("=" * 50)
    print("Motor de IA local con memoria persistente y base de conocimiento")
    print("=" * 50)

    # Variables para limpieza garantizada
    components = None
    protection = None
    health_checker = None
    shutdown_manager = None
    metrics_collector = None
    voice_ws_proc = None

    try:
        # 1. Inicialización del sistema de métricas
        logger.info("📊 Inicializando sistema de métricas...")
        metrics_collector = initialize_metrics_collector()

        # 2. Inicializada del sistema optimizada
        logger.info("🚀 Inicializando sistema optimizado...")
        init_stats = initialize_optimized_system()

        # 3. Inicialización del sistema de protección
        logger.info("🛡️ Inicializando sistema de protección...")
        protection = initialize_system_protection()

        # 4. Validación de configuración
        logger.info("🔍 Validando configuración del sistema...")
        if not validate_system_configuration():
            logger.error("❌ Configuración inválida, abortando inicio")
            sys.exit(1)

        # 5. Ejecución de tests si se solicita
        if args.test:
            logger.info("🧪 Ejecutando tests de integración...")
            success = run_integration_tests()

            if success:
                print("✅ Todos los tests pasaron exitosamente")
                sys.exit(0)
            else:
                print("❌ Algunos tests fallaron")
                sys.exit(1)

        # 6. Determinar modo de ejecución (interactivo por defecto)
        if not (args.api or args.interactive):
            args.interactive = True

        # 7. Inicialización de componentes del sistema
        logger.info("🧩 Inicializando componentes del sistema...")
        components = initialize_system_components(dry_init=args.dry_init)

        # 7.1 Opcional: iniciar servidor de voz WebSocket
        if args.voice_ws:
            logger.info("🔊 Iniciando servidor Voice WebSocket...")
            voice_ws_proc = start_voice_ws_server_process()

        # 8. Inicialización del graceful shutdown
        logger.info("🛡️ Inicializando graceful shutdown...")
        shutdown_manager = initialize_graceful_shutdown(components, metrics_collector)

        # 9. Inicialización del health checker
        logger.info("🏥 Inicializando health checker...")
        health_checker = initialize_health_checker(components)

        # 10. Recolectar métricas post-inicialización
        if metrics_collector:
            metrics_collector.collect_system_metrics()
            logger.info("📊 Métricas post-inicialización recolectadas")

        # 11. Ejecución del modo solicitado
        if args.api:
            logger.info("🌐 Iniciando servidor API...")
            start_api_server(components)

        elif args.interactive:
            logger.info(f"💬 Iniciando modo interactivo con UI: {args.ui}...")
            from src.backend.ui.adaptive_interactive_mode import adaptive_interactive_mode

            adaptive_interactive_mode(components, ui_type=args.ui)

        logger.info("👋 Asistente finalizado correctamente")

    except KeyboardInterrupt:
        logger.info("👋 Interrupción del usuario detectada")
        print("\n👋 Saliendo del asistente...")

    except SystemExit:
        # Permitir que SystemExit se propague normalmente
        raise

    except Exception as e:
        logger.error(f"❌ Error crítico en función principal: {e}")
        print(f"❌ Error crítico: {e}")
        sys.exit(1)

    finally:
        # Limpieza garantizada de recursos
        try:
            if components or protection or health_checker:
                logger.info("🧹 Limpiando recursos del sistema...")
                cleanup_system_resources(components or {}, protection, health_checker)

            # Detener Voice WS server si está activo
            try:
                if voice_ws_proc:
                    voice_ws_proc.terminate()
                    voice_ws_proc.wait(timeout=5)
                    logger.info("🔇 Voice WS server detenido")
            except Exception as e:
                logger.warning(f"⚠️ Error deteniendo Voice WS server: {e}")
        except Exception as cleanup_error:
            print(f"⚠️ Error en limpieza final: {cleanup_error}")


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    """
    Punto de entrada principal del script.

    Se ejecuta solo cuando el archivo se llama directamente,
    no cuando se importa como módulo.
    """
    main()
