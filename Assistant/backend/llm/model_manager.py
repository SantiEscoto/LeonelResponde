# Standard library imports
import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Third-party imports
from llama_cpp import Llama

# Local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Importar config una sola vez
try:
    import config
except ImportError:
    config = None

try:
    from backend.utils.logger import get_logger
except ImportError:
    # Fallback si no se puede importar el logger
    import logging
    def get_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)

logger = get_logger("LLM")

class LLMManager:
    """
    Gestor de modelo LLM local usando llama-cpp-python
    Optimizado para modelos GGUF cuantizados
    """
    
    def __init__(self, model_path: str):
        """
        Inicializa el gestor de modelo LLM
        
        Args:
            model_path: Ruta al archivo del modelo GGUF
        """
        self.model_path = model_path
        self.model: Optional[Llama] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.is_loaded = False
        
        # Parámetros de generación por defecto
        self.params = {
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "n_ctx": 2048
        }
        
        logger.info(f"🧠 Inicializando LLMManager con modelo: {model_path}")
    
    def load_model(self) -> bool:
        """Carga el modelo GGUF en memoria con configuración optimizada"""
        try:
            # Verificar que el archivo existe
            if not os.path.exists(self.model_path):
                logger.error(f"❌ Modelo no encontrado en: {self.model_path}")
                return False
            
            # Valores por defecto para parámetros
            n_ctx = self.params.get("n_ctx", 2048)
            n_threads = 4
            n_gpu_layers = 0
            
            # Intentar importar configuración global de forma segura
            try:
                # Obtener parámetros optimizados de la configuración global
                if config and hasattr(config, 'LLM_CONFIG'):
                    n_ctx = config.LLM_CONFIG.get("n_ctx", n_ctx)
                    n_threads = config.LLM_CONFIG.get("n_threads", n_threads)
                    n_gpu_layers = config.LLM_CONFIG.get("n_gpu_layers", n_gpu_layers)
                    
                    # Actualizar parámetros locales con los de la configuración global
                    self.params["n_ctx"] = n_ctx
                    self.params["max_tokens"] = config.LLM_CONFIG.get("max_tokens", self.params.get("max_tokens", 256))
                    self.params["temperature"] = config.LLM_CONFIG.get("temperature", self.params.get("temperature", 0.7))
                    self.params["top_p"] = config.LLM_CONFIG.get("top_p", self.params.get("top_p", 0.95))
                    self.params["top_k"] = config.LLM_CONFIG.get("top_k", self.params.get("top_k", 40))
            except (ImportError, AttributeError) as e:
                logger.warning(f"No se pudo importar configuración global: {e}")
                logger.warning("Usando valores por defecto para parámetros del modelo")
            
            logger.info(f"📥 Cargando modelo GGUF: {self.model_path}...")
            logger.info(f"⚙️ Parámetros: n_ctx={n_ctx}, n_threads={n_threads}, n_gpu_layers={n_gpu_layers}")
            
            # Cargar modelo con llama-cpp-python con parámetros optimizados
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                verbose=False  # Reducir logs para mejor rendimiento
            )
            
            self.is_loaded = True
            logger.info("✅ Modelo GGUF cargado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cargando modelo GGUF: {e}")
            print(f"❌ Error detallado: {e}")
            return False
    
    def query(self, text: str, context: List[str] = None, timeout: int = 30) -> str:
        """
        Procesa una consulta y devuelve respuesta con límite de tiempo
        
        Args:
            text: Texto de la consulta del usuario
            context: Lista opcional de textos de contexto para RAG
            timeout: Tiempo máximo en segundos para generar respuesta (default: 30s)
            
        Returns:
            Respuesta generada por el modelo o mensaje de timeout
        """
        import time
        
        if not self.is_loaded:
            logger.warning("⚠️ Modelo no cargado, intentando cargar...")
            if not self.load_model():
                return "Error: No pude cargar el modelo LLM"
        
        try:
            logger.info(f"🤔 Procesando consulta: {text[:50]}... (timeout: {timeout}s)")
            start_time = time.time()
            
            # Preparar prompt con formato para chat (optimizado para concisión)
            system_prompt = """Eres Leonel, un asistente conversacional que responde en ESPAÑOL MEXICANO de forma CONCISA y DIRECTA.

Reglas ESTRICTAS:
1. IDIOMA: Solo español (excepto nombres propios/términos técnicos)
2. BREVEDAD: Máximo 2-3 oraciones para preguntas simples, máximo 100 palabras para temas complejos
3. ESTILO: Directo, sin rodeos, sin repetir información obvia
4. FORMATO: Respuestas claras, usa listas solo si es necesario

Sé útil pero conciso. No expliques lo que no te preguntan."""
            
            # Incluir contexto si existe (limitado para mejor rendimiento)
            if context and len(context) > 0:
                # Limitar tamaño del contexto para mejor rendimiento
                max_context_len = 1500
                context_text = "\n".join(context)
                if len(context_text) > max_context_len:
                    context_text = context_text[:max_context_len] + "..."
                system_prompt += f"\n\nInformación relevante de conversaciones anteriores:\n{context_text}"
            
            # Crear prompt en formato chat para Llama
            prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{text} [/INST]"
            
            # Generar respuesta directamente con el modelo (sin ThreadPoolExecutor)
            # Nota: Implementamos un timeout manual basado en tiempo transcurrido
            max_tokens = min(self.params.get("max_tokens", 256), 256)  # Limitar tokens para respuestas más rápidas
            
            # Configurar parámetros de generación
            result = self.model.create_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=self.params.get("temperature", 0.7),
                top_p=self.params.get("top_p", 0.95),
                top_k=self.params.get("top_k", 40),
                repeat_penalty=self.params.get("repeat_penalty", 1.1),
                stop=["</s>", "[INST]", "[/INST]"],
                echo=False
            )
            
            # Extraer respuesta
            response = result["choices"][0]["text"].strip()
            
            # Si la respuesta está vacía o muy corta, dar una por defecto
            if not response or len(response) < 5:
                response = "Entiendo tu mensaje. ¿Puedes darme más detalles?"
            
            # Verificar si se excedió el tiempo límite
            total_time = time.time() - start_time
            if total_time > timeout:
                logger.warning(f"⏱️ Tiempo de respuesta excedido: {total_time:.2f}s > {timeout}s")
                response += f"\n\n(Nota: Esta respuesta tomó {total_time:.2f}s, superando el límite recomendado de {timeout}s)"
            
            # Actualizar historial
            self.conversation_history.append({"role": "user", "content": text})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Mantener historial limitado (reducido para mejor rendimiento)
            if len(self.conversation_history) > 10:  # Reducido de 20 a 10 para mejor rendimiento
                self.conversation_history = self.conversation_history[-10:]
            
            # Registrar tiempo total
            logger.info(f"💬 Respuesta generada en {total_time:.2f}s: {response[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error generando respuesta: {e}")
            return f"Lo siento, tuve un problema: {str(e)[:100]}"
    
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
            if config and hasattr(config, 'LLM_CONFIG'):
                timeout = config.LLM_CONFIG.get("response_timeout", 30)
        except (AttributeError) as e:
            logger.warning(f"No se pudo acceder a configuración: {e}")
        
        return {
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "conversation_length": len(self.conversation_history) // 2,  # Pares de mensajes
            "params": self.params,
            "timeout": timeout,
            "optimized": True,
            "max_tokens": self.params.get("max_tokens", 256),
            "context_size": self.params.get("n_ctx", 2048)
        }
    
    def clear_history(self):
        """Limpia el historial de conversación"""
        self.conversation_history.clear()
        logger.info("🧹 Historial de conversación limpiado")

# Test de importación
if __name__ == "__main__":
    print("🧪 Testing LLMManager...")
    # Ruta de ejemplo para testing
    test_model_path = "../../../models/llm/llama-2-7b-chat.Q4_K_M.gguf"
    llm = LLMManager(test_model_path)
    print(f"✅ LLMManager creado: {llm}")
    print(f"📊 Estado inicial: {llm.get_status()}")