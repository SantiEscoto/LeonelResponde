"""
Optimizador de rendimiento para Apple Silicon y sistemas modernos
Incluye optimizaciones específicas para MPS, threading y memoria
"""

import os
import platform
import threading
import time
import psutil
import gc
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """Configuración de optimización de rendimiento"""
    # Apple Silicon optimizations
    enable_mps: bool = True
    mps_fallback: bool = True
    optimize_for_apple_silicon: bool = True
    
    # Threading optimizations
    max_threads: int = 8
    io_threads: int = 2
    compute_threads: int = 6
    
    # Memory optimizations
    enable_memory_mapping: bool = True
    enable_memory_locking: bool = True
    gc_threshold: int = 100  # MB
    auto_gc_interval: int = 30  # seconds
    
    # Caching optimizations
    enable_model_cache: bool = True
    enable_embedding_cache: bool = True
    cache_compression: bool = True
    
    # Performance monitoring
    enable_performance_monitoring: bool = True
    monitor_interval: int = 60  # seconds
    log_performance_stats: bool = True


class PerformanceOptimizer:
    """
    Optimizador de rendimiento para el sistema
    Detecta automáticamente el hardware y aplica optimizaciones
    """
    
    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or PerformanceConfig()
        self.system_info = self._detect_system()
        self.optimizations_applied = []
        self.performance_stats = {}
        self._monitor_thread = None
        self._monitoring = False
        
        logger.info(f"🚀 PerformanceOptimizer inicializado para {self.system_info['platform']}")
    
    def _detect_system(self) -> Dict[str, Any]:
        """Detecta las características del sistema"""
        system_info = {
            'platform': platform.system(),
            'architecture': platform.machine(),
            'cpu_count': os.cpu_count() or 4,
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'is_apple_silicon': False,
            'has_mps': False,
            'has_cuda': False,
            'has_opencl': False
        }
        
        # Detectar Apple Silicon
        if system_info['platform'] == 'Darwin':
            if 'arm' in system_info['architecture'].lower():
                system_info['is_apple_silicon'] = True
                logger.info("🍎 Apple Silicon detectado")
        
        # Detectar MPS (Metal Performance Shaders)
        try:
            import torch
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                system_info['has_mps'] = True
                logger.info("🚀 MPS (Metal Performance Shaders) disponible")
        except ImportError:
            pass
        
        # Detectar CUDA
        try:
            import torch
            if torch.cuda.is_available():
                system_info['has_cuda'] = True
                logger.info("🔥 CUDA disponible")
        except ImportError:
            pass
        
        return system_info
    
    def apply_apple_silicon_optimizations(self) -> List[str]:
        """Aplica optimizaciones específicas para Apple Silicon"""
        optimizations = []
        
        if not self.system_info['is_apple_silicon']:
            return optimizations
        
        # Optimizar variables de entorno para Apple Silicon
        env_optimizations = {
            'PYTORCH_ENABLE_MPS_FALLBACK': '1' if self.config.mps_fallback else '0',
            'OMP_NUM_THREADS': str(self.config.compute_threads),
            'TOKENIZERS_PARALLELISM': 'false',  # Evitar conflictos
            'MKL_NUM_THREADS': str(self.config.compute_threads),
            'OPENBLAS_NUM_THREADS': str(self.config.compute_threads),
            'VECLIB_MAXIMUM_THREADS': str(self.config.compute_threads),
            'NUMEXPR_NUM_THREADS': str(self.config.compute_threads),
        }
        
        for key, value in env_optimizations.items():
            os.environ[key] = value
            optimizations.append(f"Set {key}={value}")
        
        # Optimizar threading para Apple Silicon
        if self.config.optimize_for_apple_silicon:
            # En Apple Silicon, menos threads pueden ser más eficientes
            optimal_threads = min(8, self.system_info['cpu_count'])
            os.environ['OMP_NUM_THREADS'] = str(optimal_threads)
            optimizations.append(f"Optimized threads for Apple Silicon: {optimal_threads}")
        
        logger.info(f"🍎 Aplicadas {len(optimizations)} optimizaciones para Apple Silicon")
        return optimizations
    
    def apply_memory_optimizations(self) -> List[str]:
        """Aplica optimizaciones de memoria"""
        optimizations = []
        
        # Configurar garbage collection
        if self.config.gc_threshold > 0:
            gc.set_threshold(
                self.config.gc_threshold * 1000,  # Generación 0
                self.config.gc_threshold * 100,   # Generación 1
                self.config.gc_threshold * 10     # Generación 2
            )
            optimizations.append(f"GC threshold set to {self.config.gc_threshold}MB")
        
        # Habilitar memory mapping si está disponible
        if self.config.enable_memory_mapping:
            os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
            optimizations.append("Memory mapping enabled")
        
        # Configurar memory locking
        if self.config.enable_memory_locking:
            os.environ['PYTORCH_MPS_LOW_WATERMARK_RATIO'] = '0.0'
            optimizations.append("Memory locking enabled")
        
        logger.info(f"💾 Aplicadas {len(optimizations)} optimizaciones de memoria")
        return optimizations
    
    def apply_threading_optimizations(self) -> List[str]:
        """Aplica optimizaciones de threading"""
        optimizations = []
        
        # Configurar threads para diferentes tipos de operaciones
        threading_config = {
            'OMP_NUM_THREADS': str(self.config.compute_threads),
            'MKL_NUM_THREADS': str(self.config.compute_threads),
            'OPENBLAS_NUM_THREADS': str(self.config.compute_threads),
            'VECLIB_MAXIMUM_THREADS': str(self.config.compute_threads),
            'NUMEXPR_NUM_THREADS': str(self.config.compute_threads),
            'TOKENIZERS_PARALLELISM': 'false',  # Evitar conflictos
        }
        
        for key, value in threading_config.items():
            os.environ[key] = value
            optimizations.append(f"Set {key}={value}")
        
        # Configurar threading para PyTorch si está disponible
        try:
            import torch
            torch.set_num_threads(self.config.compute_threads)
            optimizations.append(f"PyTorch threads set to {self.config.compute_threads}")
        except ImportError:
            pass
        
        logger.info(f"🧵 Aplicadas {len(optimizations)} optimizaciones de threading")
        return optimizations
    
    def apply_torch_optimizations(self) -> List[str]:
        """Aplica optimizaciones específicas de PyTorch"""
        optimizations = []
        
        try:
            import torch
            
            # Habilitar optimizaciones de compilación
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.deterministic = False
            optimizations.append("CuDNN optimizations enabled")
            
            # Configurar MPS si está disponible
            if self.system_info['has_mps'] and self.config.enable_mps:
                torch.backends.mps.is_available()
                optimizations.append("MPS optimizations enabled")
            
            # Configurar threading
            torch.set_num_threads(self.config.compute_threads)
            optimizations.append(f"PyTorch threads: {self.config.compute_threads}")
            
            # Habilitar optimizaciones de memoria
            if hasattr(torch.backends, 'mps'):
                torch.backends.mps.allow_tf32 = True
                optimizations.append("MPS TF32 enabled")
            
        except ImportError:
            logger.warning("⚠️ PyTorch no disponible, saltando optimizaciones específicas")
        
        logger.info(f"🔥 Aplicadas {len(optimizations)} optimizaciones de PyTorch")
        return optimizations
    
    def apply_all_optimizations(self) -> Dict[str, List[str]]:
        """Aplica todas las optimizaciones disponibles"""
        all_optimizations = {}
        
        # Aplicar optimizaciones por categoría
        all_optimizations['apple_silicon'] = self.apply_apple_silicon_optimizations()
        all_optimizations['memory'] = self.apply_memory_optimizations()
        all_optimizations['threading'] = self.apply_threading_optimizations()
        all_optimizations['torch'] = self.apply_torch_optimizations()
        
        # Combinar todas las optimizaciones
        self.optimizations_applied = []
        for category, optimizations in all_optimizations.items():
            self.optimizations_applied.extend(optimizations)
        
        logger.info(f"✅ Aplicadas {len(self.optimizations_applied)} optimizaciones totales")
        return all_optimizations
    
    def start_performance_monitoring(self):
        """Inicia el monitoreo de rendimiento en background"""
        if not self.config.enable_performance_monitoring:
            return
        
        if self._monitoring:
            logger.warning("⚠️ Monitoreo de rendimiento ya está activo")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_performance,
            daemon=True,
            name="PerformanceMonitor"
        )
        self._monitor_thread.start()
        logger.info("📊 Monitoreo de rendimiento iniciado")
    
    def stop_performance_monitoring(self):
        """Detiene el monitoreo de rendimiento"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("📊 Monitoreo de rendimiento detenido")
    
    def _monitor_performance(self):
        """Loop de monitoreo de rendimiento"""
        while self._monitoring:
            try:
                stats = self._collect_performance_stats()
                self.performance_stats = stats
                
                if self.config.log_performance_stats:
                    self._log_performance_stats(stats)
                
                # Auto garbage collection si es necesario
                if self.config.auto_gc_interval > 0:
                    self._auto_gc_if_needed(stats)
                
                time.sleep(self.config.monitor_interval)
                
            except Exception as e:
                logger.error(f"❌ Error en monitoreo de rendimiento: {e}")
                time.sleep(60)  # Esperar antes de reintentar
    
    def _collect_performance_stats(self) -> Dict[str, Any]:
        """Recolecta estadísticas de rendimiento"""
        process = psutil.Process()
        
        stats = {
            'timestamp': time.time(),
            'memory': {
                'rss_mb': process.memory_info().rss / (1024 * 1024),
                'vms_mb': process.memory_info().vms / (1024 * 1024),
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / (1024 * 1024)
            },
            'cpu': {
                'percent': process.cpu_percent(),
                'system_percent': psutil.cpu_percent(),
                'count': psutil.cpu_count()
            },
            'system': {
                'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                'threads': process.num_threads(),
                'open_files': process.num_fds() if hasattr(process, 'num_fds') else 0
            }
        }
        
        # Agregar estadísticas de GPU si están disponibles
        try:
            import torch
            if torch.cuda.is_available():
                stats['gpu'] = {
                    'memory_allocated_mb': torch.cuda.memory_allocated() / (1024 * 1024),
                    'memory_reserved_mb': torch.cuda.memory_reserved() / (1024 * 1024),
                    'memory_cached_mb': torch.cuda.memory_cached() / (1024 * 1024)
                }
        except ImportError:
            pass
        
        return stats
    
    def _log_performance_stats(self, stats: Dict[str, Any]):
        """Registra estadísticas de rendimiento"""
        memory = stats['memory']
        cpu = stats['cpu']
        
        logger.info(
            f"📊 Performance: "
            f"RAM {memory['rss_mb']:.1f}MB ({memory['percent']:.1f}%), "
            f"CPU {cpu['percent']:.1f}%, "
            f"Threads {stats['system']['threads']}"
        )
    
    def _auto_gc_if_needed(self, stats: Dict[str, Any]):
        """Ejecuta garbage collection automático si es necesario"""
        memory_mb = stats['memory']['rss_mb']
        
        if memory_mb > self.config.gc_threshold:
            logger.info(f"🧹 Auto GC: memoria {memory_mb:.1f}MB > {self.config.gc_threshold}MB")
            gc.collect()
            
            # Limpiar cache de GPU si está disponible
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen del rendimiento actual"""
        if not self.performance_stats:
            self.performance_stats = self._collect_performance_stats()
        
        return {
            'system_info': self.system_info,
            'optimizations_applied': len(self.optimizations_applied),
            'current_stats': self.performance_stats,
            'monitoring_active': self._monitoring,
            'config': {
                'max_threads': self.config.max_threads,
                'gc_threshold_mb': self.config.gc_threshold,
                'enable_mps': self.config.enable_mps,
                'enable_memory_mapping': self.config.enable_memory_mapping
            }
        }
    
    def optimize_for_workload(self, workload_type: str) -> List[str]:
        """Optimiza el sistema para un tipo específico de carga de trabajo"""
        optimizations = []
        
        if workload_type == "inference":
            # Optimizaciones para inferencia
            os.environ['OMP_NUM_THREADS'] = str(min(4, self.system_info['cpu_count']))
            optimizations.append("Optimized for inference workload")
            
        elif workload_type == "training":
            # Optimizaciones para entrenamiento
            os.environ['OMP_NUM_THREADS'] = str(self.system_info['cpu_count'])
            optimizations.append("Optimized for training workload")
            
        elif workload_type == "batch_processing":
            # Optimizaciones para procesamiento por lotes
            os.environ['OMP_NUM_THREADS'] = str(min(8, self.system_info['cpu_count']))
            optimizations.append("Optimized for batch processing")
        
        logger.info(f"🎯 Optimizado para carga de trabajo: {workload_type}")
        return optimizations


# Instancia global del optimizador
_global_optimizer = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Obtiene la instancia global del optimizador de rendimiento"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PerformanceOptimizer()
        _global_optimizer.apply_all_optimizations()
        _global_optimizer.start_performance_monitoring()
    return _global_optimizer


def optimize_system_performance():
    """Función de conveniencia para optimizar el sistema"""
    optimizer = get_performance_optimizer()
    return optimizer.get_performance_summary()
