"""
Modo interactivo adaptativo que puede usar diferentes interfaces de usuario.
Mantiene la funcionalidad existente pero permite cambiar entre consola y PySide6.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from src.backend.utils.unified_config import get_config
from src.backend.utils.unified_logger import get_unified_logger
from src.backend.utils.validators import ValidationError, validate_query_input
from src.backend.utils.tracing import PerformanceTracer
from .ui_abstraction import UIManager, UIState
from .console_ui import ConsoleUI
# Lazy import de PySide6 UI classes dentro de adaptive_interactive_mode()
from .display_utils import display_available_commands, display_error_with_help, display_validation_error
from .command_handlers import (
    handle_help_command, handle_status_command, handle_resources_command,
    handle_clear_command, handle_memory_command, handle_rag_command,
    handle_add_command, handle_list_short_command, handle_list_long_command,
    handle_delete_command
)
from ..core.context_manager import (
    retrieve_memory_context, retrieve_knowledge_base_context, combine_and_limit_context
)
from ..context.text_context_processor import TextContextProcessor

config = get_config()
logger = get_unified_logger("AdaptiveInteractiveMode")

# Initialize performance tracer
tracer = PerformanceTracer(
    enabled=config.tracing.enabled, log_file=str(config.paths.logs_dir / "trace_data.jsonl")
)


def configure_interactive_logging():
    """Configurar todos los loggers para modo interactivo silencioso"""
    import os

    # Configurar variables de entorno para bibliotecas externas
    os.environ["TOKENIZERS_PARALLELISM"] = config.environment.tokenizers_parallelism

    # Configurar el logger principal
    logger.set_console_level(logging.ERROR)

    # Configurar otros loggers estructurados
    from src.backend.utils.unified_logger import get_unified_logger

    loggers_to_silence = ["API", "backend.utils.resource_monitor", "SYSTEM", "MAIN"]

    for logger_name in loggers_to_silence:
        try:
            silent_logger = get_unified_logger(logger_name)
            silent_logger.set_console_level(logging.ERROR)
        except Exception:
            pass

    # Configurar loggers tradicionales
    traditional_loggers = [
        "BackupManager", "Knowledge", "Memory", "LLM", "MemoryLimiter",
        "transformers", "urllib3", "requests", "httpx",
    ]

    for logger_name in traditional_loggers:
        try:
            trad_logger = logging.getLogger(logger_name)
            trad_logger.setLevel(logging.ERROR)
            for handler in trad_logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(logging.ERROR)
        except Exception:
            pass

    # Silenciar el logger root para bibliotecas externas
    logging.getLogger().setLevel(logging.ERROR)


def adaptive_interactive_mode(components: Dict[str, Any], ui_type: str = "console") -> None:
    """
    Modo interactivo adaptativo que puede usar diferentes interfaces.
    
    Args:
        components: Componentes del sistema inicializados
        ui_type: Tipo de interfaz a usar ("console" o "pyside6")
    """
    # Configurar todos los loggers para modo silencioso
    configure_interactive_logging()
    logger.info(f"💬 Modo Interactivo Adaptativo - UI: {ui_type}")

    # Verificar componentes
    llm = components.get("llm")
    memory = components.get("memory")
    enhanced_memory = components.get("enhanced_memory")
    kb = components.get("kb")
    lc_memory = components.get("lc_memory")
    
    # Inicializar procesador de contexto
    context_processor = TextContextProcessor()
    context_stats = context_processor.get_context_stats()
    logger.info(f"📚 Contexto cargado: {context_stats['total_files']} archivos, {context_stats['total_chars']} caracteres")

    if not llm:
        print("⚠️ LLM no inicializado: la UI se abrirá en modo demo (sin respuesta).")
        logger.warning("LLM no inicializado; UI seguirá en modo demo.")

    # Usar Enhanced Memory Manager si está disponible, sino usar el básico
    active_memory = enhanced_memory if enhanced_memory else memory

    # Inicializar sesión de usuario al inicio
    if enhanced_memory:
        try:
            user_session, greeting_message = enhanced_memory.initialize_user_session()
            # If LangChain MemoryService is enabled, re-instantiate with session-specific id
            try:
                lc_mem_cfg = getattr(config.memory, "langchain", None)
            except Exception:
                lc_mem_cfg = None
            if (
                lc_memory
                and lc_mem_cfg
                and getattr(lc_mem_cfg, "enable", False)
            ):
                try:
                    from src.backend.memory.memory_service import MemoryService
                    session_id = getattr(user_session, "user_id", "default") or "default"
                    base_dir = str(Path(config.paths.memory_dir) / "langchain")
                    components["lc_memory"] = MemoryService(
                        session_id=session_id,
                        base_dir=base_dir,
                        window_k=int(getattr(lc_mem_cfg, "window_k", 6)),
                        enable_summaries=bool(getattr(lc_mem_cfg, "enable_summaries", True)),
                        summary_threshold_tokens=int(
                            getattr(lc_mem_cfg, "summary_threshold_tokens", 800)
                        ),
                        retrieval_k=int(getattr(lc_mem_cfg, "retrieval_k", 5)),
                    )
                    lc_memory = components["lc_memory"]
                except Exception as e:
                    logger.warning(f"Failed to bind MemoryService to session: {e}")
        except Exception as e:
            logger.warning(f"Error al inicializar sesión de usuario: {e}")

    # Crear gestor de UI
    ui_manager = UIManager()
    
    # Seleccionar tipo de UI
    app = None
    if ui_type.startswith("pyside6"):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        if ui_type == "pyside6-web":
            try:
                from .pyside6_web_ui import PySide6WebUI
                ui = PySide6WebUI()  # Interfaz híbrida (QWebEngineView)
            except Exception as e:
                logger.error(f"PySide6 Web UI no disponible: {e}")
                ui = ConsoleUI()
        else:
            try:
                from .pyside6_ui import PySide6UI
                ui = PySide6UI()  # Interfaz nativa Qt
            except Exception as e:
                logger.error(f"PySide6 UI no disponible: {e}")
                ui = ConsoleUI()
    else:
        ui = ConsoleUI()
    
    ui_manager.set_ui(ui)
    ui_manager.initialize(components)

    # Configuración de la sesión
    use_rag = False

    def process_user_input(user_input: str) -> None:
        """Procesar entrada del usuario"""
        nonlocal use_rag
        
        # Procesar comandos especiales PRIMERO
        if user_input and user_input.startswith("/"):
            cmd_lower = user_input.lower()

            # Exit commands
            if cmd_lower in ["/salir", "/exit", "/quit"]:
                ui_manager.append_message("👋 ¡Hasta luego! Sesión terminada.", "system")
                return

            # Simple commands (no parameters)
            simple_commands = {
                "/help": lambda: handle_help_command(),
                "/status": lambda: handle_status_command(
                    llm, active_memory, kb, components, use_rag
                ),
                "/resources": lambda: handle_resources_command(components),
                "/clear": lambda: handle_clear_command(active_memory),
                "/memory": lambda: handle_memory_command(active_memory),
                "/list_short": lambda: handle_list_short_command(active_memory),
                "/list_long": lambda: handle_list_long_command(active_memory),
            }

            if cmd_lower in simple_commands:
                simple_commands[cmd_lower]()
                return

            # Parametrized commands
            if cmd_lower.startswith("/rag"):
                use_rag = handle_rag_command(kb, use_rag, user_input)
                return
            elif cmd_lower.startswith("/add "):
                handle_add_command(user_input, kb, active_memory)
                return
            elif cmd_lower.startswith("/delete_short "):
                handle_delete_command(user_input, active_memory, "short")
                return
            elif cmd_lower.startswith("/delete_long "):
                handle_delete_command(user_input, active_memory, "long")
                return
            else:
                ui_manager.show_error("Comando no reconocido. Usa /help para ver todos los comandos disponibles")
                return

        # Procesar entrada regular del usuario
        elif user_input:
            try:
                user_input = validate_query_input(user_input)
                logger.info(f"✅ Entrada validada: {len(user_input)} caracteres")
            except ValidationError as e:
                ui_manager.show_error(f"Entrada inválida: {e}")
                logger.warning(f"Entrada rechazada: {e}")
                return

            # Avisar si no hay LLM activo (modo demo)
            if not llm:
                ui_manager.append_message(
                    "⚠️ LLM no inicializado. Activa un modelo o ejecuta sin --dry-init para obtener respuestas.",
                    "system",
                )
                return

            # Procesar consulta normal
            logger.info(
                f"💬 Procesando consulta: {len(user_input)} caracteres",
                query_length=len(user_input),
                rag_enabled=use_rag,
            )

            # Activar alertas de recursos durante el procesamiento
            resource_monitor = components.get("resource_monitor")
            if resource_monitor:
                resource_monitor.enable_alerts()

            try:
                # Medición E2E completa con tracing
                with tracer.span(
                    "e2e_query_processing", {"user_input_length": len(user_input)}
                ):
                    with logger.operation("interactive_query_processing"):
                        # Preprocessing: input validation and preparation
                        with tracer.span("preprocess", {"input_type": "text"}):
                            timeout = config.llm.response_timeout

                    # RAG: Retrieve and combine context
                    with tracer.span("rag_total", {"use_rag": use_rag}):
                        with tracer.span("memory_retrieval"):
                            # Simplified memory retrieval - avoid LangChain issues
                            memory_context = retrieve_memory_context(
                                active_memory, user_input
                            )

                        with tracer.span("kb_retrieval"):
                            kb_context, use_rag = retrieve_knowledge_base_context(
                                kb, user_input, use_rag
                            )

                        # Obtener contexto de archivos TXT
                        with tracer.span("text_context_retrieval"):
                            text_context = context_processor.get_context_for_query(user_input)
                            if text_context:
                                logger.info(f"📚 Contexto de archivos encontrado: {len(text_context)} caracteres")

                        with tracer.span("context_assembly"):
                            # Get session_id from lc_memory if available
                            session_id = None
                            if lc_memory and hasattr(lc_memory, 'cfg') and hasattr(lc_memory.cfg, 'session_id'):
                                session_id = lc_memory.cfg.session_id
                            
                            # Combinar contexto existente con contexto de archivos
                            context = combine_and_limit_context(
                                memory_context,
                                kb_context,
                                text_context=text_context,
                                session_id=session_id,
                            )
                            
                            # No se requiere manipulación adicional: combine_and_limit_context ya incluye text_context.

                    # LLM: Generate response
                    with tracer.span(
                        "llm_total",
                        {"context_length": len(context) if context else 0, "timeout": timeout},
                    ):
                        with logger.operation("llm_generation"):
                            response = llm.query(
                                user_input,
                                context=[context] if context else None,
                                timeout=timeout,
                            )

                            # Validate response before logging
                            if response is None:
                                response = (
                                    "Lo siento, no pude generar una respuesta en este momento. "
                                    "Por favor, intenta de nuevo."
                                )
                                logger.warning(
                                    "⚠️ LLM retornó None, usando respuesta por defecto"
                                )

                            logger.info(
                                "✅ Respuesta generada",
                                response_length=len(response),
                                context_used=bool(context),
                                timeout=timeout,
                            )

                        # Postprocessing: Save to memory and update session context
                        with tracer.span(
                            "postprocess", {"response_length": len(response) if response else 0}
                        ):
                            if response:
                                # Simplified memory storage - avoid LangChain issues
                                if active_memory:
                                    with logger.operation("memory_storage"):
                                        active_memory.add_interaction(user_input, response)

                                # Update session context if using enhanced memory
                                if enhanced_memory:
                                    try:
                                        enhanced_memory.update_session_context(
                                            user_input, response
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"Error al actualizar contexto de sesión: {e}"
                                        )

            finally:
                # Desactivar alertas de recursos después del procesamiento
                if resource_monitor:
                    resource_monitor.disable_alerts()

            # Log interaction saved
            logger.info(
                "💾 Interacción guardada en memoria",
                user_input_length=len(user_input),
                response_length=len(response),
            )

            # Display response with timing
            with tracer.span("print_total"):
                # Print the actual response FIRST
                ui_manager.append_message(response, "assistant")

                # Get E2E timing from tracer (convert ms to seconds)
                e2e_time_ms = tracer.get_last_span_duration("e2e_query_processing")
                e2e_time = e2e_time_ms / 1000.0 if e2e_time_ms is not None else None

                # Print timing information AFTER the response
                if config.tracing.enable_e2e_timing and e2e_time is not None:
                    timing_msg = f"⏱️ Tiempo E2E: {e2e_time:.3f}s (límite: {timeout}s)"
                    ui_manager.append_message(timing_msg, "system")

                    if timeout * 0.8 < e2e_time < timeout:
                        warning_msg = (
                            "⚠️ Advertencia: La respuesta tardó más del 80% "
                            "del tiempo límite. Considera usar consultas más cortas."
                        )
                        ui_manager.append_message(warning_msg, "system")
                        logger.warning(
                            "Tiempo de respuesta cercano al límite",
                            processing_time=e2e_time,
                            timeout=timeout,
                            percentage=e2e_time / timeout * 100,
                        )

                # Performance metrics from logger (legacy) - also AFTER response
                metrics_summary = logger.get_metrics_summary()
                if metrics_summary.get("total_operations", 0) > 0:
                    avg_time = metrics_summary.get("average_duration_ms", 0) / 1000
                    if not config.tracing.enable_e2e_timing:
                        timing_msg = f"⏱️ Tiempo promedio: {avg_time:.2f}s (límite: {timeout}s)"
                        ui_manager.append_message(timing_msg, "system")

    # Establecer callback para entrada del usuario
    ui_manager.set_user_input_callback(process_user_input)
    
    # Mostrar mensaje de bienvenida
    ui_manager.append_message("✅ ¡Listo para chatear!", "system")
    
    # Ejecutar interfaz
    try:
        # Ejecución según tipo de UI
        if ui_type == "pyside6-web":
            ui.show()
            if app:
                app.exec()
            else:
                logger.error("Error crítico: QApplication no se inicializó para la UI web de PySide6.")
        else:
            # PySide6 nativa o consola ejecutan vía UIManager
            ui_manager.run()
    except KeyboardInterrupt:
        ui_manager.append_message("👋 Interrupción del usuario detectada", "system")
    except Exception as e:
        ui_manager.show_error(f"Error crítico: {e}")
        logger.error(f"❌ Error crítico en modo interactivo: {e}")
    finally:
        ui_manager.cleanup()

