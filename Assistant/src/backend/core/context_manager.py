"""
Context and memory management for the assistant application.
"""

import json
from pathlib import Path
from typing import Optional

def _get_config():
    """Lazy import of config to avoid circular imports"""
    from src.backend.utils.unified_config import get_config
    return get_config()

def _get_logger():
    """Lazy import of logger to avoid circular imports"""
    from src.backend.utils.unified_logger import get_unified_logger
    return get_unified_logger("ContextManager")


def retrieve_memory_context(memory, user_input: str) -> str:
    """Retrieve and combine memory context from LangChain MemoryService."""
    if not memory or not user_input:
        return ""

    logger = _get_logger()
    with logger.operation("memory_retrieval"):
        try:
            # Use LangChain MemoryService to get conversation history
            if hasattr(memory, 'get_messages'):
                # Get recent messages from LangChain memory
                messages = memory.get_messages()
                if messages:
                    memory_context = "\n\nConversación reciente:\n"
                    for msg in messages[-6:]:  # Get last 6 messages
                        role = "Usuario" if msg.type == "human" else "Asistente"
                        memory_context += f"{role}: {msg.content}\n"
                    
                    logger.info(
                        f"🧠 Contexto de memoria recuperado: {len(memory_context)} caracteres",
                        memory_context_length=len(memory_context),
                        message_count=len(messages[-6:]),
                    )
                    return memory_context
            else:
                # Fallback for legacy memory systems
                recent_context = memory.get_recent_context(max_items=6) if hasattr(memory, 'get_recent_context') else []
                relevant_memories = memory.get_relevant_memory_contents(user_input, max_items=3) if hasattr(memory, 'get_relevant_memory_contents') else []

                all_memory = []
                if recent_context:
                    all_memory.extend([f"Conversación reciente:\n{ctx}" for ctx in recent_context])
                if relevant_memories:
                    all_memory.extend([f"Memoria relevante:\n{mem}" for mem in relevant_memories])

                if all_memory:
                    memory_context = "\n\n" + "\n---\n".join(all_memory)
                    logger.info(
                        f"🧠 Contexto de memoria recuperado: {len(memory_context)} caracteres",
                        memory_context_length=len(memory_context),
                        recent_items=len(recent_context),
                        relevant_items=len(relevant_memories),
                    )
                    return memory_context

        except Exception as e:
            logger.error(
                f"❌ Error al recuperar memoria: {e}", error_type="memory_retrieval", exc_info=True
            )

    return ""


def retrieve_knowledge_base_context(kb, user_input: str, use_rag: bool) -> tuple[str, bool]:
    """Retrieve context from knowledge base if RAG is enabled.

    Returns:
        tuple: (kb_context, updated_use_rag_flag)
    """
    if not use_rag or not kb or not user_input:
        return "", use_rag

    logger = _get_logger()
    with logger.operation("knowledge_base_query"):
        try:
            kb_results = kb.query(user_input, top_k=2)
            if kb_results:
                kb_context = "\n\nInformación de la base de conocimiento:\n" + "\n---\n".join(
                    [r["content"] for r in kb_results]
                )
                logger.info(
                    f"📚 Contexto de KB recuperado: {len(kb_context)} caracteres",
                    kb_context_length=len(kb_context),
                    kb_results_count=len(kb_results),
                )
                return kb_context, use_rag
        except Exception as e:
            logger.error(
                f"❌ Error al recuperar contexto de KB: {e}",
                error_type="knowledge_base_query",
                exc_info=True,
            )
            print(
                (
                    "⚠️ No se pudo recuperar contexto de la base de conocimiento. "
                    "RAG desactivado para esta consulta."
                )
            )
            return "", False

    return "", use_rag


def get_user_profile_context(session_id: str = None) -> str:
    """Get user profile information to include in context.
    
    Args:
        session_id: Session ID to identify the user
        
    Returns:
        Formatted user profile context string
    """
    if not session_id or session_id in ["default", "default_session"]:
        return ""
    
    try:
        # Extract user name from session_id (format: user_name)
        if session_id.startswith("user_"):
            user_name = session_id[5:]  # Remove "user_" prefix
        else:
            user_name = session_id
        
        # Look for user profile file
        # Check both possible locations
        profile_paths = [
            Path(f"models/memory/users/{user_name}_user.json"),
            Path(f"Assistant/models/memory/users/{user_name}_user.json")
        ]
        
        for profile_path in profile_paths:
            if profile_path.exists():
                with open(profile_path, 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                
                profile = user_data.get("profile", {})
                if not profile:
                    continue
                
                # Format user profile information
                profile_parts = []
                
                name = profile.get("name", "")
                if name:
                    profile_parts.append(f"Usuario: {name}")
                
                career = profile.get("career", "")
                if career:
                    profile_parts.append(f"Carrera: {career}")
                
                semester = profile.get("semester", "")
                if semester:
                    profile_parts.append(f"Semestre: {semester}")
                
                interests = profile.get("interests", [])
                if interests:
                    profile_parts.append(f"Intereses: {', '.join(interests)}")
                
                comm_pref = profile.get("communication_preference", "")
                if comm_pref:
                    profile_parts.append(f"Estilo de comunicación preferido: {comm_pref}")
                
                lang = profile.get("preferred_language", "")
                if lang:
                    profile_parts.append(f"Idioma preferido: {lang}")
                
                # Agregar información personal adicional
                favorite_color = profile.get("favorite_color", "")
                if favorite_color:
                    profile_parts.append(f"Color favorito: {favorite_color}")
                
                favorite_food = profile.get("favorite_food", "")
                if favorite_food:
                    profile_parts.append(f"Comida favorita: {favorite_food}")
                
                age = profile.get("age", "")
                if age:
                    profile_parts.append(f"Edad: {age} años")
                
                profession = profile.get("profession", "")
                if profession:
                    profile_parts.append(f"Profesión: {profession}")
                
                location = profile.get("location", "")
                if location:
                    profile_parts.append(f"Ubicación: {location}")
                
                hobbies = profile.get("hobbies", [])
                if hobbies:
                    hobbies_str = ", ".join(hobbies) if isinstance(hobbies, list) else hobbies
                    profile_parts.append(f"Hobbies: {hobbies_str}")
                
                if profile_parts:
                    return f"PERFIL DEL USUARIO:\n{chr(10).join(profile_parts)}\n"
                
                break
        
        return ""
        
    except Exception as e:
        logger = _get_logger()
        logger.debug(f"No se pudo obtener perfil del usuario: {e}")
        return ""


def combine_and_limit_context(
    memory_context: str,
    kb_context: str,
    text_context: Optional[str] = None,
    max_length: int = 6000,
    session_id: Optional[str] = None,
) -> str:
    """Enhanced context combination with intelligent prioritization and truncation.

    Args:
        memory_context: Context from memory (conversation history)
        kb_context: Context from knowledge base (RAG)
        text_context: Additional text-based context (files, notes, etc.)
        max_length: Maximum allowed context length
        session_id: Session ID to get user profile information

    Returns:
        Combined and intelligently truncated context with user profile
    """
    # Get user profile context
    profile_context = get_user_profile_context(session_id)
    logger = _get_logger()

    # Normalize inputs
    memory_context = memory_context or ""
    kb_context = kb_context or ""
    text_context = text_context or ""

    # Enhanced context combination with smart prioritization
    if not memory_context and not kb_context and not text_context and not profile_context:
        return ""

    # Calculate available space after profile context
    profile_length = len(profile_context)
    available_length = max_length - profile_length - 30  # Reserve space for separators

    # If only profile context exists
    if profile_context and not memory_context and not kb_context and not text_context:
        return profile_context.strip()

    # Single-source contexts (plus optional profile)
    if memory_context and not kb_context and not text_context:
        context = memory_context
        if len(context) > available_length:
            logger.warning(
                f"⚠️ Contexto de memoria truncado de {len(context)} a {available_length} caracteres",
                original_length=len(context),
                truncated_length=available_length,
            )
            # Keep the end of memory context (most recent conversation)
            context = "...(conversación anterior truncada)\n" + context[-(available_length - 50):]

        final_context = f"{profile_context}{context}" if profile_context else context
        return final_context

    if kb_context and not memory_context and not text_context:
        context = kb_context
        if len(context) > available_length:
            logger.warning(
                f"⚠️ Contexto de KB truncado de {len(context)} a {available_length} caracteres",
                original_length=len(context),
                truncated_length=available_length,
            )
            context = context[: available_length - 20] + "...(información truncada)"

        final_context = f"{profile_context}{context}" if profile_context else context
        return final_context

    if text_context and not memory_context and not kb_context:
        context = text_context
        if len(context) > available_length:
            logger.warning(
                f"⚠️ Contexto TXT truncado de {len(context)} a {available_length} caracteres",
                original_length=len(context),
                truncated_length=available_length,
            )
            context = context[: available_length - 20] + "...(texto truncado)"
        # Keep label for clarity
        labeled = f"INFORMACIÓN ADICIONAL:\n{context}"
        final_context = f"{profile_context}{labeled}" if profile_context else labeled
        return final_context

    # Two-source combinations
    if memory_context and kb_context and not text_context:
        total_content_length = len(memory_context) + len(kb_context)
        if total_content_length <= available_length:
            context = f"{memory_context}\n\n{kb_context}"
        else:
            memory_priority_ratio = 0.7  # 70% memory, 30% KB
            max_memory_length = int(available_length * memory_priority_ratio)
            max_kb_length = available_length - max_memory_length - 10

            if len(memory_context) > max_memory_length:
                truncated_memory = "...(conversación anterior truncada)\n" + memory_context[-(max_memory_length - 50):]
            else:
                truncated_memory = memory_context

            if len(kb_context) > max_kb_length:
                truncated_kb = kb_context[: max_kb_length - 20] + "...(información truncada)"
            else:
                truncated_kb = kb_context

            context = f"{truncated_memory}\n\n{truncated_kb}"
            logger.warning(
                f"⚠️ Contexto combinado truncado de {total_content_length} a {len(context)} caracteres",
                original_memory_length=len(memory_context),
                original_kb_length=len(kb_context),
                final_length=len(context),
                memory_priority_ratio=memory_priority_ratio,
            )
        final_context = f"{profile_context}{context}" if profile_context else context
        logger.info(
            f"📚 Contexto total preparado: {len(final_context)} caracteres",
            total_context_length=len(final_context),
            has_profile=bool(profile_context),
            has_memory=bool(memory_context),
            has_kb=bool(kb_context),
            has_text=False,
            memory_length=len(memory_context) if memory_context else 0,
            kb_length=len(kb_context) if kb_context else 0,
            text_length=0,
        )
        return final_context

    # memory + text only
    if memory_context and text_context and not kb_context:
        total_content_length = len(memory_context) + len(text_context)
        if total_content_length <= available_length:
            labeled_text = f"INFORMACIÓN ADICIONAL:\n{text_context}"
            context = f"{memory_context}\n\n{labeled_text}"
        else:
            memory_priority_ratio = 0.7  # prioritize conversation
            max_memory_length = int(available_length * memory_priority_ratio)
            max_text_length = available_length - max_memory_length - 10

            if len(memory_context) > max_memory_length:
                truncated_memory = "...(conversación anterior truncada)\n" + memory_context[-(max_memory_length - 50):]
            else:
                truncated_memory = memory_context

            if len(text_context) > max_text_length:
                truncated_text = text_context[: max_text_length - 20] + "...(texto truncado)"
            else:
                truncated_text = text_context

            labeled_text = f"INFORMACIÓN ADICIONAL:\n{truncated_text}"
            context = f"{truncated_memory}\n\n{labeled_text}"

        final_context = f"{profile_context}{context}" if profile_context else context
        logger.info(
            f"📚 Contexto total preparado: {len(final_context)} caracteres",
            total_context_length=len(final_context),
            has_profile=bool(profile_context),
            has_memory=bool(memory_context),
            has_kb=False,
            has_text=True,
            memory_length=len(memory_context) if memory_context else 0,
            kb_length=0,
            text_length=len(text_context) if text_context else 0,
        )
        return final_context

    # kb + text only
    if kb_context and text_context and not memory_context:
        total_content_length = len(kb_context) + len(text_context)
        if total_content_length <= available_length:
            labeled_text = f"INFORMACIÓN ADICIONAL:\n{text_context}"
            context = f"{kb_context}\n\n{labeled_text}"
        else:
            kb_ratio = 0.6
            max_kb_length = int(available_length * kb_ratio)
            max_text_length = available_length - max_kb_length - 10

            if len(kb_context) > max_kb_length:
                truncated_kb = kb_context[: max_kb_length - 20] + "...(información truncada)"
            else:
                truncated_kb = kb_context

            if len(text_context) > max_text_length:
                truncated_text = text_context[: max_text_length - 20] + "...(texto truncado)"
            else:
                truncated_text = text_context

            labeled_text = f"INFORMACIÓN ADICIONAL:\n{truncated_text}"
            context = f"{truncated_kb}\n\n{labeled_text}"

        final_context = f"{profile_context}{context}" if profile_context else context
        logger.info(
            f"📚 Contexto total preparado: {len(final_context)} caracteres",
            total_context_length=len(final_context),
            has_profile=bool(profile_context),
            has_memory=False,
            has_kb=True,
            has_text=True,
            memory_length=0,
            kb_length=len(kb_context) if kb_context else 0,
            text_length=len(text_context) if text_context else 0,
        )
        return final_context

    # All three contexts exist: memory + kb + text
    total_content_length = len(memory_context) + len(kb_context) + len(text_context)
    if total_content_length <= available_length:
        labeled_text = f"INFORMACIÓN ADICIONAL:\n{text_context}"
        context = f"{memory_context}\n\n{kb_context}\n\n{labeled_text}"
    else:
        # Intelligent split: prioritize recent conversation
        memory_ratio = 0.6
        kb_ratio = 0.25
        text_ratio = 0.15
        max_memory_length = int(available_length * memory_ratio)
        max_kb_length = int(available_length * kb_ratio)
        max_text_length = available_length - max_memory_length - max_kb_length - 10

        if len(memory_context) > max_memory_length:
            truncated_memory = "...(conversación anterior truncada)\n" + memory_context[-(max_memory_length - 50):]
        else:
            truncated_memory = memory_context

        if len(kb_context) > max_kb_length:
            truncated_kb = kb_context[: max_kb_length - 20] + "...(información truncada)"
        else:
            truncated_kb = kb_context

        if len(text_context) > max_text_length:
            truncated_text = text_context[: max_text_length - 20] + "...(texto truncado)"
        else:
            truncated_text = text_context

        labeled_text = f"INFORMACIÓN ADICIONAL:\n{truncated_text}"
        context = f"{truncated_memory}\n\n{truncated_kb}\n\n{labeled_text}"

        logger.warning(
            f"⚠️ Contexto triple truncado de {total_content_length} a {len(context)} caracteres",
            original_memory_length=len(memory_context),
            original_kb_length=len(kb_context),
            original_text_length=len(text_context),
            final_length=len(context),
            memory_ratio=memory_ratio,
            kb_ratio=kb_ratio,
            text_ratio=text_ratio,
        )

    final_context = f"{profile_context}{context}" if profile_context else context

    logger.info(
        f"📚 Contexto total preparado: {len(final_context)} caracteres",
        total_context_length=len(final_context),
        has_profile=bool(profile_context),
        has_memory=bool(memory_context),
        has_kb=bool(kb_context),
        has_text=bool(text_context),
        memory_length=len(memory_context) if memory_context else 0,
        kb_length=len(kb_context) if kb_context else 0,
        text_length=len(text_context) if text_context else 0,
    )

    return final_context

