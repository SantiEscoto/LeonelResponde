# -*- coding: utf-8 -*-
"""
Generador de Respuestas de Leonel
Integra personalidad, memoria y contexto inteligente

Este módulo:
- Genera respuestas con la personalidad de Leonel
- Utiliza contexto inteligente para respuestas relevantes
- Mantiene coherencia conversacional
- Optimiza para baja latencia
- Compatible con TTS/STT
"""

from dataclasses import dataclass
from functools import lru_cache
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# from .consolidated_memory_manager import ConsolidatedMemoryManager  # Legacy - removed
from src.backend.memory.memory_service import MemoryService
from .leonel_personality import InteractionContext


@dataclass
class ResponseContext:
    """Contexto para generar respuesta"""

    user_message: str
    user_id: str
    interaction_context: InteractionContext
    user_name: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = None
    urgency_level: str = "normal"  # "low", "normal", "high"
    requires_empathy: bool = False
    topic_category: Optional[str] = None


@dataclass
class LeonelResponse:
    """Respuesta generada por Leonel"""

    content: str
    personality_applied: bool
    context_tokens_used: int
    response_time_ms: float
    interaction_context: InteractionContext
    values_reflected: List[str]
    user_personalization: Dict[str, Any]


class LeonelResponseGenerator:
    """
    Generador de respuestas con personalidad de Leonel integrada
    Optimizado para bajo consumo de CPU y alta eficiencia
    """

    def __init__(self, memory_service: MemoryService):
        """
        Inicializa el generador de respuestas

        Args:
            memory_service: Servicio de memoria usando LangChain
        """
        self.memory_service = memory_service
        # Initialize personality directly since memory_service doesn't have it
        from .leonel_personality import LeonelPersonality
        self.leonel_personality = LeonelPersonality()

        # Cache para respuestas frecuentes y componentes
        self._response_cache = {}
        self._component_cache = {}
        self._cache_lock = threading.Lock()
        self._cache_max_size = 100

        # Pre-compilar expresiones regulares para mejor rendimiento
        self._compiled_patterns = {
            "help_words": re.compile(r"\b(ayuda|apoyo|necesito)\b", re.IGNORECASE),
            "thanks_words": re.compile(r"\b(gracias|agradezco)\b", re.IGNORECASE),
            "problem_words": re.compile(r"\b(problema|dificultad|complicado)\b", re.IGNORECASE),
            "project_words": re.compile(r"\b(proyecto|tarea|trabajo)\b", re.IGNORECASE),
            "exam_words": re.compile(r"\b(examen|evaluación|prueba)\b", re.IGNORECASE),
        }

        # Plantillas de respuesta por contexto
        self.response_templates = {
            InteractionContext.GENERAL: [
                "¡{greeting}! Me da mucho gusto {emotion}. {personality_intro}",
                "{greeting} {user_name}! {motivational_phrase} {support_offer}",
                "¡Hola {user_name}! {leonel_intro} {context_specific}",
            ],
            InteractionContext.ACADEMIC: [
                (
                    "{user_name}, como {leonel_role}, estoy aquí para apoyarte en {topic}. "
                    "{academic_values}"
                ),
                (
                    "Excelente pregunta sobre {topic}, {user_name}. "
                    "{academic_support} {excellence_value}"
                ),
                "{academic_greeting} {topic_response} {growth_encouragement}",
            ],
            InteractionContext.MOTIVATIONAL: [
                "{user_name}, {motivational_phrase} {strength_reminder} {transcendence_value}",
                "{empathy_response} {motivational_core} {positive_leadership}",
                "{user_name}, recuerda que {personal_strength} {university_values}",
            ],
            InteractionContext.SOCIAL: [
                "{social_greeting} {dialogue_value} {community_connection}",
                "{user_name}, {social_engagement} {person_centricity} {social_commitment}",
                "{friendly_approach} {social_values} {relationship_building}",
            ],
            InteractionContext.ACADEMIC: [
                "{user_name}, entiendo tu situación. {problem_acknowledgment} {solution_approach}",
                "{empathy_response} {analytical_approach} {support_assurance}",
                "Vamos a resolver esto juntos, {user_name}. {problem_solving_values}",
            ],
        }

        # Frases de valores por contexto
        self.value_phrases = {
            "formacion_integral": "Tu formación integral es fundamental para tu crecimiento.",
            "centralidad_persona": "Cada persona es única y valiosa, incluyéndote a ti.",
            "trascendencia": "Busquemos el sentido trascendente en lo que haces.",
            "verdad": "La pasión por la verdad nos guía hacia el conocimiento.",
            "liderazgo_positivo": "Tienes el potencial de ejercer un liderazgo positivo.",
            "dialogo": "El diálogo abierto enriquece nuestro entendimiento.",
            "compromiso_social": "Tu compromiso social puede transformar la comunidad.",
            "excelencia": "La excelencia en el actuar es nuestro estándar.",
            "esfuerzo_permanente": "El esfuerzo permanente lleva al éxito.",
        }

        # Configuración de respuesta
        self.max_response_length = 300  # Caracteres
        self.min_response_length = 50
        self.personality_integration_level = 0.8  # 0.0 - 1.0

    def generate_response(self, context: ResponseContext) -> LeonelResponse:
        """
        Genera respuesta completa con personalidad de Leonel

        Args:
            context: Contexto de la respuesta

        Returns:
            Respuesta generada con metadatos
        """
        start_time = time.time()

        # Obtener contexto inteligente usando memory_service
        smart_context = self.memory_service.get_smart_context_for_response(
            query=context.user_message,
            user_id=context.user_id,
            context_type="general"
        )

        # Obtener información del usuario - placeholder for now
        # TODO: Implement user summary retrieval using memory_service
        user_summary = {"profile": {"name": "amigo"}}
        user_name = context.user_name or user_summary.get("profile", {}).get("name", "amigo")

        # Generar componentes de respuesta
        response_components = self._generate_response_components(
            context, smart_context, user_summary, user_name
        )

        # Ensamblar respuesta final
        final_response = self._assemble_final_response(context, response_components, user_summary)

        # Aplicar personalización según preferencias del usuario
        personalized_response = self._apply_user_personalization(
            final_response, user_summary, context
        )

        # Calcular tiempo de respuesta
        response_time = (time.time() - start_time) * 1000

        # Crear objeto de respuesta
        leonel_response = LeonelResponse(
            content=personalized_response,
            personality_applied=True,
            context_tokens_used=smart_context.get("estimated_tokens", 0),
            response_time_ms=response_time,
            interaction_context=context.interaction_context,
            values_reflected=response_components.get("values_used", []),
            user_personalization={
                "name_used": user_name,
                "communication_style": user_summary.get("profile", {}).get(
                    "communication_preference"
                ),
                "context_relevant": len(smart_context.get("relevant_history", "")) > 0,
            },
        )

        return leonel_response

    def _generate_response_components(
        self,
        context: ResponseContext,
        smart_context: Dict[str, Any],
        user_summary: Dict[str, Any],
        user_name: str,
    ) -> Dict[str, Any]:
        """
        Genera componentes individuales de la respuesta
        """
        components = {
            "greeting": self._generate_greeting(context, user_name),
            "personality_intro": self._generate_personality_intro(context),
            "content_response": self._generate_content_response(context, smart_context),
            "values_integration": self._generate_values_integration(context),
            "motivational_element": self._generate_motivational_element(context),
            "closing": self._generate_closing(context, user_name),
            "values_used": [],
        }

        return components

    def _generate_greeting(self, context: ResponseContext, user_name: str) -> str:
        """
        Genera saludo apropiado según el contexto
        """
        if context.interaction_context == InteractionContext.GENERAL:
            return self.leonel_personality.get_greeting(user_name)
        elif context.interaction_context == InteractionContext.ACADEMIC:
            return f"Hola {user_name}"
        elif context.interaction_context == InteractionContext.MOTIVATIONAL:
            return f"¡{user_name}!"
        elif context.interaction_context == InteractionContext.SOCIAL:
            return f"¡Qué gusto saludarte, {user_name}!"
        else:
            return f"Hola {user_name}"

    def _generate_personality_intro(self, context: ResponseContext) -> str:
        """
        Genera introducción de personalidad según el contexto
        """
        if context.interaction_context == InteractionContext.GENERAL:
            return (
                f"Soy {self.leonel_personality.name}, "
                f"{self.leonel_personality.role} de la "
                f"{self.leonel_personality.university}."
            )
        elif context.interaction_context == InteractionContext.ACADEMIC:
            return "Como león de la comunidad Anáhuac, estoy aquí para apoyarte en tu formación."
        elif context.interaction_context == InteractionContext.MOTIVATIONAL:
            return "Recuerda que llevas dentro la fuerza y valentía del león Anáhuac."
        else:
            return ""

    @lru_cache(maxsize=50)
    def _get_cached_content_response(self, message_hash: str, has_context: bool) -> str:
        """
        Genera respuesta de contenido con cache para mejor rendimiento
        """
        # Usar patrones pre-compilados para mejor rendimiento
        if self._compiled_patterns["help_words"].search(message_hash):
            response = "Estoy aquí para brindarte todo mi apoyo. "
        elif self._compiled_patterns["thanks_words"].search(message_hash):
            response = "Es un honor poder ayudarte. "
        elif self._compiled_patterns["problem_words"].search(message_hash):
            response = "Entiendo que enfrentas un desafío. Juntos podemos encontrar la solución. "
        elif self._compiled_patterns["project_words"].search(message_hash):
            response = "Tu proyecto es una oportunidad de crecimiento y aprendizaje. "
        elif self._compiled_patterns["exam_words"].search(message_hash):
            response = "Los exámenes son oportunidades para demostrar tu preparación. "
        else:
            response = "Me interesa mucho lo que compartes conmigo. "

        # Agregar contexto relevante si está disponible
        if has_context:
            response += "Recordando nuestras conversaciones anteriores, "

        return response

    def _generate_content_response(
        self, context: ResponseContext, smart_context: Dict[str, Any]
    ) -> str:
        """
        Genera respuesta de contenido basada en el contexto inteligente
        Optimizado con cache y patrones pre-compilados
        """
        # Crear hash del mensaje para cache
        message_hash = context.user_message.lower()
        has_context = bool(smart_context.get("relevant_history"))

        return self._get_cached_content_response(message_hash, has_context)

    def _generate_values_integration(self, context: ResponseContext) -> str:
        """
        Integra valores de Anáhuac según el contexto
        """
        values_to_use = []

        if context.interaction_context == InteractionContext.ACADEMIC:
            values_to_use = ["excelencia", "formacion_integral", "verdad"]
        elif context.interaction_context == InteractionContext.MOTIVATIONAL:
            values_to_use = ["trascendencia", "liderazgo_positivo", "esfuerzo_permanente"]
        elif context.interaction_context == InteractionContext.SOCIAL:
            values_to_use = ["dialogo", "centralidad_persona", "compromiso_social"]
        elif context.interaction_context == InteractionContext.ACADEMIC:
            values_to_use = ["esfuerzo_permanente", "liderazgo_positivo", "excelencia"]
        else:
            values_to_use = ["centralidad_persona", "formacion_integral"]

        # Seleccionar un valor relevante
        if values_to_use:
            selected_value = values_to_use[0]  # Tomar el más relevante
            return self.value_phrases.get(selected_value, "")

        return ""

    def _generate_motivational_element(self, context: ResponseContext) -> str:
        """
        Genera elemento motivacional
        """
        if context.requires_empathy:
            return "Confío en tu capacidad para superar cualquier desafío. "
        elif context.urgency_level == "high":
            return "Tienes toda mi confianza y apoyo en este momento importante. "
        elif context.interaction_context == InteractionContext.ACADEMIC:
            return "Tu dedicación al estudio refleja el espíritu Anáhuac. "
        else:
            return self.leonel_personality.get_motivational_phrase(context.interaction_context)

    def _generate_closing(self, context: ResponseContext, user_name: str) -> str:
        """
        Genera cierre apropiado
        """
        if context.interaction_context == InteractionContext.ACADEMIC:
            return f"¡Adelante {user_name}, con excelencia y determinación!"
        elif context.interaction_context == InteractionContext.MOTIVATIONAL:
            return f"¡Tú puedes lograrlo, {user_name}! 🦁"
        elif context.interaction_context == InteractionContext.SOCIAL:
            return f"Siempre es un placer conversar contigo, {user_name}."
        else:
            return f"Estoy aquí cuando me necesites, {user_name}."

    def _assemble_final_response(
        self, context: ResponseContext, components: Dict[str, Any], user_summary: Dict[str, Any]
    ) -> str:
        """
        Ensambla la respuesta final combinando componentes
        Optimizado para reducir operaciones de string
        """
        # Pre-calcular condiciones para evitar evaluaciones repetidas
        is_social_general = context.interaction_context in [
            InteractionContext.GENERAL,
            InteractionContext.SOCIAL,
        ]
        total_interactions = user_summary.get("interaction_stats", {}).get("total_interactions", 0)
        is_new_user = total_interactions < 3

        # Usar lista para construcción eficiente de strings
        response_parts = []

        # Agregar componentes según condiciones pre-calculadas
        if is_social_general and components.get("greeting"):
            response_parts.append(components["greeting"])

        if components.get("personality_intro") and (
            context.interaction_context == InteractionContext.GENERAL or is_new_user
        ):
            response_parts.append(components["personality_intro"])

        # Componentes principales (siempre presentes)
        if components.get("content_response"):
            response_parts.append(components["content_response"])

        if components.get("values_integration"):
            response_parts.append(components["values_integration"])

        if components.get("motivational_element"):
            response_parts.append(components["motivational_element"])

        if components.get("closing"):
            response_parts.append(components["closing"])

        # Unir componentes de forma eficiente
        full_response = " ".join(filter(None, response_parts))

        # Ajustar longitud si es necesario (optimizado)
        response_len = len(full_response)
        if response_len > self.max_response_length:
            full_response = self._truncate_response(full_response)
        elif response_len < self.min_response_length:
            full_response = self._expand_response(full_response, context)

        return full_response

    def _apply_user_personalization(
        self, response: str, user_summary: Dict[str, Any], context: ResponseContext
    ) -> str:
        """
        Aplica personalización según las preferencias del usuario
        """
        # Obtener preferencia de comunicación
        comm_pref = user_summary.get("profile", {}).get("communication_preference")

        if comm_pref == "formal":
            # Hacer más formal
            response = response.replace("¡", "").replace("!", ".")
            response = re.sub(r"\b(tú|tu)\b", "usted", response, flags=re.IGNORECASE)
        elif comm_pref == "casual":
            # Hacer más casual
            response = response.replace("usted", "tú")
            if not any(char in response for char in "!¡"):
                response = response.replace(".", "!", 1)  # Agregar exclamación

        # Ajustar según intereses del usuario
        interests = user_summary.get("profile", {}).get("interests", [])
        if "tecnología" in interests and "proyecto" in context.user_message.lower():
            response += " La tecnología es una herramienta poderosa para el cambio positivo."
        elif "deportes" in interests and any(
            word in context.user_message.lower() for word in ["equipo", "competencia"]
        ):
            response += " El espíritu deportivo refleja los valores de esfuerzo y excelencia."

        return response

    def _truncate_response(self, response: str) -> str:
        """
        Trunca respuesta manteniendo coherencia
        """
        # Encontrar último punto antes del límite
        truncate_point = response.rfind(".", 0, self.max_response_length)
        if truncate_point > self.min_response_length:
            return response[: truncate_point + 1]
        else:
            # Truncar en palabra completa
            words = response[: self.max_response_length].split()
            return " ".join(words[:-1]) + "."

    def _expand_response(self, response: str, context: ResponseContext) -> str:
        """
        Expande respuesta si es muy corta
        """
        expansions = [
            " Me alegra poder acompañarte en este proceso.",
            " Juntos podemos lograr grandes cosas.",
            " Tu crecimiento es importante para toda la comunidad Anáhuac.",
            " Confío plenamente en tus capacidades.",
        ]

        # Seleccionar expansión apropiada
        if context.interaction_context == InteractionContext.ACADEMIC:
            expansion = " Tu dedicación al aprendizaje es admirable."
        elif context.interaction_context == InteractionContext.MOTIVATIONAL:
            expansion = " Tienes todo lo necesario para triunfar."
        else:
            expansion = expansions[0]

        return response + expansion

    def generate_quick_response(
        self,
        user_message: str,
        user_id: str,
        interaction_context: InteractionContext = InteractionContext.GENERAL,
    ) -> str:
        """
        Genera respuesta rápida para casos de baja latencia

        Args:
            user_message: Mensaje del usuario
            user_id: ID del usuario
            interaction_context: Contexto de interacción

        Returns:
            Respuesta rápida con personalidad básica
        """
        # Obtener nombre del usuario - placeholder for now
        # TODO: Implement user summary retrieval using memory_service
        user_summary = {"profile": {"name": "amigo"}}
        user_name = user_summary.get("profile", {}).get("name", "amigo")

        # Generar respuesta básica
        if interaction_context == InteractionContext.GENERAL:
            return (
                f"¡Hola {user_name}! Soy Leonel, tu león Anáhuac. " f"¿En qué puedo apoyarte hoy?"
            )
        elif interaction_context == InteractionContext.ACADEMIC:
            return (
                f"Hola {user_name}, estoy aquí para apoyarte en tu formación académica. "
                f"¿Qué necesitas?"
            )
        elif interaction_context == InteractionContext.MOTIVATIONAL:
            return (
                f"¡{user_name}! Recuerda que tienes la fuerza del león dentro de ti. "
                f"¡Tú puedes lograrlo!"
            )
        else:
            return (
                f"Hola {user_name}, soy Leonel. Estoy aquí para acompañarte. "
                f"¿Cómo puedo ayudarte?"
            )

    def analyze_user_message(self, message: str) -> Tuple[InteractionContext, bool, str]:
        """
        Analiza el mensaje del usuario para determinar contexto y necesidades

        Args:
            message: Mensaje del usuario

        Returns:
            Tupla con (contexto, requiere_empatía, urgencia)
        """
        message_lower = message.lower()

        # Detectar contexto
        if any(word in message_lower for word in ["hola", "buenos", "saludos", "hi"]):
            context = InteractionContext.GENERAL
        elif any(
            word in message_lower for word in ["tarea", "examen", "proyecto", "estudio", "clase"]
        ):
            context = InteractionContext.ACADEMIC
        elif any(
            word in message_lower for word in ["triste", "deprimido", "mal", "problema", "ayuda"]
        ):
            context = InteractionContext.MOTIVATIONAL
        elif any(word in message_lower for word in ["amigos", "social", "evento", "actividad"]):
            context = InteractionContext.SOCIAL
        elif any(word in message_lower for word in ["resolver", "solución", "cómo", "qué hacer"]):
            context = InteractionContext.ACADEMIC
        else:
            context = InteractionContext.GENERAL

        # Detectar necesidad de empatía
        requires_empathy = any(
            word in message_lower
            for word in [
                "triste",
                "mal",
                "problema",
                "difícil",
                "complicado",
                "preocupado",
                "estresado",
            ]
        )

        # Detectar urgencia
        if any(word in message_lower for word in ["urgente", "rápido", "ya", "ahora", "inmediato"]):
            urgency = "high"
        elif any(word in message_lower for word in ["cuando puedas", "sin prisa", "tranquilo"]):
            urgency = "low"
        else:
            urgency = "normal"

        return context, requires_empathy, urgency


# Función de utilidad para crear el generador
def create_leonel_response_generator(
    memory_service: MemoryService,
) -> LeonelResponseGenerator:
    """
    Crea una instancia del generador de respuestas de Leonel

    Args:
        memory_service: Servicio de memoria usando LangChain

    Returns:
        Instancia de LeonelResponseGenerator
    """
    return LeonelResponseGenerator(memory_service)


if __name__ == "__main__":
    # Test básico del generador de respuestas
    print("🦁 Testing Leonel Response Generator...")

    from src.backend.memory.memory_service import MemoryService

    memory_service = MemoryService()
    response_generator = create_leonel_response_generator(memory_service)

    # Test básico sin configuración de usuario específica
    context = ResponseContext(
        user_message="Hola Leonel, necesito motivación para mi examen",
        user_id="test_user_456",
        interaction_context=InteractionContext.MOTIVATIONAL,
        requires_empathy=True,
    )

    response = response_generator.generate_response(context)

    print(f"✅ Response generated: {response.content}")
    print(f"📊 Tokens used: {response.context_tokens_used}")
    print(f"⏱️ Response time: {response.response_time_ms:.2f}ms")
    print(f"🎯 Values reflected: {response.values_reflected}")
