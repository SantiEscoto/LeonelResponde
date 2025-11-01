"""
Interactive mode implementation for the assistant application.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from src.backend.utils.unified_config import get_config
from src.backend.utils.unified_logger import get_unified_logger
from src.backend.utils.validators import ValidationError, validate_query_input
from src.backend.utils.tracing import PerformanceTracer
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

config = get_config()
logger = get_unified_logger("InteractiveMode")

# Initialize performance tracer
tracer = PerformanceTracer(
    enabled=config.tracing.enabled, log_file=str(config.paths.logs_dir / "trace_data.jsonl")
)


def configure_interactive_logging():
    """Configurar todos los loggers para modo interactivo silencioso"""
    # Use module-level imports for logging and os to avoid redefinitions in function scope
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
            # Silently ignore logging configuration issues for structured loggers
            pass

    # Configurar loggers tradicionales
    traditional_loggers = [
        "BackupManager",
        "Knowledge",
        "Memory",
        "LLM",
        "MemoryLimiter",
        "transformers",
        "urllib3",
        "requests",
        "httpx",
    ]

    for logger_name in traditional_loggers:
        try:
            trad_logger = logging.getLogger(logger_name)
            trad_logger.setLevel(logging.ERROR)
            for handler in trad_logger.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(logging.ERROR)
        except Exception:
            # Silently ignore logging configuration issues for traditional loggers
            pass

    # Silenciar el logger root para bibliotecas externas
    logging.getLogger().setLevel(logging.ERROR)


def interactive_mode(components: Dict[str, Any]):
    """Modo interactivo con LLM, memoria y base de conocimiento"""
    # Configurar todos los loggers para modo silencioso
    configure_interactive_logging()
    logger.info("\n💬 Modo Interactivo Avanzado")

    print("\n🤖 Asistente Personal Leonel - Modo Interactivo")
    print(config.ui.separator_line)
    print("📋 Comandos disponibles:")
    print()
    display_available_commands()
    print(config.ui.separator_line)
    print("💬 Escribe tu mensaje o usa un comando:")

    # Verificar componentes
    llm = components.get("llm")
    memory = components.get("memory")
    enhanced_memory = components.get("enhanced_memory")
    kb = components.get("kb")
    lc_memory = components.get("lc_memory")

    if not llm:
        print("❌ LLM no inicializado, no se puede iniciar modo interactivo")
        logger.error("❌ LLM no inicializado, no se puede iniciar modo interactivo")
        return

    # Usar Enhanced Memory Manager si está disponible, sino usar el básico
    active_memory = enhanced_memory if enhanced_memory else memory

    # Inicializar sesión de usuario al inicio (sin saludo inicial en pantalla)
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
                and MemoryService is not None
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

    print("✅ ¡Listo para chatear!")

    # Configuración de la sesión
    use_rag = False

    while True:
        try:
            user_input = input("\n👤 Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 ¡Hasta luego! Sesión terminada.")
            break

        # Procesar comandos especiales PRIMERO
        if user_input and user_input.startswith("/"):
            cmd_lower = user_input.lower()

            # Exit commands
            if cmd_lower in ["/salir", "/exit", "/quit"]:
                print("\n👋 ¡Hasta luego! Sesión terminada.")
                break

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
                continue

            # Parametrized commands
            if cmd_lower.startswith("/rag"):
                use_rag = handle_rag_command(kb, use_rag, user_input)
                continue
            elif cmd_lower.startswith("/add "):
                handle_add_command(user_input, kb, active_memory)
                continue
            elif cmd_lower.startswith("/delete_short "):
                handle_delete_command(user_input, active_memory, "short")
                continue
            elif cmd_lower.startswith("/delete_long "):
                handle_delete_command(user_input, active_memory, "long")
                continue
            else:
                display_error_with_help(
                    "Comando no reconocido", "Usa /help para ver todos los comandos disponibles"
                )
                continue

        # Procesar entrada regular del usuario
        elif user_input:
            try:
                user_input = validate_query_input(user_input)
                logger.info(f"✅ Entrada validada: {len(user_input)} caracteres")
            except ValidationError as e:
                display_validation_error(e, "consulta")
                logger.warning(f"Entrada rechazada: {e}")
                continue

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

                        with tracer.span("context_assembly"):
                            # Get session_id from lc_memory if available
                            session_id = None
                            if lc_memory and hasattr(lc_memory, 'cfg') and hasattr(lc_memory.cfg, 'session_id'):
                                session_id = lc_memory.cfg.session_id
                            
                            context = combine_and_limit_context(memory_context, kb_context, session_id=session_id)

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
                print(
                    f"🤖 Asistente: {response}",
                    flush=config.FLUSH_CONSOLE_OUTPUT,
                )
                print()  # Add a blank line for better readability

                # Get E2E timing from tracer (convert ms to seconds)
                e2e_time_ms = tracer.get_last_span_duration("e2e_query_processing")
                e2e_time = e2e_time_ms / 1000.0 if e2e_time_ms is not None else None

                # Print timing information AFTER the response
                if config.tracing.enable_e2e_timing and e2e_time is not None:
                    print(f"⏱️  Tiempo E2E: {e2e_time:.3f}s (límite: {timeout}s)", flush=True)

                    if timeout * 0.8 < e2e_time < timeout:
                        print(
                            (
                                "⚠️  Advertencia: La respuesta tardó más del 80% "
                                "del tiempo límite."
                            ),
                            flush=True,
                        )
                        print(
                            (
                                "   Considera usar consultas más cortas o ajustar "
                                "el timeout en backend/utils/unified_config.py"
                            ),
                            flush=True,
                        )
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
                    if (
                        not config.tracing.enable_e2e_timing
                    ):  # Solo mostrar si no hay E2E timing
                        print(
                            (f"⏱️  Tiempo promedio: {avg_time:.2f}s " f"(límite: {timeout}s)"),
                            flush=True,
                        )

