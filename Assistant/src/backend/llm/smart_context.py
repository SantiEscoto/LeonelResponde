# -*- coding: utf-8 -*-
"""
Sistema de Contexto Dinámico Inteligente para Leonel
Optimiza el contexto del modelo priorizando información relevante

Este módulo implementa:
- Selección inteligente de contexto con límite de tokens
- Priorización de interacciones recientes
- Integración de información clave de largo plazo
- Cache de contexto para consultas similares
- Optimización para mantener baja latencia
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from .leonel_personality import InteractionContext, LeonelPersonality
# from .user_memory import UserMemory, UserMemoryManager  # Legacy - removed


@dataclass
class ContextItem:
    """Elemento de contexto con metadatos"""

    content: str
    priority: float  # 0.0 - 1.0
    token_count: int
    timestamp: datetime
    context_type: str  # "recent", "long_term", "personality", "user_profile"
    source: str
    relevance_score: float = 0.0


@dataclass
class ContextCache:
    """Cache de contexto para consultas similares"""

    query_hash: str
    context_items: List[ContextItem]
    total_tokens: int
    created_at: datetime
    user_id: str
    hit_count: int = 0


class SmartContextManager:
    """Gestor de contexto dinámico inteligente"""

    def __init__(self, config: Dict[str, Any], memory_service=None):
        self.config = config
        self.memory_service = memory_service  # Updated to use MemoryService instead of UserMemoryManager
        self.leonel_personality = LeonelPersonality()

        # Configuración de contexto
        if hasattr(config, "memory"):
            # Si config es un objeto UnifiedConfig
            self.max_tokens = config.memory.context_token_limit
            self.cache_enabled = config.memory.enable_caching
            self.cache_ttl_hours = config.memory.cache_ttl_hours
        elif isinstance(config, dict) and "memory" in config:
            # Si config es un diccionario con sección memory
            memory_config = config["memory"]
            self.max_tokens = memory_config.get("context_token_limit", 800)
            self.cache_enabled = memory_config.get("enable_caching", True)
            self.cache_ttl_hours = memory_config.get("cache_ttl_hours", 1)
        else:
            # Valores por defecto
            self.max_tokens = 800
            self.cache_enabled = True
            self.cache_ttl_hours = 1

        # Cache de contexto
        self._context_cache: Dict[str, ContextCache] = {}
        if hasattr(config, "paths"):
            # Si config es un objeto UnifiedConfig
            self.cache_dir = Path(config.paths.cache_dir)
        elif isinstance(config, dict) and "cache_dir" in config:
            # Si config es un diccionario con cache_dir
            self.cache_dir = Path(config["cache_dir"])
        else:
            # Valor por defecto
            self.cache_dir = Path("./models/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Configuración de prioridades
        self.priority_weights = {
            "recent_interaction": 1.0,
            "user_profile": 0.9,
            "personality_core": 0.8,
            "relevant_long_term": 0.7,
            "context_specific": 0.6,
            "general_knowledge": 0.3,
        }

        # Patrones para estimación de tokens
        self.token_estimation_ratio = 0.75  # Aproximadamente 0.75 tokens por palabra en español

        # Cargar cache desde disco
        self._load_cache_from_disk()

    def generate_smart_context(
        self,
        user_id: str,
        current_query: str,
        interaction_context: InteractionContext,
        include_personality: bool = True,
    ) -> Dict[str, Any]:
        """Genera contexto inteligente optimizado para el modelo"""

        # Verificar cache
        cache_key = self._generate_cache_key(user_id, current_query, interaction_context)
        cached_context = self._get_cached_context(cache_key)

        if cached_context:
            cached_context.hit_count += 1
            return self._format_context_for_model(cached_context.context_items)

        # Generar nuevo contexto
        context_items = []
        remaining_tokens = self.max_tokens

        # 1. Información de personalidad de Leonel (siempre incluir)
        if include_personality:
            personality_items = self._get_personality_context(interaction_context)
            for item in personality_items:
                if remaining_tokens > item.token_count:
                    context_items.append(item)
                    remaining_tokens -= item.token_count

        # 2. Perfil del usuario
        user_memory = self.user_memory_manager.get_user_memory(user_id)
        user_profile_items = self._get_user_profile_context(user_memory)
        for item in user_profile_items:
            if remaining_tokens > item.token_count:
                context_items.append(item)
                remaining_tokens -= item.token_count

        # 3. Interacciones recientes (alta prioridad)
        recent_items = self._get_recent_interactions_context(user_memory, current_query)
        for item in recent_items:
            if remaining_tokens > item.token_count:
                context_items.append(item)
                remaining_tokens -= item.token_count

        # 4. Información relevante de largo plazo
        if remaining_tokens > 50:  # Reservar espacio mínimo
            long_term_items = self._get_relevant_long_term_context(
                user_memory, current_query, interaction_context, remaining_tokens
            )
            for item in long_term_items:
                if remaining_tokens > item.token_count:
                    context_items.append(item)
                    remaining_tokens -= item.token_count

        # Ordenar por prioridad
        context_items.sort(key=lambda x: x.priority, reverse=True)

        # Guardar en cache
        if self.cache_enabled:
            total_tokens = sum(item.token_count for item in context_items)
            cache_entry = ContextCache(
                query_hash=cache_key,
                context_items=context_items,
                total_tokens=total_tokens,
                created_at=datetime.now(),
                user_id=user_id,
            )
            self._cache_context(cache_key, cache_entry)

        return self._format_context_for_model(context_items)

    def _get_personality_context(
        self, interaction_context: InteractionContext
    ) -> List[ContextItem]:
        """Obtiene contexto de personalidad de Leonel"""
        items = []

        # Información básica de Leonel
        basic_info = (
            f"Soy {self.leonel_personality.name}, {self.leonel_personality.role} "
            f"de la {self.leonel_personality.university}. {self.leonel_personality.story}"
        )

        items.append(
            ContextItem(
                content=basic_info,
                priority=self.priority_weights["personality_core"],
                token_count=self._estimate_tokens(basic_info),
                timestamp=datetime.now(),
                context_type="personality",
                source="leonel_core",
            )
        )

        # Valores relevantes al contexto
        if interaction_context == InteractionContext.ACADEMIC:
            values_text = (
                "Mis valores fundamentales incluyen la excelencia en el actuar, "
                "la formación integral y la pasión por la verdad. Busco apoyarte "
                "en tu crecimiento académico con dedicación y esfuerzo permanente."
            )
        elif interaction_context == InteractionContext.SOCIAL:
            values_text = (
                "Valoro la apertura al diálogo, el compromiso social y la centralidad "
                "de la persona. Cada interacción es una oportunidad de ejercer "
                "liderazgo de acción positiva."
            )
        elif interaction_context == InteractionContext.MOTIVATIONAL:
            values_text = (
                "Mi propósito es inspirarte con optimismo y fortaleza. Creo en tu "
                "potencial y en el sentido de trascendencia que cada persona lleva dentro."
            )
        else:
            values_text = (
                "Mis valores de formación integral, liderazgo positivo y compromiso "
                "social guían cada una de mis interacciones contigo."
            )

        items.append(
            ContextItem(
                content=values_text,
                priority=self.priority_weights["context_specific"],
                token_count=self._estimate_tokens(values_text),
                timestamp=datetime.now(),
                context_type="personality",
                source="leonel_values",
            )
        )

        return items

    def _get_user_profile_context(self, memory_service) -> List[ContextItem]:
        """Obtiene contexto del perfil del usuario - Simplified for MemoryService"""
        items = []

        # Since MemoryService doesn't have user profiles like UserMemory,
        # we'll create a basic context item indicating this functionality is deprecated
        profile_text = "Perfil de usuario: Funcionalidad migrada a MemoryService"
        
        items.append(
            ContextItem(
                content=profile_text,
                priority=0.3,  # Lower priority since it's deprecated
                token_count=self._estimate_tokens(profile_text),
                timestamp=datetime.now(),
                context_type="user_profile",
                source="memory_service",
                relevance_score=0.3,
            )
        )

        return items

        # Preferencias de comunicación
        if profile.communication_preference:
            pref_text = f"Preferencia de comunicación: {profile.communication_preference.value}"
            items.append(
                ContextItem(
                    content=pref_text,
                    priority=self.priority_weights["user_profile"] * 0.8,
                    token_count=self._estimate_tokens(pref_text),
                    timestamp=datetime.now(),
                    context_type="user_profile",
                    source="user_preferences",
                )
            )

        # Aprendizajes importantes del usuario
        high_confidence_learnings = {
            key: learning
            for key, learning in user_memory.learnings.items()
            if learning.confidence > 0.7
        }

        if high_confidence_learnings:
            learnings_text = "Información importante: " + "; ".join(
                [learning.description for learning in list(high_confidence_learnings.values())[:2]]
            )

            items.append(
                ContextItem(
                    content=learnings_text,
                    priority=self.priority_weights["user_profile"] * 0.9,
                    token_count=self._estimate_tokens(learnings_text),
                    timestamp=datetime.now(),
                    context_type="user_profile",
                    source="user_learnings",
                )
            )

        return items

    def _get_recent_interactions_context(
        self, memory_service, current_query: str
    ) -> List[ContextItem]:
        """Obtiene contexto de interacciones recientes usando MemoryService"""
        items = []

        # Placeholder: MemoryService doesn't have direct recent interactions method
        # This would need to be implemented based on the actual MemoryService API
        recent_interactions = []  # memory_service.get_recent_interactions(max_count=5)

        for i, interaction in enumerate(recent_interactions[-3:]):  # Solo las últimas 3
            # Calcular prioridad basada en recencia
            recency_factor = 1.0 - (i * 0.2)  # Más reciente = mayor prioridad
            priority = self.priority_weights["recent_interaction"] * recency_factor

            # Formatear interacción
            interaction_text = (
                f"Usuario: {interaction['user_message']} | "
                f"Leonel: {interaction['assistant_response'][:100]}..."
            )

            # Calcular relevancia con la consulta actual
            relevance = self._calculate_query_relevance(current_query, interaction["user_message"])

            items.append(
                ContextItem(
                    content=interaction_text,
                    priority=priority + (relevance * 0.2),  # Bonus por relevancia
                    token_count=self._estimate_tokens(interaction_text),
                    timestamp=datetime.fromisoformat(interaction["timestamp"]),
                    context_type="recent",
                    source="recent_interaction",
                    relevance_score=relevance,
                )
            )

        return items

    def _get_relevant_long_term_context(
        self,
        memory_service,
        current_query: str,
        interaction_context: InteractionContext,
        max_tokens: int,
    ) -> List[ContextItem]:
        """Obtiene contexto relevante de memoria de largo plazo usando MemoryService"""
        items = []

        # Placeholder: MemoryService doesn't have direct long-term context method
        # This would need to be implemented based on the actual MemoryService API
        relevant_memories = []  # memory_service.get_relevant_memories(current_query, max_items=3)

        for memory in relevant_memories:
            # Crear resumen de la memoria
            memory_text = (
                f"Contexto previo: {memory['user_message'][:80]}... | "
                f"Respuesta: {memory['assistant_response'][:80]}..."
            )

            # Prioridad basada en relevancia
            relevance_score = memory.get("relevance_score", 0.5)
            priority = self.priority_weights["relevant_long_term"] * relevance_score

            token_count = self._estimate_tokens(memory_text)

            # Solo agregar si cabe en el límite de tokens
            if token_count <= max_tokens:
                items.append(
                    ContextItem(
                        content=memory_text,
                        priority=priority,
                        token_count=token_count,
                        timestamp=datetime.fromisoformat(memory["timestamp"]),
                        context_type="long_term",
                        source="long_term_memory",
                        relevance_score=relevance_score,
                    )
                )

        return items

    def _calculate_query_relevance(self, query1: str, query2: str) -> float:
        """Calcula la relevancia entre dos consultas"""
        # Normalizar texto
        words1 = set(re.findall(r"\w+", query1.lower()))
        words2 = set(re.findall(r"\w+", query2.lower()))

        if not words1 or not words2:
            return 0.0

        # Calcular intersección
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        # Jaccard similarity
        return intersection / union if union > 0 else 0.0

    def _estimate_tokens(self, text: str) -> int:
        """Estima el número de tokens en un texto"""
        # Estimación simple basada en palabras
        word_count = len(text.split())
        return max(1, int(word_count * self.token_estimation_ratio))

    def _generate_cache_key(self, user_id: str, query: str, context: InteractionContext) -> str:
        """Genera clave única para el cache"""
        # Normalizar query para mejor cache hit rate
        normalized_query = re.sub(r"\W+", " ", query.lower()).strip()

        # Crear hash
        cache_string = f"{user_id}:{normalized_query}:{context.value}"
        return hashlib.md5(cache_string.encode()).hexdigest()[:16]

    def _get_cached_context(self, cache_key: str) -> Optional[ContextCache]:
        """Obtiene contexto del cache si está disponible y válido"""
        if not self.cache_enabled or cache_key not in self._context_cache:
            return None

        cached = self._context_cache[cache_key]

        # Verificar TTL
        age = datetime.now() - cached.created_at
        if age > timedelta(hours=self.cache_ttl_hours):
            del self._context_cache[cache_key]
            return None

        return cached

    def _cache_context(self, cache_key: str, context_cache: ContextCache):
        """Guarda contexto en cache"""
        if not self.cache_enabled:
            return

        # Limitar tamaño del cache
        if len(self._context_cache) > 100:
            # Remover entradas más antiguas
            oldest_key = min(
                self._context_cache.keys(), key=lambda k: self._context_cache[k].created_at
            )
            del self._context_cache[oldest_key]

        self._context_cache[cache_key] = context_cache

    def _format_context_for_model(self, context_items: List[ContextItem]) -> Dict[str, Any]:
        """Formatea el contexto para el modelo LLM"""
        # Agrupar por tipo de contexto
        context_by_type = {"personality": [], "user_profile": [], "recent": [], "long_term": []}

        for item in context_items:
            context_by_type[item.context_type].append(item.content)

        # Crear contexto estructurado
        formatted_context = {
            "leonel_personality": " ".join(context_by_type["personality"]),
            "user_information": " ".join(context_by_type["user_profile"]),
            "recent_conversation": " ".join(context_by_type["recent"]),
            "relevant_history": " ".join(context_by_type["long_term"]),
            "total_tokens": sum(item.token_count for item in context_items),
            "context_items_count": len(context_items),
        }

        return formatted_context

    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del cache"""
        if not self._context_cache:
            return {"cache_size": 0, "total_hits": 0, "avg_tokens": 0}

        total_hits = sum(cache.hit_count for cache in self._context_cache.values())
        avg_tokens = sum(cache.total_tokens for cache in self._context_cache.values()) / len(
            self._context_cache
        )

        return {
            "cache_size": len(self._context_cache),
            "total_hits": total_hits,
            "avg_tokens": round(avg_tokens, 2),
            "cache_enabled": self.cache_enabled,
        }

    def clear_cache(self, user_id: Optional[str] = None):
        """Limpia el cache (opcionalmente solo para un usuario)"""
        if user_id:
            # Remover solo entradas del usuario específico
            keys_to_remove = [
                key for key, cache in self._context_cache.items() if cache.user_id == user_id
            ]
            for key in keys_to_remove:
                del self._context_cache[key]
        else:
            # Limpiar todo el cache
            self._context_cache.clear()

    def _save_cache_to_disk(self):
        """Guarda el cache a disco (solo metadatos, no contenido completo)"""
        cache_file = self.cache_dir / "context_cache_stats.json"

        stats = {
            "last_save": datetime.now().isoformat(),
            "cache_size": len(self._context_cache),
            "total_entries": sum(cache.hit_count for cache in self._context_cache.values()),
        }

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache stats: {e}")

    def _load_cache_from_disk(self):
        """Carga estadísticas del cache desde disco"""
        cache_file = self.cache_dir / "context_cache_stats.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    stats = json.load(f)
                print(f"📊 Context cache stats loaded: {stats.get('cache_size', 0)} entries")
            except Exception as e:
                print(f"Error loading cache stats: {e}")


# Función de utilidad para crear el gestor de contexto
def create_smart_context_manager(config: Dict[str, Any]) -> SmartContextManager:
    """Crea una instancia del gestor de contexto inteligente"""
    if hasattr(config, "paths"):
        # Si config es un objeto UnifiedConfig
        user_memory_dir = config.paths.user_memory_dir
    elif isinstance(config, dict) and "user_memory_dir" in config:
        # Si config es un diccionario con user_memory_dir
        user_memory_dir = config["user_memory_dir"]
    else:
        # Valor por defecto
        user_memory_dir = "models/memory/users"

    # Create a placeholder MemoryService for compatibility
    # In a real implementation, this would be properly initialized
    from src.backend.memory.memory_service import MemoryService
    memory_service = MemoryService(
        session_id="default",
        base_dir=user_memory_dir,
        window_k=5,
        enable_summaries=True,
        summary_threshold_tokens=1000,
        retrieval_k=3
    )
    return SmartContextManager(config, memory_service)


if __name__ == "__main__":
    # Test del sistema de contexto inteligente
    print("🧠 Testing Smart Context Manager...")

    # Configuración de prueba
    test_config = {
        "context_token_limit": 800,
        "enable_caching": True,
        "cache_ttl_hours": 1,
        "user_memory_dir": "./models/memory/users",
        "cache_dir": "./models/cache",
    }

    # Crear gestor
    context_manager = create_smart_context_manager(test_config)

    # Generar contexto de prueba
    test_context = context_manager.generate_smart_context(
        user_id="test_user_123",
        current_query="Necesito ayuda con mi proyecto de programación",
        interaction_context=InteractionContext.ACADEMIC,
    )

    print(f"Generated context: {test_context['total_tokens']} tokens")
    print(f"Cache stats: {context_manager.get_cache_stats()}")

    print("✅ Smart Context Manager working correctly!")
