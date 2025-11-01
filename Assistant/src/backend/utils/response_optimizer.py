"""
Optimizador de respuestas para mejorar tiempos de respuesta
Incluye streaming, batching y optimizaciones de contexto
"""

import asyncio
import time
import threading
from typing import Any, Dict, List, Optional, Union, Generator, AsyncGenerator
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResponseConfig:
    """Configuración para optimización de respuestas"""
    # Streaming
    enable_streaming: bool = True
    stream_chunk_size: int = 50
    stream_delay_ms: int = 10
    
    # Batching
    enable_batching: bool = True
    batch_size: int = 4
    batch_timeout_ms: int = 100
    
    # Context optimization
    max_context_length: int = 4096
    context_compression_ratio: float = 0.8
    
    # Performance
    enable_async_processing: bool = True
    max_concurrent_requests: int = 8
    response_timeout: int = 30


class ResponseOptimizer:
    """
    Optimizador de respuestas con streaming, batching y procesamiento asíncrono
    """
    
    def __init__(self, config: Optional[ResponseConfig] = None):
        self.config = config or ResponseConfig()
        self.request_queue = asyncio.Queue()
        self.response_cache = {}
        self.active_requests = 0
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_requests)
        self._shutdown = False
        
        logger.info(f"🚀 ResponseOptimizer inicializado: streaming={self.config.enable_streaming}, "
                   f"batching={self.config.enable_batching}")
    
    def optimize_context(self, context: List[str], max_length: Optional[int] = None) -> List[str]:
        """
        Optimiza el contexto para reducir el tamaño manteniendo relevancia
        
        Args:
            context: Lista de textos de contexto
            max_length: Longitud máxima del contexto
            
        Returns:
            Lista optimizada de contexto
        """
        if not context:
            return []
        
        max_length = max_length or self.config.max_context_length
        
        # Calcular longitud total
        total_length = sum(len(text) for text in context)
        
        if total_length <= max_length:
            return context
        
        # Ordenar por relevancia (longitud como proxy de relevancia)
        sorted_context = sorted(context, key=len, reverse=True)
        
        # Seleccionar contexto hasta alcanzar el límite
        optimized_context = []
        current_length = 0
        
        for text in sorted_context:
            if current_length + len(text) <= max_length:
                optimized_context.append(text)
                current_length += len(text)
            else:
                # Truncar el último texto si es necesario
                remaining = max_length - current_length
                if remaining > 100:  # Solo si queda espacio significativo
                    optimized_context.append(text[:remaining] + "...")
                break
        
        logger.debug(f"📝 Contexto optimizado: {len(context)} -> {len(optimized_context)} elementos, "
                    f"{total_length} -> {current_length} caracteres")
        
        return optimized_context
    
    def create_streaming_response(self, text: str, chunk_size: Optional[int] = None) -> Generator[str, None, None]:
        """
        Crea una respuesta en streaming para mejorar la percepción de velocidad
        
        Args:
            text: Texto completo a enviar
            chunk_size: Tamaño de cada chunk
            
        Yields:
            Chunks del texto
        """
        chunk_size = chunk_size or self.config.stream_chunk_size
        
        if not self.config.enable_streaming:
            yield text
            return
        
        # Dividir texto en chunks
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            yield chunk
            
            # Pequeña pausa para simular streaming natural
            if self.config.stream_delay_ms > 0:
                time.sleep(self.config.stream_delay_ms / 1000.0)
    
    async def create_async_streaming_response(
        self, 
        text: str, 
        chunk_size: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Crea una respuesta en streaming asíncrona
        
        Args:
            text: Texto completo a enviar
            chunk_size: Tamaño de cada chunk
            
        Yields:
            Chunks del texto
        """
        chunk_size = chunk_size or self.config.stream_chunk_size
        
        if not self.config.enable_streaming:
            yield text
            return
        
        # Dividir texto en chunks
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            yield chunk
            
            # Pausa asíncrona
            if self.config.stream_delay_ms > 0:
                await asyncio.sleep(self.config.stream_delay_ms / 1000.0)
    
    def batch_requests(self, requests: List[Dict[str, Any]]) -> List[Any]:
        """
        Procesa múltiples requests en lotes para mejorar eficiencia
        
        Args:
            requests: Lista de requests a procesar
            
        Returns:
            Lista de respuestas
        """
        if not self.config.enable_batching or len(requests) <= 1:
            return requests
        
        # Agrupar requests en lotes
        batches = []
        for i in range(0, len(requests), self.config.batch_size):
            batch = requests[i:i + self.config.batch_size]
            batches.append(batch)
        
        results = []
        for batch in batches:
            # Procesar lote en paralelo
            with ThreadPoolExecutor(max_workers=min(len(batch), self.config.max_concurrent_requests)) as executor:
                future_to_request = {
                    executor.submit(self._process_single_request, req): req 
                    for req in batch
                }
                
                for future in as_completed(future_to_request):
                    try:
                        result = future.result(timeout=self.config.response_timeout)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"❌ Error procesando request en lote: {e}")
                        results.append({"error": str(e)})
        
        return results
    
    def _process_single_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un request individual
        
        Args:
            request: Request a procesar
            
        Returns:
            Respuesta procesada
        """
        # Simular procesamiento
        time.sleep(0.1)  # Simulación de procesamiento
        return {"response": f"Processed: {request.get('text', '')}"}
    
    async def process_async_requests(
        self, 
        requests: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Procesa múltiples requests de forma asíncrona
        
        Args:
            requests: Lista de requests a procesar
            
        Returns:
            Lista de respuestas
        """
        if not self.config.enable_async_processing:
            return self.batch_requests(requests)
        
        # Crear tareas asíncronas
        tasks = []
        for request in requests:
            task = asyncio.create_task(self._process_async_request(request))
            tasks.append(task)
        
        # Esperar todas las tareas
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados y excepciones
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Error en request asíncrono {i}: {result}")
                processed_results.append({"error": str(result)})
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_async_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un request de forma asíncrona
        
        Args:
            request: Request a procesar
            
        Returns:
            Respuesta procesada
        """
        # Simular procesamiento asíncrono
        await asyncio.sleep(0.1)
        return {"response": f"Async processed: {request.get('text', '')}"}
    
    def optimize_prompt(self, prompt: str, max_length: Optional[int] = None) -> str:
        """
        Optimiza el prompt para mejorar eficiencia
        
        Args:
            prompt: Prompt original
            max_length: Longitud máxima del prompt
            
        Returns:
            Prompt optimizado
        """
        max_length = max_length or self.config.max_context_length
        
        if len(prompt) <= max_length:
            return prompt
        
        # Estrategias de optimización
        optimized_prompt = prompt
        
        # 1. Eliminar espacios múltiples
        import re
        optimized_prompt = re.sub(r'\s+', ' ', optimized_prompt)
        
        # 2. Truncar si sigue siendo muy largo
        if len(optimized_prompt) > max_length:
            # Truncar manteniendo palabras completas
            words = optimized_prompt.split()
            truncated_words = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 <= max_length - 3:  # -3 para "..."
                    truncated_words.append(word)
                    current_length += len(word) + 1
                else:
                    break
            
            optimized_prompt = ' '.join(truncated_words) + "..."
        
        logger.debug(f"📝 Prompt optimizado: {len(prompt)} -> {len(optimized_prompt)} caracteres")
        
        return optimized_prompt
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas de rendimiento del optimizador
        
        Returns:
            Diccionario con métricas
        """
        return {
            "active_requests": self.active_requests,
            "config": {
                "streaming_enabled": self.config.enable_streaming,
                "batching_enabled": self.config.enable_batching,
                "async_enabled": self.config.enable_async_processing,
                "max_concurrent": self.config.max_concurrent_requests,
                "batch_size": self.config.batch_size
            },
            "cache_size": len(self.response_cache),
            "executor_threads": self.executor._max_workers
        }
    
    def shutdown(self):
        """Cierra el optimizador y libera recursos"""
        self._shutdown = True
        self.executor.shutdown(wait=True)
        logger.info("🛑 ResponseOptimizer cerrado")


# Instancia global del optimizador
_global_response_optimizer = None


def get_response_optimizer() -> ResponseOptimizer:
    """Obtiene la instancia global del optimizador de respuestas"""
    global _global_response_optimizer
    if _global_response_optimizer is None:
        _global_response_optimizer = ResponseOptimizer()
    return _global_response_optimizer


def optimize_response_performance():
    """Función de conveniencia para optimizar respuestas"""
    optimizer = get_response_optimizer()
    return optimizer.get_performance_metrics()
