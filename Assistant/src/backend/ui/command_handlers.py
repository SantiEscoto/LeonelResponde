"""
Command handlers for the interactive mode - Fixed with lazy imports.
"""

import os

def _get_config():
    """Lazy import of config to avoid circular imports"""
    from src.backend.utils.unified_config import get_config
    return get_config()

def _get_logger():
    """Lazy import of logger to avoid circular imports"""
    from src.backend.utils.unified_logger import get_unified_logger
    return get_unified_logger("CommandHandlers")


def handle_help_command():
    """Handle the /help command."""
    config = _get_config()
    print("\n" + config.ui.separator_line)
    print("🤖 COMANDOS DISPONIBLES:")
    print()
    from .display_utils import display_available_commands
    display_available_commands()
    print(config.ui.separator_line)


def handle_status_command(llm, memory, kb, components, use_rag):
    """Handle the /status command."""
    print("📊 Estado del Sistema")

    try:
        # Get component statuses
        llm_status = llm.get_status() if llm else {}
        
        # MemoryService status - create compatible status dict
        memory_status = {}
        if memory:
            try:
                # Get messages from memory history
                if hasattr(memory, 'history') and hasattr(memory.history, 'messages'):
                    messages = list(memory.history.messages)
                    total_messages = len(messages)
                else:
                    messages = []
                    total_messages = 0
                
                memory_status = {
                    "session_id": getattr(memory.cfg, 'session_id', 'default'),
                    "total_messages": total_messages,
                    "context_messages": len(messages),
                    "has_summary": bool(getattr(memory, 'summary_text', None)),
                    "window_size": getattr(memory, 'window_k', 0)
                }
            except Exception as e:
                memory_status = {"error": str(e)}
        
        kb_status = kb.get_status() if kb else {}

        # Get resource information
        resource_monitor = components.get("resource_monitor")
        current_snapshot = resource_monitor.get_current_snapshot() if resource_monitor else None
        gpu_info = (
            resource_monitor.get_enhanced_gpu_info() if resource_monitor else {"available": False}
        )

        # Format GPU status
        if gpu_info["available"]:
            if gpu_info["type"] == "mps" and gpu_info["devices"]:
                gpu_status = f"✅ {gpu_info['devices'][0]['name']} (MPS)"
            elif gpu_info["type"] == "cuda":
                gpu_status = f"✅ {len(gpu_info['devices'])} CUDA device(s)"
            else:
                gpu_status = f"✅ {gpu_info['type'].upper()}"
        else:
            gpu_status = "❌ No disponible"

        # Line 1: LLM Status
        model_name = os.path.basename(llm_status.get("model_path", "No cargado"))
        llm_loaded = "✅" if llm_status.get("is_loaded", False) else "❌"
        llm_optimized = "✅" if llm_status.get("optimized", False) else "❌"
        print(
            f"🧠 LLM:\t\t{model_name[:25]:<25}\tCargado: {llm_loaded}\tOptimizado: {llm_optimized}"
        )

        # Line 2: LLM Parameters
        max_tokens = llm_status.get("max_tokens", 256)
        context_size = llm_status.get("context_size", 2048)
        temperature = llm_status.get("params", {}).get("temperature", 0.7)
        print(f"\t\tTokens: {max_tokens:<8}\tContexto: {context_size:<8}\tTemp: {temperature}")

        # Line 3: Memory Status
        session_id = memory_status.get("session_id", "N/A")
        total_messages = memory_status.get("total_messages", 0)
        context_messages = memory_status.get("context_messages", 0)
        has_summary = "✅" if memory_status.get("has_summary", False) else "❌"
        window_size = memory_status.get("window_size", 0)
        print(
            (
                f"💾 Memoria:\tSesión: {session_id:<12}\t"
                f"Total: {total_messages:<8}\t"
                f"Contexto: {context_messages}/{window_size}\t"
                f"Resumen: {has_summary}"
            )
        )

        # Line 4: Knowledge Base
        doc_count = kb_status.get("document_count", 0)
        embedding_model = kb_status.get("embedding_model", "No disponible")[:20]
        rag_status = "✅" if use_rag else "❌"
        print(
            (
                f"📚 Base Conocimiento:\tDocumentos: {doc_count:<8}\t"
                f"Modelo: {embedding_model:<20}\t"
                f"RAG: {rag_status}"
            )
        )

        # Line 6: CPU and Memory
        if current_snapshot:
            cpu_percent = current_snapshot.cpu_percent
            mem_percent = current_snapshot.memory_percent
            mem_used_gb = current_snapshot.memory_used_mb // 1024
            mem_total_gb = (
                current_snapshot.memory_used_mb + current_snapshot.memory_available_mb
            ) // 1024
            print(
                (
                    "💻 CPU:\t\t{cpu:5.1f}% utilizado\t\t💾 RAM:\t\t{mem:5.1f}% "
                    "({used}GB/{total}GB)"
                ).format(cpu=cpu_percent, mem=mem_percent, used=mem_used_gb, total=mem_total_gb)
            )
        else:
            print("💻 CPU:\t\tNo disponible\t\t💾 RAM:\t\tNo disponible")

        # Line 7: Disk and GPU
        if current_snapshot:
            disk_percent = current_snapshot.disk_usage_percent
            process_count = current_snapshot.process_count
            print(f"💽 Disco:\t{disk_percent:5.1f}% utilizado\t\t🎮 GPU:\t\t{gpu_status}")
        else:
            print(f"💽 Disco:\tNo disponible\t\t🎮 GPU:\t\t{gpu_status}")

        # Line 8: Process count and GPU details (if available)
        if current_snapshot:
            if gpu_info["available"] and gpu_info["devices"]:
                device = gpu_info["devices"][0]
                if device.get("memory_unified"):
                    gpu_detail = "Memoria unificada"
                elif device.get("memory_total"):
                    gpu_detail = f"{device.get('memory_total', 0):,}MB total"
                else:
                    gpu_detail = device.get("type", "Detalles N/A")
                print(f"⚙️ Procesos:\t{process_count} activos\t\t\t🔧 GPU Info:\t{gpu_detail}")
            else:
                print(f"⚙️ Procesos:\t{process_count} activos")

        # Line 9: Conversation history
        conv_length = llm_status.get("conversation_length", 0)
        timeout = llm_status.get("timeout", 30)
        print(f"💬 Historial:\t{conv_length} mensajes\t\t\t⏱️ Timeout:\t{timeout}s")

    except Exception as e:
        logger = _get_logger()
        logger.error(f"Error obteniendo estado del sistema: {e}")
        print(f"❌ Error obteniendo estado del sistema: {str(e)}")


def handle_resources_command(components):
    """Handle the /resources command."""
    resource_monitor = components.get("resource_monitor")
    if resource_monitor:
        try:
            config = _get_config()
            print("\n📊 Monitoreo Detallado de Recursos")
            print("═" * 50)

            # Información del sistema
            system_info = resource_monitor.get_system_info()
            print("🖥️ INFORMACIÓN DEL SISTEMA:")
            print(
                ("  - CPU: {cpu} núcleos físicos, " "{cpu_logical} lógicos").format(
                    cpu=system_info["cpu_count"], cpu_logical=system_info["cpu_count_logical"]
                )
            )
            print(f"  - RAM Total: {system_info['memory_total_gb']:.1f} GB")
            print(f"  - Disco Total: {system_info['disk_total_gb']:.1f} GB")
            print(f"  - PID del proceso: {system_info['python_process_pid']}")

            # Estado actual
            current = resource_monitor.get_current_snapshot()
            print("\n📈 ESTADO ACTUAL:")
            print(f"  - CPU: {current.cpu_percent:.1f}%")
            memory_total_mb = current.memory_used_mb + current.memory_available_mb
            print(
                ("  - RAM: {mem_percent:.1f}% (" "{used:.0f}MB / {total:.0f}MB)").format(
                    mem_percent=current.memory_percent,
                    used=current.memory_used_mb,
                    total=memory_total_mb,
                )
            )
            print(f"  - Disco: {current.disk_usage_percent:.1f}%")
            print(f"  - Procesos activos: {current.process_count}")

            # GPU si está disponible
            if current.gpu_usage:
                print("\n🎮 ESTADO GPU:")
                for gpu in current.gpu_usage:
                    print(f"  - GPU {gpu['id']} ({gpu['name']}):")
                    print(f"    • Carga: {gpu['load']:.1f}%")
                    print(
                        ("    • Memoria: {pct:.1f}% (" "{used:.0f}MB / {total:.0f}MB)").format(
                            pct=gpu["memory_percent"],
                            used=gpu["memory_used"],
                            total=gpu["memory_total"],
                        )
                    )
                    print(f"    • Temperatura: {gpu['temperature']:.0f}°C")
            else:
                print("\n🎮 GPU: No disponible o no detectada")

            # Promedios históricos
            avg_usage = resource_monitor.get_average_usage(
                last_n=config.resource_monitor.average_usage_samples
            )
            if avg_usage:
                print(
                    (
                        "\n📊 PROMEDIOS (últimas "
                        f"{config.resource_monitor.average_usage_samples}"
                        " mediciones):"
                    )
                )
                print(f"  - CPU promedio: {avg_usage.get('cpu_percent', 0):.1f}%")
                print(f"  - RAM promedio: {avg_usage.get('memory_percent', 0):.1f}%")
                print(f"  - Procesos promedio: {avg_usage.get('process_count', 0):.0f}")

            # Historial de alertas si las hay
            history = resource_monitor.get_history()
            if history:
                recent_alerts = [
                    h for h in history[-20:] if h.cpu_percent > 80 or h.memory_percent > 80
                ]
                if recent_alerts:
                    print(
                        (
                            "\n⚠️ ALERTAS RECIENTES ("
                            f"{len(recent_alerts)}"
                            " en las últimas 20 mediciones):"
                        )
                    )
                    for alert in recent_alerts[-3:]:  # Mostrar solo las 3 más recientes
                        timestamp = alert.timestamp.strftime("%H:%M:%S")
                        print(
                            f"  - {timestamp}: CPU {alert.cpu_percent:.1f}%, "
                            f"RAM {alert.memory_percent:.1f}%"
                        )

            print("═" * 50)

        except Exception as e:
            logger = _get_logger()
            logger.error(f"Error obteniendo información detallada de recursos: {e}")
            from .display_utils import display_error_with_help
            display_error_with_help(
                "Error obteniendo información detallada de recursos",
                "Verifica que el monitor de recursos esté funcionando correctamente",
                str(e),
            )
    else:
        from .display_utils import display_component_unavailable_error
        display_component_unavailable_error(
            "Monitor de recursos", "Reinicia el sistema o verifica la configuración del monitor"
        )


def handle_clear_command(memory):
    """Handle the /clear command."""
    if memory:
        try:
            memory.reset()
            # Si la memoria soporta cambio de sesión, volver a default_session
            if hasattr(memory, "switch_to_default_session"):
                try:
                    memory.switch_to_default_session()
                    # Asegurar que la nueva default quede completamente limpia
                    try:
                        memory.reset()
                    except Exception:
                        pass
                except Exception:
                    pass
            print(
                (
                    "\n🧹 Memoria limpiada completamente\n"
                    "   ✅ Historial de mensajes: Limpiado\n"
                    "   ✅ Resumen de sesión: Eliminado\n"
                    "   ↩️ Sesión activa: default_session"
                )
            )
        except Exception as e:
            print(f"\n❌ Error al limpiar memoria: {e}")
    else:
        from .display_utils import display_component_unavailable_error
        display_component_unavailable_error(
            "Memoria", "Reinicia el sistema o verifica la configuración de memoria"
        )


def handle_memory_command(memory):
    """Handle the /memory command."""
    if not memory:
        return print("\n❌ Error: Memoria no disponible")

    try:
        from .display_utils import display_section_header, display_status_item
        
        # Get memory status using the new API
        if hasattr(memory, 'history') and hasattr(memory.history, 'messages'):
            context_messages = list(memory.history.messages)
            total_messages = len(context_messages)
        else:
            context_messages = []
            total_messages = 0
        
        has_summary = bool(memory.summary_text) if hasattr(memory, 'summary_text') else False
        window_size = memory.window_k if hasattr(memory, 'window_k') else 0
        
        display_section_header("💾 Estado de la Memoria", "─" * 35)

        status_items = [
            ("📝 Mensajes en contexto", f"{len(context_messages)} mensajes"),
            ("🗄️ Total de mensajes", f"{total_messages} mensajes"),
            ("📊 Tamaño de ventana", f"{window_size} mensajes"),
            ("📋 Resumen disponible", "✅ Sí" if has_summary else "❌ No"),
        ]

        for label, value in status_items:
            display_status_item(label, value)

        if context_messages:
            print("\n📋 Últimos 3 mensajes en contexto:")
            for i, msg in enumerate(context_messages[-3:], 1):
                if hasattr(msg, 'content'):
                    content = msg.content[:80] + ("..." if len(msg.content) > 80 else "")
                    msg_type = "Usuario" if hasattr(msg, 'type') and msg.type == 'human' else "Asistente"
                    print(f"   {i}. [{msg_type}] {content}")
                else:
                    print(f"   {i}. [Mensaje con formato incorrecto]")
        print("─" * 35)
    except Exception as e:
        print(f"\n❌ Error al obtener estado de memoria: {e}")


def handle_rag_command(knowledge_base, use_rag: bool, user_input: str) -> bool:
    """Handle the /rag command to toggle or set RAG functionality."""
    from .display_utils import display_error_with_help
    
    parts = user_input.split()
    if len(parts) > 1:
        if parts[1].lower() == "on":
            use_rag = True
            print("\n🔍 RAG (Búsqueda en Base de Conocimiento)")
            print("   ✅ Estado: Activado")
        elif parts[1].lower() == "off":
            use_rag = False
            print("\n🔍 RAG (Búsqueda en Base de Conocimiento)")
            print("   ❌ Estado: Desactivado")
        else:
            display_error_with_help(
                "Comando inválido",
                "Uso correcto: /rag on|off",
                "Solo se permiten los valores 'on' u 'off'",
            )
    else:
        print("\n🔍 RAG (Búsqueda en Base de Conocimiento)")
        print(f"   {'✅ Estado: Activado' if use_rag else '❌ Estado: Desactivado'}")
    return use_rag


def handle_add_command(user_input, kb, memory):
    """Handle the /add command."""
    from .display_utils import display_section_header, display_success_error, display_error_with_help
    
    text_to_add = user_input[5:].strip()
    if text_to_add:
        try:
            # Validar texto antes de agregar
            from src.backend.utils.validators import validate_user_input
            text_to_add = validate_user_input(text_to_add)
            logger = _get_logger()
            logger.info(f"✅ Texto validado para agregar: {len(text_to_add)} caracteres")

            from datetime import datetime

            success_kb = False
            success_memory = False

            # Agregar a la base de conocimiento si está disponible
            if kb:
                success_kb = kb.add_document(
                    text_to_add, {"source": "user_input", "timestamp": str(datetime.now())}
                )

            # Agregar a memoria a largo plazo si está disponible
            if memory:
                memory.add_to_long_term(
                    content=text_to_add,
                    metadata={
                        "group": "user_added",
                        "category": "important_info",
                        "importance": "high",
                        "source": "manual_add",
                        "timestamp": str(datetime.now()),
                    },
                )
                success_memory = True

            # Mostrar resultado
            display_section_header("📝 Información Agregada", "─" * 30)

            if success_kb:
                display_success_error(True, "Base de Conocimiento", "Agregado")
            elif kb:
                display_success_error(False, "Base de Conocimiento", "Error")
            else:
                print("   ⚠️ Base de Conocimiento: No disponible")

            if success_memory:
                display_success_error(True, "Memoria a Largo Plazo", "Agregado")
            elif memory:
                display_success_error(False, "Memoria a Largo Plazo", "Error")
            else:
                print("   ⚠️ Memoria a Largo Plazo: No disponible")

            print(f"   📝 Contenido: {text_to_add[:60]}{'...' if len(text_to_add) > 60 else ''}")

            if not success_kb and not success_memory:
                print("   ⚠️ Advertencia: No se pudo guardar en ningún sistema")

        except Exception as e:
            display_error_with_help(
                "Error al agregar información",
                "Verifica que el texto sea válido y que los sistemas estén funcionando",
                str(e),
            )
    else:
        display_error_with_help("Texto requerido", "Uso correcto: /add <texto>")


def handle_list_short_command(memory):
    """Handle the /list_short command."""
    if memory:
        try:
            if hasattr(memory, 'history') and hasattr(memory.history, 'messages'):
                context_messages = list(memory.history.messages)
            else:
                context_messages = []
            
            if context_messages:
                print("\n📝 Mensajes en Contexto Actual")
                print("─" * 40)
                for i, msg in enumerate(context_messages, 1):
                    if hasattr(msg, 'content'):
                        content = msg.content[:60] + ("..." if len(msg.content) > 60 else "")
                        msg_type = "Usuario" if hasattr(msg, 'type') and msg.type == 'human' else "Asistente"
                        print(f"  {i}. [{msg_type}] {content}")
                    else:
                        print(f"  {i}. [Mensaje con formato incorrecto]")
                print()
            else:
                print("\n📝 Mensajes en Contexto: Vacío")
        except Exception as e:
            print(f"\n❌ Error al obtener mensajes: {e}")
    else:
        from .display_utils import display_component_unavailable_error
        display_component_unavailable_error(
            "Memoria", "Reinicia el sistema o verifica la configuración de memoria"
        )


def handle_list_long_command(memory):
    """Handle the /list_long command."""
    if memory:
        try:
            # Get all messages from history
            if hasattr(memory, 'history') and hasattr(memory.history, 'messages'):
                all_messages = list(memory.history.messages)
            else:
                all_messages = []
                
            if all_messages:
                print("\n🧠 Historial Completo de Mensajes")
                print("─" * 40)
                for i, msg in enumerate(all_messages, 1):
                    if hasattr(msg, 'content'):
                        content = msg.content[:80] + ("..." if len(msg.content) > 80 else "")
                        msg_type = "Usuario" if hasattr(msg, 'type') and msg.type == 'human' else "Asistente"
                        print(f"  {i}. [{msg_type}] {content}")
                    else:
                        print(f"  {i}. [Mensaje con formato incorrecto]")
            else:
                print("\n🧠 Historial de Mensajes: Vacío")
                
            # Also show summary if available
            if hasattr(memory, 'summary_text') and memory.summary_text:
                print("\n📋 Resumen de Sesión:")
                print("─" * 40)
                summary_preview = memory.summary_text[:200] + ("..." if len(memory.summary_text) > 200 else "")
                print(f"  {summary_preview}")
        except Exception as e:
            print(f"\n❌ Error al obtener historial: {e}")
    else:
        print("\n❌ Error: Memoria no disponible")


def handle_delete_command(user_input: str, memory, memory_type: str):
    """Generic handler for delete commands (LangChain memory)"""
    from .display_utils import display_component_unavailable_error, display_error_with_help, display_index_error
    
    if not memory:
        display_component_unavailable_error(
            "Memoria", "Reinicia el sistema o verifica la configuración de memoria"
        )
        return

    parts = user_input.split()
    if len(parts) < 2:
        display_error_with_help(
            "Índice requerido",
            f"Uso correcto: /delete_{memory_type} [número]",
            ("Debes especificar el número del mensaje a eliminar"),
        )
        return

    try:
        index = int(parts[1]) - 1
        
        # Handle LangChain MemoryService
        if hasattr(memory, 'get_messages') and hasattr(memory, 'clear'):
            messages = memory.get_messages()
            if 0 <= index < len(messages):
                # LangChain doesn't support individual message deletion easily
                # For now, we'll inform the user that full clear is available
                print(f"\n⚠️  El sistema de memoria LangChain no soporta eliminación individual")
                print("   💡 Usa /clear_memory para limpiar toda la memoria")
                return
            else:
                display_index_error(index, len(messages), f"/delete_{memory_type}")
                return
        
        # Fallback for legacy memory systems
        if hasattr(memory, 'short_term_memory') and hasattr(memory, 'long_term_memory'):
            memory_list = (
                memory.short_term_memory if memory_type == "short" else memory.long_term_memory
            )

            if 0 <= index < len(memory_list):
                deleted = memory_list.pop(index)
                if hasattr(memory, 'save_memory'):
                    memory.save_memory()

                term_name = "corto" if memory_type == "short" else "largo"
                item_name = "Interacción" if memory_type == "short" else "Memoria"
                content_key = "user_message" if memory_type == "short" else "content"

                print(f"\n✅ {item_name} {index + 1} eliminada de memoria a {term_name} plazo")
                content_preview = deleted.get(content_key, "")[:50]
                print(
                    "   📝 Contenido: {}{}".format(
                        content_preview,
                        "..." if len(deleted.get(content_key, "")) > 50 else "",
                    )
                )
            else:
                display_index_error(index, len(memory_list), f"/delete_{memory_type}")
        else:
            print(f"\n⚠️  Función de eliminación no disponible para este tipo de memoria")
            
    except (ValueError, IndexError):
        display_error_with_help(
            "Índice inválido",
            f"Uso correcto: /delete_{memory_type} [número]",
            "El índice debe ser un número entero válido",
        )
