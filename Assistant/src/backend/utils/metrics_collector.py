"""
Sistema de Métricas y Monitoring
=================================

Módulo para recolección, almacenamiento y reporte de métricas del sistema.

Características:
- Métricas de sistema (CPU, RAM, disco, red)
- Métricas de LLM (tokens/s, latencia, throughput)
- Métricas de API (requests/s, errores, latencia)
- Métricas de memoria (cache hits/misses, operaciones)
- Almacenamiento en ventana temporal
- Agregaciones y estadísticas
- Exportación en múltiples formatos

Autor: Assistant
Fecha: 2025
"""

import time
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from statistics import mean, median, stdev

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from src.backend.utils.unified_logger import get_unified_logger
    logger = get_unified_logger("METRICS")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("METRICS")


class MetricType(str, Enum):
    """Tipos de métricas"""
    COUNTER = "counter"           # Valor incremental (requests totales)
    GAUGE = "gauge"               # Valor actual (CPU %)
    HISTOGRAM = "histogram"       # Distribución de valores (latencias)
    SUMMARY = "summary"           # Resumen estadístico


class MetricCategory(str, Enum):
    """Categorías de métricas"""
    SYSTEM = "system"
    LLM = "llm"
    API = "api"
    MEMORY = "memory"
    KNOWLEDGE_BASE = "knowledge_base"
    CUSTOM = "custom"


@dataclass
class MetricPoint:
    """Punto de métrica individual"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "value": self.value,
            "labels": self.labels
        }


@dataclass
class Metric:
    """Métrica con historial"""
    name: str
    metric_type: MetricType
    category: MetricCategory
    description: str = ""
    unit: str = ""
    points: deque = field(default_factory=lambda: deque(maxlen=1000))

    def add_point(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Agrega un punto de métrica"""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels or {}
        )
        self.points.append(point)

    def get_current(self) -> Optional[float]:
        """Obtiene el valor actual (último punto)"""
        return self.points[-1].value if self.points else None

    def get_stats(self, window_seconds: Optional[float] = None) -> Dict[str, float]:
        """
        Calcula estadísticas de la métrica

        Args:
            window_seconds: Ventana temporal en segundos (None = todos los puntos)

        Returns:
            Diccionario con estadísticas
        """
        if not self.points:
            return {}

        # Filtrar por ventana temporal si se especifica
        now = time.time()
        values = [
            p.value for p in self.points
            if window_seconds is None or (now - p.timestamp) <= window_seconds
        ]

        if not values:
            return {}

        stats = {
            "count": len(values),
            "current": values[-1],
            "min": min(values),
            "max": max(values),
            "mean": mean(values),
            "median": median(values)
        }

        # Agregar desviación estándar si hay suficientes puntos
        if len(values) >= 2:
            stats["stdev"] = stdev(values)

        return stats

    def to_dict(self, include_points: bool = False) -> Dict[str, Any]:
        """Convierte a diccionario"""
        result = {
            "name": self.name,
            "type": self.metric_type.value,
            "category": self.category.value,
            "description": self.description,
            "unit": self.unit,
            "point_count": len(self.points),
            "current_value": self.get_current(),
            "stats": self.get_stats()
        }

        if include_points:
            result["points"] = [p.to_dict() for p in list(self.points)[-100:]]  # Últimos 100 puntos

        return result


class MetricsCollector:
    """
    Recolector central de métricas del sistema

    Recolecta, almacena y proporciona acceso a métricas de todos
    los componentes del sistema.
    """

    def __init__(self, collection_interval: float = 10.0):
        """
        Inicializa el recolector de métricas

        Args:
            collection_interval: Intervalo de recolección automática (segundos)
        """
        self.collection_interval = collection_interval
        self.metrics: Dict[str, Metric] = {}
        self.start_time = time.time()
        self.is_collecting = False

        logger.info(f"📊 Metrics Collector inicializado (interval: {collection_interval}s)")

    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        category: MetricCategory,
        description: str = "",
        unit: str = ""
    ) -> None:
        """
        Registra una nueva métrica

        Args:
            name: Nombre único de la métrica
            metric_type: Tipo de métrica
            category: Categoría de la métrica
            description: Descripción de la métrica
            unit: Unidad de medida
        """
        if name in self.metrics:
            logger.warning(f"⚠️ Métrica '{name}' ya registrada, sobrescribiendo")

        self.metrics[name] = Metric(
            name=name,
            metric_type=metric_type,
            category=category,
            description=description,
            unit=unit
        )

        logger.debug(f"✅ Métrica registrada: {name} ({metric_type.value})")

    def record(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Registra un valor de métrica

        Args:
            name: Nombre de la métrica
            value: Valor a registrar
            labels: Labels opcionales para el punto
        """
        if name not in self.metrics:
            logger.warning(f"⚠️ Métrica '{name}' no registrada, creando automáticamente")
            self.register_metric(
                name=name,
                metric_type=MetricType.GAUGE,
                category=MetricCategory.CUSTOM
            )

        self.metrics[name].add_point(value, labels)

    def increment(self, name: str, amount: float = 1.0) -> None:
        """
        Incrementa un contador

        Args:
            name: Nombre de la métrica
            amount: Cantidad a incrementar
        """
        current = self.get_current(name) or 0.0
        self.record(name, current + amount)

    def get_current(self, name: str) -> Optional[float]:
        """Obtiene el valor actual de una métrica"""
        metric = self.metrics.get(name)
        return metric.get_current() if metric else None

    def get_metric(self, name: str) -> Optional[Metric]:
        """Obtiene una métrica por nombre"""
        return self.metrics.get(name)

    def get_all_metrics(self, category: Optional[MetricCategory] = None) -> Dict[str, Metric]:
        """
        Obtiene todas las métricas, opcionalmente filtradas por categoría

        Args:
            category: Categoría para filtrar (None = todas)

        Returns:
            Diccionario de métricas
        """
        if category is None:
            return self.metrics.copy()

        return {
            name: metric
            for name, metric in self.metrics.items()
            if metric.category == category
        }

    def collect_system_metrics(self) -> None:
        """Recolecta métricas del sistema"""
        if not PSUTIL_AVAILABLE:
            return

        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.record("system.cpu.percent", cpu_percent)
            self.record("system.cpu.count", psutil.cpu_count() or 0)

            # Memoria
            mem = psutil.virtual_memory()
            self.record("system.memory.percent", mem.percent)
            self.record("system.memory.used_gb", mem.used / (1024**3))
            self.record("system.memory.available_gb", mem.available / (1024**3))

            # Disco
            disk = psutil.disk_usage('/')
            self.record("system.disk.percent", disk.percent)
            self.record("system.disk.used_gb", disk.used / (1024**3))
            self.record("system.disk.free_gb", disk.free / (1024**3))

            # Uptime
            uptime = time.time() - self.start_time
            self.record("system.uptime_seconds", uptime)

            # Load average (solo Unix)
            if hasattr(psutil, 'getloadavg'):
                load_avg = psutil.getloadavg()
                self.record("system.load_avg_1m", load_avg[0])
                self.record("system.load_avg_5m", load_avg[1])
                self.record("system.load_avg_15m", load_avg[2])

        except Exception as e:
            logger.error(f"❌ Error recolectando métricas del sistema: {e}")

    def get_summary(self, category: Optional[MetricCategory] = None) -> Dict[str, Any]:
        """
        Obtiene resumen de métricas

        Args:
            category: Categoría para filtrar (None = todas)

        Returns:
            Diccionario con resumen de métricas
        """
        metrics = self.get_all_metrics(category)

        summary = {
            "total_metrics": len(metrics),
            "collection_interval": self.collection_interval,
            "uptime_seconds": time.time() - self.start_time,
            "metrics": {}
        }

        for name, metric in metrics.items():
            summary["metrics"][name] = metric.to_dict()

        return summary

    def get_stats_summary(self, window_seconds: float = 60.0) -> Dict[str, Any]:
        """
        Obtiene resumen estadístico de métricas

        Args:
            window_seconds: Ventana temporal para estadísticas

        Returns:
            Resumen estadístico
        """
        summary = {
            "window_seconds": window_seconds,
            "timestamp": time.time(),
            "categories": {}
        }

        # Agrupar por categoría
        for category in MetricCategory:
            metrics = self.get_all_metrics(category)
            if not metrics:
                continue

            category_stats = {}
            for name, metric in metrics.items():
                stats = metric.get_stats(window_seconds)
                if stats:
                    category_stats[name] = stats

            if category_stats:
                summary["categories"][category.value] = category_stats

        return summary

    def export_prometheus(self) -> str:
        """
        Exporta métricas en formato Prometheus, incluyendo labels.

        - Genera HELP y TYPE por métrica.
        - Para cada métrica, emite la última muestra por combinación de labels.
          Esto permite series separadas en Prometheus según labels.
        - Sanea nombres ('.' -> '_') para cumplir el formato de Prometheus.
        - Para métricas de tipo HISTOGRAM, expone gauges derivados de cuantiles
          (p50/p95/p99) usando los puntos disponibles.
        """
        lines = []

        def _sanitize(name: str) -> str:
            return name.replace(".", "_")

        def _compute_quantile(values: List[float], q: float) -> Optional[float]:
            if not values:
                return None
            # Ordenar y seleccionar índice basado en percentil
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            # Índice de percentil utilizando método nearest-rank simplificado
            idx = int(round(q * (n - 1)))
            return sorted_vals[idx]

        for metric in self.metrics.values():
            sanitized_name = _sanitize(metric.name)

            # Header
            lines.append(f"# HELP {sanitized_name} {metric.description}")
            lines.append(f"# TYPE {sanitized_name} {metric.metric_type.value}")

            if not metric.points:
                # Sin puntos aún; emitir valor actual si existe sin labels
                current = metric.get_current()
                if current is not None:
                    lines.append(f"{sanitized_name} {current}")
                continue

            # Construir mapa de última muestra por combinación de labels
            latest_by_labels = {}
            values_for_quantiles: List[float] = []
            for p in list(metric.points):
                # Clave de labels determinista
                label_items = tuple(sorted((k, v) for k, v in (p.labels or {}).items()))
                latest_by_labels[label_items] = p
                values_for_quantiles.append(p.value)

            # Emitir cada serie con labels
            for label_items, point in latest_by_labels.items():
                labels_str = ""
                if label_items:
                    # Formato Prometheus: name{key="value",key2="value2"} value
                    labels_kv = ",".join([f'{k}="{v}"' for k, v in label_items])
                    labels_str = f"{{{labels_kv}}}"
                lines.append(f"{sanitized_name}{labels_str} {point.value}")

            # Derivados para HISTOGRAM: cuantiles como gauges
            if metric.metric_type == MetricType.HISTOGRAM and values_for_quantiles:
                # p50, p95, p99
                p50 = _compute_quantile(values_for_quantiles, 0.50)
                p95 = _compute_quantile(values_for_quantiles, 0.95)
                p99 = _compute_quantile(values_for_quantiles, 0.99)

                for suffix, val in [("_p50", p50), ("_p95", p95), ("_p99", p99)]:
                    if val is None:
                        continue
                    derived_name = f"{sanitized_name}{suffix}"
                    lines.append(f"# HELP {derived_name} {metric.description} (quantile {suffix[1:]})")
                    lines.append(f"# TYPE {derived_name} gauge")
                    lines.append(f"{derived_name} {val}")

        return "\n".join(lines)

    def export_json(self, include_points: bool = False) -> Dict[str, Any]:
        """
        Exporta métricas en formato JSON

        Args:
            include_points: Si incluir puntos históricos

        Returns:
            Diccionario con todas las métricas
        """
        return {
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self.start_time,
            "metrics": {
                name: metric.to_dict(include_points=include_points)
                for name, metric in self.metrics.items()
            }
        }

    def reset_metric(self, name: str) -> bool:
        """
        Resetea una métrica (limpia historial)

        Args:
            name: Nombre de la métrica

        Returns:
            True si se reseteó correctamente
        """
        metric = self.metrics.get(name)
        if metric:
            metric.points.clear()
            logger.info(f"🔄 Métrica '{name}' reseteada")
            return True
        return False

    def reset_all_metrics(self) -> None:
        """Resetea todas las métricas"""
        for metric in self.metrics.values():
            metric.points.clear()
        logger.info("🔄 Todas las métricas reseteadas")


# Métricas predefinidas del sistema
SYSTEM_METRICS = {
    # Sistema
    "system.cpu.percent": (MetricType.GAUGE, MetricCategory.SYSTEM, "CPU usage percentage", "%"),
    "system.cpu.count": (MetricType.GAUGE, MetricCategory.SYSTEM, "Number of CPU cores", "cores"),
    "system.memory.percent": (MetricType.GAUGE, MetricCategory.SYSTEM, "Memory usage percentage", "%"),
    "system.memory.used_gb": (MetricType.GAUGE, MetricCategory.SYSTEM, "Memory used", "GB"),
    "system.memory.available_gb": (MetricType.GAUGE, MetricCategory.SYSTEM, "Memory available", "GB"),
    "system.disk.percent": (MetricType.GAUGE, MetricCategory.SYSTEM, "Disk usage percentage", "%"),
    "system.disk.used_gb": (MetricType.GAUGE, MetricCategory.SYSTEM, "Disk used", "GB"),
    "system.disk.free_gb": (MetricType.GAUGE, MetricCategory.SYSTEM, "Disk free", "GB"),
    "system.uptime_seconds": (MetricType.GAUGE, MetricCategory.SYSTEM, "System uptime", "s"),

    # LLM
    "llm.queries_total": (MetricType.COUNTER, MetricCategory.LLM, "Total LLM queries", "queries"),
    "llm.tokens_generated": (MetricType.COUNTER, MetricCategory.LLM, "Tokens generated", "tokens"),
    "llm.latency_seconds": (MetricType.HISTOGRAM, MetricCategory.LLM, "Query latency", "s"),
    "llm.tokens_per_second": (MetricType.GAUGE, MetricCategory.LLM, "Generation speed", "tokens/s"),

    # API
    "api.requests_total": (MetricType.COUNTER, MetricCategory.API, "Total API requests", "requests"),
    "api.requests_success": (MetricType.COUNTER, MetricCategory.API, "Successful requests", "requests"),
    "api.requests_error": (MetricType.COUNTER, MetricCategory.API, "Failed requests", "requests"),
    "api.latency_seconds": (MetricType.HISTOGRAM, MetricCategory.API, "Request latency", "s"),

    # Memoria
    "memory.operations_total": (MetricType.COUNTER, MetricCategory.MEMORY, "Total memory operations", "ops"),
    "memory.cache_hits": (MetricType.COUNTER, MetricCategory.MEMORY, "Cache hits", "hits"),
    "memory.cache_misses": (MetricType.COUNTER, MetricCategory.MEMORY, "Cache misses", "misses"),
}


# Instancia global del recolector de métricas (lazy initialization)
_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(collection_interval: float = 10.0) -> MetricsCollector:
    """
    Obtiene la instancia global del metrics collector (singleton)

    Args:
        collection_interval: Intervalo de recolección (solo primera inicialización)

    Returns:
        MetricsCollector: Instancia global
    """
    global _global_metrics_collector

    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector(collection_interval)

        # Registrar métricas predefinidas
        for name, (metric_type, category, description, unit) in SYSTEM_METRICS.items():
            _global_metrics_collector.register_metric(
                name=name,
                metric_type=metric_type,
                category=category,
                description=description,
                unit=unit
            )

    return _global_metrics_collector
