"""
Sistema de caché inteligente para optimización de rendimiento
Incluye LRU cache, TTL, compresión y métricas de rendimiento
"""

import time
import threading
import hashlib
import json
import gzip
import pickle
from typing import Any, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import wraps
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Estadísticas del sistema de caché"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    compressions: int = 0
    total_size_bytes: int = 0
    last_cleanup: float = field(default_factory=time.time)
    
    @property
    def hit_rate(self) -> float:
        """Tasa de aciertos del caché"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    @property
    def total_requests(self) -> int:
        """Total de requests al caché"""
        return self.hits + self.misses


@dataclass
class CacheEntry:
    """Entrada del caché con metadatos"""
    value: Any
    timestamp: float
    access_count: int = 0
    compressed: bool = False
    size_bytes: int = 0
    
    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = self._estimate_size()
    
    def _estimate_size(self) -> int:
        """Estima el tamaño en bytes de la entrada"""
        try:
            if isinstance(self.value, str):
                return len(self.value.encode('utf-8'))
            elif isinstance(self.value, (dict, list)):
                return len(json.dumps(self.value).encode('utf-8'))
            else:
                return len(pickle.dumps(self.value))
        except:
            return 1024  # Estimación conservadora


class IntelligentCache:
    """
    Sistema de caché inteligente con:
    - LRU eviction
    - TTL (Time To Live)
    - Compresión automática
    - Métricas de rendimiento
    - Limpieza automática
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 500,
        default_ttl: int = 3600,  # 1 hora
        compression_threshold: int = 1024,  # 1KB
        cleanup_interval: int = 300,  # 5 minutos
        enable_compression: bool = True
    ):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.compression_threshold = compression_threshold
        self.cleanup_interval = cleanup_interval
        self.enable_compression = enable_compression
        
        # Cache storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = CacheStats()
        
        # Background cleanup
        self._last_cleanup = time.time()
        
        logger.info(f"🚀 IntelligentCache inicializado: max_size={max_size}, max_memory={max_memory_mb}MB")
    
    def _generate_key(self, key: Union[str, Any]) -> str:
        """Genera una clave hash para el caché"""
        if isinstance(key, str):
            return key
        
        try:
            # Para objetos complejos, usar hash de serialización
            key_str = json.dumps(key, sort_keys=True, default=str)
            return hashlib.md5(key_str.encode()).hexdigest()
        except:
            return str(hash(str(key)))
    
    def _compress_value(self, value: Any) -> Tuple[Any, bool]:
        """Comprime el valor si es beneficioso"""
        if not self.enable_compression:
            return value, False
        
        try:
            # Solo comprimir strings largos o datos serializables
            if isinstance(value, str) and len(value) > self.compression_threshold:
                compressed = gzip.compress(value.encode('utf-8'))
                if len(compressed) < len(value.encode('utf-8')) * 0.8:  # Solo si ahorra >20%
                    self.stats.compressions += 1
                    return compressed, True
            
            elif isinstance(value, (dict, list)) and len(str(value)) > self.compression_threshold:
                serialized = json.dumps(value).encode('utf-8')
                compressed = gzip.compress(serialized)
                if len(compressed) < len(serialized) * 0.8:
                    self.stats.compressions += 1
                    return compressed, True
                    
        except Exception as e:
            logger.warning(f"⚠️ Error comprimiendo valor: {e}")
        
        return value, False
    
    def _decompress_value(self, value: Any, compressed: bool) -> Any:
        """Descomprime el valor si está comprimido"""
        if not compressed:
            return value
        
        try:
            if isinstance(value, bytes):
                decompressed = gzip.decompress(value).decode('utf-8')
                # Intentar deserializar si es JSON
                try:
                    return json.loads(decompressed)
                except:
                    return decompressed
        except Exception as e:
            logger.warning(f"⚠️ Error descomprimiendo valor: {e}")
            return value
        
        return value
    
    def _cleanup_expired(self):
        """Limpia entradas expiradas"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if current_time - entry.timestamp > self.default_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self.stats.evictions += 1
        
        if expired_keys:
            logger.debug(f"🧹 Limpiadas {len(expired_keys)} entradas expiradas")
    
    def _evict_lru(self):
        """Elimina la entrada menos recientemente usada"""
        if not self._cache:
            return
        
        # LRU está al principio del OrderedDict
        key, entry = self._cache.popitem(last=False)
        self.stats.evictions += 1
        self.stats.total_size_bytes -= entry.size_bytes
        
        logger.debug(f"🗑️ Evictado LRU: {key[:8]}...")
    
    def _should_cleanup(self) -> bool:
        """Determina si es necesario hacer limpieza"""
        current_time = time.time()
        return (
            current_time - self._last_cleanup > self.cleanup_interval or
            len(self._cache) > self.max_size or
            self.stats.total_size_bytes > self.max_memory_bytes
        )
    
    def _perform_cleanup(self):
        """Realiza limpieza completa del caché"""
        with self._lock:
            self._cleanup_expired()
            
            # Evict LRU si excede límites
            while (
                len(self._cache) > self.max_size or 
                self.stats.total_size_bytes > self.max_memory_bytes
            ):
                self._evict_lru()
            
            self._last_cleanup = time.time()
    
    def get(self, key: Union[str, Any]) -> Optional[Any]:
        """Obtiene un valor del caché"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            # Limpieza automática si es necesario
            if self._should_cleanup():
                self._perform_cleanup()
            
            if cache_key not in self._cache:
                self.stats.misses += 1
                return None
            
            entry = self._cache[cache_key]
            
            # Verificar TTL
            if time.time() - entry.timestamp > self.default_ttl:
                del self._cache[cache_key]
                self.stats.misses += 1
                self.stats.evictions += 1
                return None
            
            # Mover al final (más reciente)
            self._cache.move_to_end(cache_key)
            entry.access_count += 1
            
            self.stats.hits += 1
            
            # Descomprimir si es necesario
            return self._decompress_value(entry.value, entry.compressed)
    
    def set(
        self, 
        key: Union[str, Any], 
        value: Any, 
        ttl: Optional[int] = None
    ) -> None:
        """Establece un valor en el caché"""
        cache_key = self._generate_key(key)
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Limpieza automática si es necesario
            if self._should_cleanup():
                self._perform_cleanup()
            
            # Comprimir si es beneficioso
            compressed_value, is_compressed = self._compress_value(value)
            
            # Crear entrada
            entry = CacheEntry(
                value=compressed_value,
                timestamp=time.time(),
                compressed=is_compressed
            )
            
            # Si ya existe, actualizar tamaño total
            if cache_key in self._cache:
                old_entry = self._cache[cache_key]
                self.stats.total_size_bytes -= old_entry.size_bytes
            
            # Agregar/actualizar entrada
            self._cache[cache_key] = entry
            self._cache.move_to_end(cache_key)  # Mover al final
            self.stats.total_size_bytes += entry.size_bytes
            
            # Evict si excede límites
            while (
                len(self._cache) > self.max_size or 
                self.stats.total_size_bytes > self.max_memory_bytes
            ):
                self._evict_lru()
    
    def delete(self, key: Union[str, Any]) -> bool:
        """Elimina una entrada del caché"""
        cache_key = self._generate_key(key)
        
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                del self._cache[cache_key]
                self.stats.total_size_bytes -= entry.size_bytes
                self.stats.evictions += 1
                return True
            return False
    
    def clear(self) -> None:
        """Limpia todo el caché"""
        with self._lock:
            self._cache.clear()
            self.stats = CacheStats()
            self._last_cleanup = time.time()
            logger.info("🧹 Caché limpiado completamente")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        with self._lock:
            return {
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "hit_rate": f"{self.stats.hit_rate:.2f}%",
                "evictions": self.stats.evictions,
                "compressions": self.stats.compressions,
                "total_requests": self.stats.total_requests,
                "current_size": len(self._cache),
                "max_size": self.max_size,
                "memory_usage_mb": self.stats.total_size_bytes / (1024 * 1024),
                "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                "last_cleanup": time.time() - self._last_cleanup
            }
    
    def __len__(self) -> int:
        """Tamaño actual del caché"""
        return len(self._cache)
    
    def __contains__(self, key: Union[str, Any]) -> bool:
        """Verifica si una clave existe en el caché"""
        return self.get(key) is not None


# Instancia global del caché inteligente
_global_cache = IntelligentCache(
    max_size=2000,
    max_memory_mb=1000,
    default_ttl=7200,  # 2 horas
    compression_threshold=512,  # 512 bytes
    cleanup_interval=180,  # 3 minutos
    enable_compression=True
)


def get_global_cache() -> IntelligentCache:
    """Obtiene la instancia global del caché inteligente"""
    return _global_cache


def cache_result(
    ttl: int = 3600,
    cache_key: Optional[Union[str, callable]] = None,
    use_global: bool = True
):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        ttl: Tiempo de vida en segundos
        cache_key: Clave personalizada o función para generar clave
        use_global: Si usar el caché global o crear uno local
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave de caché
            if cache_key:
                if callable(cache_key):
                    key = cache_key(*args, **kwargs)
                else:
                    key = cache_key
            else:
                # Clave basada en función y argumentos
                key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Obtener caché
            cache = _global_cache if use_global else IntelligentCache()
            
            # Intentar obtener del caché
            result = cache.get(key)
            if result is not None:
                logger.debug(f"🎯 Cache hit para {func.__name__}")
                return result
            
            # Ejecutar función y cachear resultado
            logger.debug(f"🔄 Cache miss para {func.__name__}, ejecutando...")
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Funciones de utilidad para métricas
def log_cache_stats():
    """Registra estadísticas del caché global"""
    stats = _global_cache.get_stats()
    logger.info(f"📊 Cache Stats: {stats['hit_rate']} hit rate, "
               f"{stats['current_size']}/{stats['max_size']} entries, "
               f"{stats['memory_usage_mb']:.1f}MB/{stats['max_memory_mb']:.1f}MB")


def optimize_cache_performance():
    """Optimiza el rendimiento del caché global"""
    _global_cache._perform_cleanup()
    log_cache_stats()
