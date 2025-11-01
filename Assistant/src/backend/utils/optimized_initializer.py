"""
Inicializador optimizado que integra todas las optimizaciones de rendimiento
Aplica lazy loading, caché inteligente y optimizaciones de sistema
"""

import os
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

from src.backend.utils.performance_cache import get_global_cache
from src.backend.utils.performance_optimizer import get_performance_optimizer
from src.backend.utils.response_optimizer import get_response_optimizer

logger = logging.getLogger(__name__)


@dataclass
class InitializationConfig:
    """Configuración para inicialización optimizada"""
    # Lazy loading
    enable_lazy_loading: bool = True
    preload_critical_components: bool = True
    
    # Caching
    enable_intelligent_cache: bool = True
    cache_warmup: bool = True
    
    # Performance
    enable_system_optimizations: bool = True
    enable_response_optimization: bool = True
    
    # Monitoring
    enable_performance_monitoring: bool = True
    log_initialization_stats: bool = True


class OptimizedInitializer:
    """
    Inicializador optimizado que coordina todas las optimizaciones
    """
    
    def __init__(self, config: Optional[InitializationConfig] = None):
        self.config = config or InitializationConfig()
        self.initialization_stats = {}
        self.components_loaded = {}
        self._initialization_lock = threading.Lock()
        self._initialized = False
        
        logger.info("🚀 OptimizedInitializer creado")
    
    def initialize_system(self) -> Dict[str, Any]:
        """
        Inicializa el sistema con todas las optimizaciones
        
        Returns:
            Diccionario con estadísticas de inicialización
        """
        with self._initialization_lock:
            if self._initialized:
                logger.info("✅ Sistema ya inicializado")
                return self.initialization_stats
            
            start_time = time.time()
            logger.info("🚀 Iniciando inicialización optimizada del sistema...")
            
            try:
                # 1. Optimizaciones de sistema
                if self.config.enable_system_optimizations:
                    self._initialize_system_optimizations()
                
                # 2. Sistema de caché inteligente
                if self.config.enable_intelligent_cache:
                    self._initialize_intelligent_cache()
                
                # 3. Optimizador de respuestas
                if self.config.enable_response_optimization:
                    self._initialize_response_optimizer()
                
                # 4. Monitoreo de rendimiento
                if self.config.enable_performance_monitoring:
                    self._initialize_performance_monitoring()
                
                # 5. Carga de componentes críticos
                if self.config.preload_critical_components:
                    self._preload_critical_components()
                
                # 6. Warmup del caché
                if self.config.cache_warmup:
                    self._warmup_cache()
                
                # Calcular estadísticas
                initialization_time = time.time() - start_time
                self.initialization_stats = {
                    "initialization_time_seconds": initialization_time,
                    "components_loaded": len(self.components_loaded),
                    "optimizations_applied": self._count_optimizations(),
                    "cache_initialized": self.config.enable_intelligent_cache,
                    "monitoring_active": self.config.enable_performance_monitoring,
                    "lazy_loading_enabled": self.config.enable_lazy_loading
                }
                
                self._initialized = True
                
                if self.config.log_initialization_stats:
                    self._log_initialization_stats()
                
                logger.info(f"✅ Inicialización optimizada completada en {initialization_time:.2f}s")
                
                return self.initialization_stats
                
            except Exception as e:
                logger.error(f"❌ Error durante inicialización: {e}")
                raise
    
    def _initialize_system_optimizations(self):
        """Inicializa optimizaciones del sistema"""
        logger.info("🔧 Aplicando optimizaciones del sistema...")
        
        try:
            optimizer = get_performance_optimizer()
            optimizations = optimizer.apply_all_optimizations()
            
            total_optimizations = sum(len(ops) for ops in optimizations.values())
            self.components_loaded["system_optimizations"] = {
                "count": total_optimizations,
                "categories": list(optimizations.keys())
            }
            
            logger.info(f"✅ {total_optimizations} optimizaciones del sistema aplicadas")
            
        except Exception as e:
            logger.error(f"❌ Error aplicando optimizaciones del sistema: {e}")
    
    def _initialize_intelligent_cache(self):
        """Inicializa el sistema de caché inteligente"""
        logger.info("💾 Inicializando caché inteligente...")
        
        try:
            cache = get_global_cache()
            
            # Configurar caché para el sistema
            cache_stats = cache.get_stats()
            
            self.components_loaded["intelligent_cache"] = {
                "max_size": cache_stats["max_size"],
                "max_memory_mb": cache_stats["max_memory_mb"],
                "compression_enabled": True
            }
            
            logger.info("✅ Caché inteligente inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando caché inteligente: {e}")
    
    def _initialize_response_optimizer(self):
        """Inicializa el optimizador de respuestas"""
        logger.info("⚡ Inicializando optimizador de respuestas...")
        
        try:
            response_optimizer = get_response_optimizer()
            
            metrics = response_optimizer.get_performance_metrics()
            
            self.components_loaded["response_optimizer"] = {
                "streaming_enabled": metrics["config"]["streaming_enabled"],
                "batching_enabled": metrics["config"]["batching_enabled"],
                "async_enabled": metrics["config"]["async_enabled"],
                "max_concurrent": metrics["config"]["max_concurrent"]
            }
            
            logger.info("✅ Optimizador de respuestas inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando optimizador de respuestas: {e}")
    
    def _initialize_performance_monitoring(self):
        """Inicializa el monitoreo de rendimiento"""
        logger.info("📊 Iniciando monitoreo de rendimiento...")
        
        try:
            optimizer = get_performance_optimizer()
            optimizer.start_performance_monitoring()
            
            self.components_loaded["performance_monitoring"] = {
                "monitoring_active": True,
                "interval_seconds": 60
            }
            
            logger.info("✅ Monitoreo de rendimiento iniciado")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando monitoreo de rendimiento: {e}")
    
    def _preload_critical_components(self):
        """Precarga componentes críticos del sistema"""
        logger.info("🔄 Precargando componentes críticos...")
        
        try:
            # Precarregar configuración
            from src.backend.utils.unified_config import get_config
            config = get_config()
            self.components_loaded["unified_config"] = True
            
            # Precarregar logger
            from src.backend.utils.unified_logger import get_unified_logger
            logger_instance = get_unified_logger("optimized_initializer")
            self.components_loaded["unified_logger"] = True
            
            # Precarregar error handler
            from src.backend.utils.error_handler import get_error_handler
            error_handler = get_error_handler()
            self.components_loaded["error_handler"] = True
            
            logger.info("✅ Componentes críticos precargados")
            
        except Exception as e:
            logger.error(f"❌ Error precargando componentes críticos: {e}")
    
    def _warmup_cache(self):
        """Realiza warmup del caché con datos comunes"""
        logger.info("🔥 Realizando warmup del caché...")
        
        try:
            cache = get_global_cache()
            
            # Datos comunes para warmup
            warmup_data = {
                "system_info": {
                    "platform": os.name,
                    "cpu_count": os.cpu_count(),
                    "python_version": os.sys.version
                },
                "config_cache": {
                    "timestamp": time.time(),
                    "initialized": True
                }
            }
            
            # Agregar datos de warmup al caché
            for key, value in warmup_data.items():
                cache.set(key, value, ttl=3600)  # 1 hora
            
            self.components_loaded["cache_warmup"] = {
                "items_warmed": len(warmup_data),
                "warmup_time": time.time()
            }
            
            logger.info(f"✅ Warmup del caché completado: {len(warmup_data)} elementos")
            
        except Exception as e:
            logger.error(f"❌ Error en warmup del caché: {e}")
    
    def _count_optimizations(self) -> int:
        """Cuenta el total de optimizaciones aplicadas"""
        total = 0
        for component, data in self.components_loaded.items():
            if isinstance(data, dict) and "count" in data:
                total += data["count"]
            elif isinstance(data, bool) and data:
                total += 1
        return total
    
    def _log_initialization_stats(self):
        """Registra estadísticas de inicialización"""
        stats = self.initialization_stats
        
        logger.info("📊 Estadísticas de inicialización:")
        logger.info(f"  ⏱️  Tiempo total: {stats['initialization_time_seconds']:.2f}s")
        logger.info(f"  🔧 Componentes cargados: {stats['components_loaded']}")
        logger.info(f"  ⚡ Optimizaciones aplicadas: {stats['optimizations_applied']}")
        logger.info(f"  💾 Caché inicializado: {stats['cache_initialized']}")
        logger.info(f"  📊 Monitoreo activo: {stats['monitoring_active']}")
        logger.info(f"  🔄 Lazy loading: {stats['lazy_loading_enabled']}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del sistema
        
        Returns:
            Diccionario con estado del sistema
        """
        if not self._initialized:
            return {"status": "not_initialized"}
        
        try:
            # Obtener métricas de todos los componentes
            cache_stats = get_global_cache().get_stats()
            performance_summary = get_performance_optimizer().get_performance_summary()
            response_metrics = get_response_optimizer().get_performance_metrics()
            
            return {
                "status": "initialized",
                "initialization_stats": self.initialization_stats,
                "components_loaded": self.components_loaded,
                "cache_stats": cache_stats,
                "performance_summary": performance_summary,
                "response_metrics": response_metrics,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estado del sistema: {e}")
            return {"status": "error", "error": str(e)}
    
    def shutdown(self):
        """Cierra el sistema optimizado"""
        logger.info("🛑 Cerrando sistema optimizado...")
        
        try:
            # Cerrar optimizador de respuestas
            response_optimizer = get_response_optimizer()
            response_optimizer.shutdown()
            
            # Detener monitoreo de rendimiento
            performance_optimizer = get_performance_optimizer()
            performance_optimizer.stop_performance_monitoring()
            
            # Limpiar caché
            cache = get_global_cache()
            cache.clear()
            
            self._initialized = False
            logger.info("✅ Sistema optimizado cerrado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error cerrando sistema optimizado: {e}")


# Instancia global del inicializador
_global_initializer = None


def get_optimized_initializer() -> OptimizedInitializer:
    """Obtiene la instancia global del inicializador optimizado"""
    global _global_initializer
    if _global_initializer is None:
        _global_initializer = OptimizedInitializer()
    return _global_initializer


def initialize_optimized_system() -> Dict[str, Any]:
    """
    Función de conveniencia para inicializar el sistema optimizado
    
    Returns:
        Estadísticas de inicialización
    """
    initializer = get_optimized_initializer()
    return initializer.initialize_system()


def get_optimized_system_status() -> Dict[str, Any]:
    """
    Función de conveniencia para obtener el estado del sistema optimizado
    
    Returns:
        Estado del sistema
    """
    initializer = get_optimized_initializer()
    return initializer.get_system_status()
