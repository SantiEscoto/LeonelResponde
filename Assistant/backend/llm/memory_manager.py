# Standard library imports
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from backend.utils.logger import get_logger
except ImportError:
    # Fallback if logger import fails
    def get_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)

logger = get_logger("Memory")

class MemoryManager:
    """
    Gestor de memoria para el asistente
    Implementa un sistema de memoria a corto y largo plazo
    """
    
    def __init__(self, memory_file: Optional[str] = None):
        """
        Inicializa el gestor de memoria
        
        Args:
            memory_file: Ruta opcional al archivo de memoria persistente
        """
        # Memoria a corto plazo (buffer circular)
        self.short_term_memory: List[Dict[str, Any]] = []
        self.max_short_term_size = 50  # Número máximo de mensajes en memoria corto plazo (aumentado de 20)
        self.auto_transition_threshold = 30  # Umbral para transición automática a largo plazo
        
        # Memoria a largo plazo (persistente)
        self.long_term_memory: List[Dict[str, Any]] = []
        self.memory_file = memory_file or "models/memory/long_term_memory.json"
        
        # Crear directorios necesarios
        self._ensure_memory_directories()
        
        # Cargar memoria persistente si existe
        if os.path.exists(self.memory_file):
            self._load_memory()
        
        logger.info(f"🧠 MemoryManager inicializado")
    
    def add_interaction(self, user_message: str, assistant_response: str) -> None:
        """
        Agrega una interacción a la memoria a corto plazo
        
        Args:
            user_message: Mensaje del usuario
            assistant_response: Respuesta del asistente
        """
        # Crear registro de interacción
        interaction = {
            "timestamp": time.time(),
            "user_message": user_message,
            "assistant_response": assistant_response
        }
        
        # Agregar a memoria a corto plazo
        self.short_term_memory.append(interaction)
        
        # Verificar si necesitamos transición automática a largo plazo
        if len(self.short_term_memory) >= self.auto_transition_threshold:
            self._auto_transition_to_long_term()
        
        # Mantener tamaño limitado (buffer circular)
        if len(self.short_term_memory) > self.max_short_term_size:
            self.short_term_memory = self.short_term_memory[-self.max_short_term_size:]
        
        # Guardar automáticamente la memoria después de cada interacción
        self._save_memory()
        
        logger.debug(f"💾 Interacción agregada a memoria corto plazo ({len(self.short_term_memory)}/{self.max_short_term_size})")
    
    def add_to_long_term(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """
        Agrega información a la memoria a largo plazo
        
        Args:
            content: Contenido a recordar
            metadata: Metadatos opcionales (categoría, importancia, grupo, etc.)
        """
        if metadata is None:
            metadata = {}
        
        # Agregar metadatos por defecto para organización
        if "group" not in metadata:
            metadata["group"] = "general"
        if "category" not in metadata:
            metadata["category"] = "conversation"
        if "importance" not in metadata:
            metadata["importance"] = "medium"
        
        # Crear registro de memoria
        memory_item = {
            "timestamp": time.time(),
            "content": content,
            "metadata": metadata
        }
        
        # Agregar a memoria a largo plazo
        self.long_term_memory.append(memory_item)
        
        # Persistir memoria automáticamente
        if self.memory_file:
            self._save_memory()
        
        logger.info(f"📝 Información agregada a memoria largo plazo [{metadata.get('group', 'general')}]: {content[:50]}...")
    
    def get_recent_context(self, max_items: int = 5) -> List[str]:
        """
        Obtiene las interacciones recientes como contexto para el LLM
        
        Args:
            max_items: Número máximo de interacciones a incluir
            
        Returns:
            Lista de strings con formato "Usuario: ... / Asistente: ..."
        """
        context = []
        
        # Obtener las últimas interacciones (limitado por max_items)
        recent_interactions = self.short_term_memory[-max_items:]
        
        for interaction in recent_interactions:
            user_msg = interaction["user_message"]
            assistant_msg = interaction["assistant_response"]
            context.append(f"Usuario: {user_msg}\nAsistente: {assistant_msg}")
        
        return context
    
    def get_relevant_memories(self, query: str, max_items: int = 3) -> List[Dict[str, Any]]:
        """
        Obtiene memorias relevantes para una consulta
        Implementa búsqueda mejorada con múltiples criterios de relevancia
        
        Args:
            query: Consulta para buscar memorias relevantes
            max_items: Número máximo de memorias a devolver
            
        Returns:
            Lista de diccionarios con memorias relevantes y sus metadatos
        """
        if not self.long_term_memory:
            return []
            
        relevant_memories = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Palabras clave importantes que aumentan la relevancia
        important_words = {'importante', 'recordar', 'clave', 'esencial', 'crítico', 'fundamental'}
        
        for memory in self.long_term_memory:
            content = memory["content"].lower()
            content_words = set(content.split())
            
            # Calcular diferentes tipos de relevancia
            score = 0
            
            # 1. Coincidencias exactas de palabras (peso alto)
            exact_matches = len(query_words.intersection(content_words))
            score += exact_matches * 3
            
            # 2. Coincidencias parciales (subcadenas)
            for query_word in query_words:
                if len(query_word) > 3:  # Solo palabras significativas
                    if query_word in content:
                        score += 2
            
            # 3. Búsqueda de frases completas
            if len(query_lower) > 10 and query_lower in content:
                score += 10
            
            # 4. Bonus por importancia en metadatos
            metadata = memory.get("metadata", {})
            if metadata.get("importance") == "high":
                score += 2
            if metadata.get("group") == "user_added":
                score += 3  # Información agregada manualmente es más relevante
            
            # 5. Bonus por palabras importantes en el contenido
            content_important = len(important_words.intersection(content_words))
            score += content_important * 2
            
            # 6. Penalización por antigüedad (memorias muy viejas son menos relevantes)
            timestamp = memory.get("timestamp", time.time())
            age_days = (time.time() - timestamp) / (24 * 3600)
            if age_days > 30:  # Más de 30 días
                score *= 0.8
            
            # Solo incluir memorias con score > 0
            if score > 0:
                relevant_memories.append((memory, score))
        
        # Ordenar por relevancia (score más alto primero)
        relevant_memories.sort(key=lambda x: x[1], reverse=True)
        
        # Devolver las memorias más relevantes
        result = [memory[0] for memory in relevant_memories[:max_items]]
        
        # Log para debugging
        if result:
            logger.debug(f"🔍 Encontradas {len(result)} memorias relevantes para: '{query[:50]}...'")
            for i, (memory, score) in enumerate(relevant_memories[:max_items]):
                content_preview = memory["content"][:50] + "..." if len(memory["content"]) > 50 else memory["content"]
                logger.debug(f"  {i+1}. Score: {score:.1f} - {content_preview}")
        
        return result
        
    def get_relevant_memory_contents(self, query: str, max_items: int = 3) -> List[str]:
        """
        Obtiene solo el contenido de las memorias relevantes para una consulta
        
        Args:
            query: Consulta para buscar memorias relevantes
            max_items: Número máximo de memorias a devolver
            
        Returns:
            Lista de strings con contenidos de memorias relevantes
        """
        memories = self.get_relevant_memories(query, max_items)
        return [memory["content"] for memory in memories]
    
    def generate_summary(self) -> str:
        """
        Genera un resumen de la conversación actual
        Versión simple - en el futuro usará el LLM para generar resúmenes
        
        Returns:
            Resumen de la conversación
        """
        if not self.short_term_memory:
            return "No hay conversación para resumir."
        
        # Versión simple: extraer temas principales
        all_text = " ".join([item["user_message"] + " " + item["assistant_response"] 
                          for item in self.short_term_memory])
        
        # Contar palabras y encontrar las más frecuentes (excluyendo palabras comunes)
        words = all_text.lower().split()
        word_count = {}
        
        common_words = {"el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "a", "de", "en", "que", "por", "con", "para"}
        
        for word in words:
            if len(word) > 3 and word not in common_words:
                word_count[word] = word_count.get(word, 0) + 1
        
        # Encontrar palabras más frecuentes
        top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Crear resumen simple
        summary = "Resumen de la conversación:\n"
        summary += f"- {len(self.short_term_memory)} interacciones\n"
        summary += f"- Temas principales: {', '.join([word for word, _ in top_words])}\n"
        
        # Agregar primera y última interacción
        first = self.short_term_memory[0]
        last = self.short_term_memory[-1]
        
        summary += f"\nInicio: Usuario: '{first['user_message'][:50]}...'\n"
        summary += f"Final: Usuario: '{last['user_message'][:50]}...'\n"
        
        return summary
    
    def _auto_transition_to_long_term(self) -> None:
        """
        Transición automática de memoria a corto plazo a largo plazo
        Genera un resumen de las interacciones más antiguas y las mueve a largo plazo
        """
        if len(self.short_term_memory) < self.auto_transition_threshold:
            return
        
        # Tomar las primeras 10 interacciones para resumir
        interactions_to_summarize = self.short_term_memory[:10]
        
        # Generar resumen de las interacciones
        summary_content = self._generate_interaction_summary(interactions_to_summarize)
        
        # Crear metadatos para el resumen
        metadata = {
            "group": "conversation_summary",
            "category": "auto_transition",
            "importance": "high",
            "interaction_count": len(interactions_to_summarize),
            "time_range": {
                "start": interactions_to_summarize[0]["timestamp"],
                "end": interactions_to_summarize[-1]["timestamp"]
            }
        }
        
        # Agregar resumen a memoria a largo plazo
        self.add_to_long_term(summary_content, metadata)
        
        # Remover las interacciones resumidas de memoria a corto plazo
        self.short_term_memory = self.short_term_memory[10:]
        
        logger.info(f"🔄 Transición automática: {len(interactions_to_summarize)} interacciones resumidas y movidas a largo plazo")
    
    def _generate_interaction_summary(self, interactions: List[Dict[str, Any]]) -> str:
        """
        Genera un resumen de un conjunto de interacciones
        
        Args:
            interactions: Lista de interacciones a resumir
            
        Returns:
            Resumen textual de las interacciones
        """
        if not interactions:
            return "Sin interacciones para resumir"
        
        # Extraer temas y conceptos principales
        all_user_messages = [interaction["user_message"] for interaction in interactions]
        all_assistant_responses = [interaction["assistant_response"] for interaction in interactions]
        
        # Análisis simple de palabras clave
        all_text = " ".join(all_user_messages + all_assistant_responses).lower()
        words = all_text.split()
        
        # Filtrar palabras comunes
        common_words = {"el", "la", "los", "las", "un", "una", "de", "en", "que", "por", "con", "para", "es", "son", "está", "están", "como", "qué", "cómo", "dónde", "cuándo", "por qué", "porque"}
        filtered_words = [word for word in words if len(word) > 3 and word not in common_words]
        
        # Contar frecuencias
        word_count = {}
        for word in filtered_words:
            word_count[word] = word_count.get(word, 0) + 1
        
        # Obtener palabras más frecuentes
        top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Crear resumen estructurado
        start_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(interactions[0]["timestamp"]))
        end_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(interactions[-1]["timestamp"]))
        
        summary = f"Resumen de conversación ({start_time} - {end_time}):\n"
        summary += f"- {len(interactions)} interacciones\n"
        summary += f"- Temas principales: {', '.join([word for word, _ in top_words])}\n"
        
        # Agregar primera y última interacción como contexto
        first_user = interactions[0]["user_message"][:100] + "..." if len(interactions[0]["user_message"]) > 100 else interactions[0]["user_message"]
        last_user = interactions[-1]["user_message"][:100] + "..." if len(interactions[-1]["user_message"]) > 100 else interactions[-1]["user_message"]
        
        summary += f"\nInicio: '{first_user}'\n"
        summary += f"Final: '{last_user}'"
        
        return summary
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de la memoria
        
        Returns:
            Diccionario con información sobre el estado de la memoria
        """
        return {
            "interactions": len(self.short_term_memory),
            "long_term_count": len(self.long_term_memory),
            "max_short_term": self.max_short_term_size,
            "file": self.memory_file if self.memory_file else "No configurado"
        }
        
    def delete_long_term_memory(self, index: int) -> bool:
        """Elimina una memoria específica del almacenamiento a largo plazo
        
        Args:
            index: Índice de la memoria a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        if not 0 <= index < len(self.long_term_memory):
            logger.error(f"❌ Índice de memoria inválido: {index}")
            return False
            
        try:
            # Guardar información para el log
            memory = self.long_term_memory[index]
            content_preview = memory["content"][:50] + "..." if len(memory["content"]) > 50 else memory["content"]
            
            # Eliminar la memoria
            del self.long_term_memory[index]
            
            # Guardar cambios
            if self.memory_file:
                self._save_memory()
                
            logger.info(f"🗑️ Memoria eliminada: {content_preview}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error eliminando memoria: {e}")
            return False
            
    def list_long_term_memories(self, max_items: int = None, include_content: bool = True) -> List[Dict[str, Any]]:
        """Lista las memorias a largo plazo
        
        Args:
            max_items: Número máximo de memorias a listar (None para todas)
            include_content: Si se debe incluir el contenido completo
            
        Returns:
            Lista de diccionarios con información sobre las memorias
        """
        result = []
        memories = self.long_term_memory[:max_items] if max_items is not None else self.long_term_memory
        
        for i, memory in enumerate(memories):
            memory_info = {
                "index": i,
                "timestamp": memory["timestamp"],
                "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(memory["timestamp"])),
                "metadata": memory["metadata"]
            }
            
            if include_content:
                memory_info["content"] = memory["content"]
            else:
                # Incluir solo una vista previa del contenido
                preview_length = 100
                content = memory["content"]
                memory_info["content_preview"] = content[:preview_length] + "..." if len(content) > preview_length else content
                
            result.append(memory_info)
            
        return result
    
    def clear_short_term(self) -> None:
        """Limpia la memoria a corto plazo"""
        self.short_term_memory.clear()
        logger.info("🧹 Memoria a corto plazo limpiada")
    
    def clear_long_term(self) -> None:
        """Limpia la memoria a largo plazo"""
        self.long_term_memory.clear()
        if self.memory_file:
            self._save_memory()
        logger.info("🧹 Memoria a largo plazo limpiada")
    
    def clear_memory(self) -> None:
        """Limpia toda la memoria (corto y largo plazo)"""
        self.clear_short_term()
        self.clear_long_term()
        logger.info("🧹 Toda la memoria ha sido limpiada")
    
    def _save_memory(self) -> None:
        """Guarda la memoria a largo plazo en archivo"""
        if not self.memory_file:
            return
        
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.long_term_memory, f, ensure_ascii=False, indent=2)
                
            logger.info(f"💾 Memoria guardada en {self.memory_file}")
        except Exception as e:
            logger.error(f"❌ Error guardando memoria: {e}")
    
    def _ensure_memory_directories(self) -> None:
        """Crea los directorios necesarios para la memoria"""
        if self.memory_file:
            memory_dir = os.path.dirname(self.memory_file)
            if memory_dir:
                os.makedirs(memory_dir, exist_ok=True)
                logger.debug(f"📁 Directorio de memoria asegurado: {memory_dir}")
    
    def _load_memory(self) -> None:
        """Carga la memoria a largo plazo desde archivo"""
        if not self.memory_file or not os.path.exists(self.memory_file):
            return
        
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                self.long_term_memory = json.load(f)
                
            logger.info(f"📂 Memoria cargada desde {self.memory_file}: {len(self.long_term_memory)} items")
        except Exception as e:
            logger.error(f"❌ Error cargando memoria: {e}")
            # Inicializar como vacía en caso de error
            self.long_term_memory = []
    
    def load_from_text_file(self, file_path: str, metadata: Dict[str, Any] = None) -> bool:
        """Carga memoria desde un archivo de texto
        
        Args:
            file_path: Ruta al archivo de texto
            metadata: Metadatos opcionales para asociar con el contenido
            
        Returns:
            bool: True si se cargó correctamente, False en caso contrario
        """
        if not os.path.exists(file_path):
            logger.error(f"❌ Archivo no encontrado: {file_path}")
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                logger.warning(f"⚠️ Archivo vacío: {file_path}")
                return False
                
            # Crear metadatos por defecto si no se proporcionan
            if metadata is None:
                metadata = {}
                
            # Agregar información sobre el archivo a los metadatos
            file_metadata = {
                "source": "text_file",
                "file_name": os.path.basename(file_path),
                "import_date": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Combinar con los metadatos proporcionados
            combined_metadata = {**file_metadata, **metadata}
            
            # Agregar a memoria a largo plazo
            self.add_to_long_term(content, combined_metadata)
            
            logger.info(f"📄 Memoria cargada desde archivo de texto: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando desde archivo de texto: {e}")
            return False
    
    def get_memories_by_group(self, group: str, max_items: int = None) -> List[Dict[str, Any]]:
        """
        Obtiene memorias filtradas por grupo
        
        Args:
            group: Nombre del grupo a filtrar
            max_items: Número máximo de memorias a devolver
            
        Returns:
            Lista de memorias del grupo especificado
        """
        group_memories = [memory for memory in self.long_term_memory 
                         if memory["metadata"].get("group") == group]
        
        if max_items is not None:
            group_memories = group_memories[:max_items]
            
        return group_memories
    
    def list_memory_groups(self) -> Dict[str, int]:
        """
        Lista todos los grupos de memoria disponibles con su conteo
        
        Returns:
            Diccionario con grupos y número de memorias en cada uno
        """
        groups = {}
        for memory in self.long_term_memory:
            group = memory["metadata"].get("group", "general")
            groups[group] = groups.get(group, 0) + 1
            
        return groups
    
    def create_memory_group(self, group_name: str, description: str = "") -> None:
        """
        Crea un nuevo grupo de memoria conceptual
        
        Args:
            group_name: Nombre del grupo
            description: Descripción opcional del grupo
        """
        # Agregar información del grupo como metadata especial
        group_info = {
            "group_name": group_name,
            "description": description,
            "created_at": time.time()
        }
        
        metadata = {
            "group": "_group_definitions",
            "category": "group_info",
            "importance": "system",
            "group_info": group_info
        }
        
        content = f"Grupo de memoria: {group_name}\nDescripción: {description}"
        self.add_to_long_term(content, metadata)
        
        logger.info(f"📁 Nuevo grupo de memoria creado: {group_name}")
    
    def transition_short_to_long_manual(self, concept_name: str, description: str = "") -> bool:
        """
        Transición manual de memoria a corto plazo a largo plazo con concepto específico
        
        Args:
            concept_name: Nombre del concepto/grupo para organizar la memoria
            description: Descripción opcional del concepto
            
        Returns:
            bool: True si se realizó la transición correctamente
        """
        if not self.short_term_memory:
            logger.warning("⚠️ No hay memoria a corto plazo para transferir")
            return False
        
        # Generar resumen de toda la memoria a corto plazo
        summary_content = self._generate_interaction_summary(self.short_term_memory)
        
        # Crear metadatos específicos para el concepto
        metadata = {
            "group": concept_name,
            "category": "manual_transition",
            "importance": "high",
            "description": description,
            "interaction_count": len(self.short_term_memory),
            "manual_concept": True
        }
        
        # Agregar a memoria a largo plazo
        self.add_to_long_term(summary_content, metadata)
        
        # Limpiar memoria a corto plazo
        interactions_count = len(self.short_term_memory)
        self.clear_short_term()
        
        logger.info(f"🔄 Transición manual completada: {interactions_count} interacciones organizadas en concepto '{concept_name}'")
        return True

# Test de importación
if __name__ == "__main__":
    print("🧪 Testing MemoryManager...")
    memory = MemoryManager()
    memory.add_interaction("Hola, ¿cómo estás?", "Estoy bien, ¿en qué puedo ayudarte?")
    memory.add_interaction("¿Qué puedes hacer?", "Puedo responder preguntas y ayudarte con tareas.")
    print(f"✅ Contexto reciente: {memory.get_recent_context()}")
    print(f"📝 Resumen: {memory.generate_summary()}")