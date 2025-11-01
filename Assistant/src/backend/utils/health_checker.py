"""
Sistema de Health Checks Avanzado
==================================

Módulo para verificación completa de salud del sistema, monitoreo de componentes
críticos y detección temprana de problemas.

Características:
- Verificación de componentes (LLM, memoria, base de conocimiento)
- Monitoreo de recursos del sistema (CPU, RAM, disco)
- Sistema de alertas configurables
- Historial de health checks
- Métricas de disponibilidad
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from src.backend.utils.unified_logger import get_unified_logger
    logger = get_unified_logger("HEALTH")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("HEALTH")


class HealthStatus(str, Enum):
    """Estados posibles de salud del sistema"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    """Tipos de componentes del sistema"""
    LLM = "llm"
    MEMORY = "memory"
    KNOWLEDGE_BASE = "knowledge_base"
    API = "api"
    SYSTEM = "system"
    STORAGE = "storage"


@dataclass
class ComponentHealth:
    """Estado de salud de un componente"""
    name: str
    component_type: ComponentType
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        return {
            "name": self.name,
            "type": self.component_type.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "last_check": self.last_check,
            "last_check_iso": datetime.fromtimestamp(self.last_check).isoformat()
        }


@dataclass
class SystemHealth:
    """Estado de salud completo del sistema"""
    overall_status: HealthStatus
    components: Dict[str, ComponentHealth]
    resources: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    timestamp: float = field(default_factory=time.time)
    uptime: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        return {
            "overall_status": self.overall_status.value,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "resources": self.resources,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "uptime_seconds": self.uptime
        }


class HealthChecker:
    """
    Sistema avanzado de health checks

    Verifica la salud de todos los componentes del sistema y monitorea recursos.
    """

    def __init__(self, alert_thresholds: Optional[Dict[str, float]] = None, critical_components: Optional[List[str]] = None, component_severity: Optional[Dict[str, str]] = None):
        """
        Inicializa el health checker

        Args:
            alert_thresholds: Umbrales para alertas (CPU, memoria, disco)
            critical_components: Lista de componentes críticos que si están UNHEALTHY degradan el sistema
            component_severity: Overrides por componente para tratar estados (e.g., {'knowledge_base': 'healthy_if_degraded'})
        """
        self.start_time = time.time()
        self.alert_thresholds = alert_thresholds or {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time": 5.0  # segundos
        }
        self.check_history: List[SystemHealth] = []
        self.max_history = 100
        self.component_checkers: Dict[str, Callable] = {}
        self.critical_components: List[str] = critical_components or ['llm', 'memory']
        # Valores posibles para component_severity[name]: 'healthy_if_degraded', 'unhealthy_if_degraded'
        self.component_severity: Dict[str, str] = component_severity or {}

        logger.info("🏥 Health Checker inicializado")
        logger.info(f"📊 Umbrales de alerta: {self.alert_thresholds}")

    def register_component_checker(
        self,
        component_name: str,
        checker_func: Callable[[], ComponentHealth]
    ) -> None:
        """
        Registra una función de verificación para un componente

        Args:
            component_name: Nombre del componente
            checker_func: Función que retorna ComponentHealth
        """
        self.component_checkers[component_name] = checker_func
        logger.info(f"✅ Checker registrado para componente: {component_name}")

    def check_system_health(self, components: Optional[Dict[str, Any]] = None) -> SystemHealth:
        """
        Realiza verificación completa de salud del sistema

        Args:
            components: Diccionario con componentes del sistema a verificar

        Returns:
            SystemHealth con el estado completo del sistema
        """
        errors = []
        warnings = []
        component_statuses = {}

        # 1. Verificar componentes críticos
        if components:
            # Verificar LLM
            llm_health = self._check_llm_component(components.get('llm_manager'))
            component_statuses['llm'] = llm_health
            if llm_health.status == HealthStatus.UNHEALTHY:
                errors.append(llm_health.message)
            elif llm_health.status == HealthStatus.DEGRADED:
                warnings.append(llm_health.message)

            # Verificar memoria
            memory_health = self._check_memory_component(components.get('memory_manager'))
            component_statuses['memory'] = memory_health
            if memory_health.status == HealthStatus.UNHEALTHY:
                errors.append(memory_health.message)
            elif memory_health.status == HealthStatus.DEGRADED:
                warnings.append(memory_health.message)

            # Verificar base de conocimiento
            kb_health = self._check_knowledge_base_component(components.get('knowledge_base'))
            component_statuses['knowledge_base'] = kb_health
            if kb_health.status == HealthStatus.UNHEALTHY:
                errors.append(kb_health.message)
            elif kb_health.status == HealthStatus.DEGRADED:
                warnings.append(kb_health.message)

            # Verificar componentes arbitrarios adicionales
            for name, comp in components.items():
                if name in {'llm_manager', 'memory_manager', 'knowledge_base'}:
                    continue
                try:
                    status_info = comp.get_status() if hasattr(comp, 'get_status') else {}
                    status_text = str(status_info.get('status', 'ok')).lower()
                    if status_text in {'ok', 'healthy', 'ready', 'operational'}:
                        status = HealthStatus.HEALTHY
                    elif status_text in {'degraded', 'warning'}:
                        status = HealthStatus.DEGRADED
                    elif status_text in {'error', 'unhealthy', 'fail', 'failed'}:
                        status = HealthStatus.UNHEALTHY
                    else:
                        # Si no hay indicador claro, considerar degradado pero incluir detalles
                        status = HealthStatus.DEGRADED

                    component_statuses[name] = ComponentHealth(
                        name=name,
                        component_type=ComponentType.SYSTEM,
                        status=status,
                        message="Custom component check",
                        details=status_info
                    )
                    if status == HealthStatus.UNHEALTHY:
                        errors.append(f"{name} reported unhealthy")
                    elif status == HealthStatus.DEGRADED:
                        warnings.append(f"{name} reported degraded")
                except Exception as e:
                    component_statuses[name] = ComponentHealth(
                        name=name,
                        component_type=ComponentType.SYSTEM,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Error verificando {name}: {str(e)}"
                    )
                    errors.append(f"Error verificando {name}: {str(e)}")

        # 2. Verificar checkers personalizados
        for name, checker_func in self.component_checkers.items():
            try:
                health = checker_func()
                component_statuses[name] = health
                if health.status == HealthStatus.UNHEALTHY:
                    errors.append(health.message)
                elif health.status == HealthStatus.DEGRADED:
                    warnings.append(health.message)
            except Exception as e:
                logger.error(f"❌ Error verificando componente {name}: {e}")
                component_statuses[name] = ComponentHealth(
                    name=name,
                    component_type=ComponentType.SYSTEM,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Error en verificación: {str(e)}"
                )
                errors.append(f"Error verificando {name}: {str(e)}")

        # 3. Verificar recursos del sistema
        resources = self._check_system_resources()

        # Verificar umbrales de recursos
        if PSUTIL_AVAILABLE:
            if resources.get('cpu_percent', 0) > self.alert_thresholds['cpu_percent']:
                warnings.append(
                    f"CPU usage high: {resources['cpu_percent']:.1f}% "
                    f"(threshold: {self.alert_thresholds['cpu_percent']}%)"
                )

            if resources.get('memory_percent', 0) > self.alert_thresholds['memory_percent']:
                warnings.append(
                    f"Memory usage high: {resources['memory_percent']:.1f}% "
                    f"(threshold: {self.alert_thresholds['memory_percent']}%)"
                )

            if resources.get('disk_percent', 0) > self.alert_thresholds['disk_percent']:
                warnings.append(
                    f"Disk usage high: {resources['disk_percent']:.1f}% "
                    f"(threshold: {self.alert_thresholds['disk_percent']}%)"
                )

        # 4. Determinar estado general del sistema
        overall_status = self._determine_overall_status(component_statuses, errors, warnings)

        # 5. Crear objeto SystemHealth
        system_health = SystemHealth(
            overall_status=overall_status,
            components=component_statuses,
            resources=resources,
            errors=errors,
            warnings=warnings,
            timestamp=time.time(),
            uptime=time.time() - self.start_time
        )

        # 6. Guardar en historial
        self._save_to_history(system_health)

        # 7. Log del resultado
        self._log_health_check(system_health)

        return system_health

    def _check_llm_component(self, llm_manager: Optional[Any]) -> ComponentHealth:
        """Verifica el estado del LLM"""
        if not llm_manager:
            return ComponentHealth(
                name="LLM Manager",
                component_type=ComponentType.LLM,
                status=HealthStatus.UNHEALTHY,
                message="LLM Manager not initialized"
            )

        try:
            # Verificar si el modelo está cargado
            is_loaded = getattr(llm_manager, 'is_loaded', False)
            model_path = getattr(llm_manager, 'model_path', 'unknown')

            if is_loaded:
                # Verificar si el modelo responde
                try:
                    status_info = llm_manager.get_status() if hasattr(llm_manager, 'get_status') else {}
                    return ComponentHealth(
                        name="LLM Manager",
                        component_type=ComponentType.LLM,
                        status=HealthStatus.HEALTHY,
                        message="LLM is loaded and operational",
                        details={
                            "model_path": model_path,
                            "is_loaded": is_loaded,
                            **status_info
                        }
                    )
                except Exception as e:
                    return ComponentHealth(
                        name="LLM Manager",
                        component_type=ComponentType.LLM,
                        status=HealthStatus.DEGRADED,
                        message=f"LLM loaded but degraded: {str(e)}",
                        details={"model_path": model_path, "error": str(e)}
                    )
            else:
                return ComponentHealth(
                    name="LLM Manager",
                    component_type=ComponentType.LLM,
                    status=HealthStatus.DEGRADED,
                    message="LLM not loaded (lazy loading enabled)",
                    details={"model_path": model_path, "is_loaded": False}
                )
        except Exception as e:
            return ComponentHealth(
                name="LLM Manager",
                component_type=ComponentType.LLM,
                status=HealthStatus.UNHEALTHY,
                message=f"Error checking LLM: {str(e)}"
            )

    def _check_memory_component(self, memory_manager: Optional[Any]) -> ComponentHealth:
        """Verifica el estado del gestor de memoria"""
        if not memory_manager:
            return ComponentHealth(
                name="Memory Manager",
                component_type=ComponentType.MEMORY,
                status=HealthStatus.UNHEALTHY,
                message="Memory Manager not initialized"
            )

        try:
            # Obtener estado del memory manager
            status_info = memory_manager.get_status() if hasattr(memory_manager, 'get_status') else {}

            return ComponentHealth(
                name="Memory Manager",
                component_type=ComponentType.MEMORY,
                status=HealthStatus.HEALTHY,
                message="Memory Manager operational",
                details=status_info
            )
        except Exception as e:
            return ComponentHealth(
                name="Memory Manager",
                component_type=ComponentType.MEMORY,
                status=HealthStatus.DEGRADED,
                message=f"Memory Manager degraded: {str(e)}"
            )

    def _check_knowledge_base_component(self, knowledge_base: Optional[Any]) -> ComponentHealth:
        """Verifica el estado de la base de conocimiento"""
        if not knowledge_base:
            return ComponentHealth(
                name="Knowledge Base",
                component_type=ComponentType.KNOWLEDGE_BASE,
                status=HealthStatus.DEGRADED,
                message="Knowledge Base not initialized (optional component)"
            )

        try:
            # Obtener estado de la base de conocimiento
            status_info = knowledge_base.get_status() if hasattr(knowledge_base, 'get_status') else {}

            return ComponentHealth(
                name="Knowledge Base",
                component_type=ComponentType.KNOWLEDGE_BASE,
                status=HealthStatus.HEALTHY,
                message="Knowledge Base operational",
                details=status_info
            )
        except Exception as e:
            return ComponentHealth(
                name="Knowledge Base",
                component_type=ComponentType.KNOWLEDGE_BASE,
                status=HealthStatus.DEGRADED,
                message=f"Knowledge Base degraded: {str(e)}"
            )

    def _check_system_resources(self) -> Dict[str, Any]:
        """Verifica recursos del sistema"""
        resources = {
            "psutil_available": PSUTIL_AVAILABLE,
            "timestamp": time.time()
        }

        if not PSUTIL_AVAILABLE:
            resources["error"] = "psutil not available - install for detailed metrics"
            return resources

        try:
            # CPU
            resources["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            resources["cpu_count"] = psutil.cpu_count()

            # Memoria
            mem = psutil.virtual_memory()
            resources["memory_percent"] = mem.percent
            resources["memory_total_gb"] = mem.total / (1024**3)
            resources["memory_available_gb"] = mem.available / (1024**3)
            resources["memory_used_gb"] = mem.used / (1024**3)

            # Disco
            disk = psutil.disk_usage('/')
            resources["disk_percent"] = disk.percent
            resources["disk_total_gb"] = disk.total / (1024**3)
            resources["disk_free_gb"] = disk.free / (1024**3)
            resources["disk_used_gb"] = disk.used / (1024**3)

            # Load average (solo en Unix)
            if hasattr(psutil, 'getloadavg'):
                load_avg = psutil.getloadavg()
                resources["load_average_1m"] = load_avg[0]
                resources["load_average_5m"] = load_avg[1]
                resources["load_average_15m"] = load_avg[2]

        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas del sistema: {e}")
            resources["error"] = str(e)

        return resources

    def _determine_overall_status(
        self,
        components: Dict[str, ComponentHealth],
        errors: List[str],
        warnings: List[str]
    ) -> HealthStatus:
        """Determina el estado general del sistema basado en componentes"""
        if not components:
            # Sin componentes registrados: determina estado por errores/advertencias o saludable
            if len(errors) >= 2:
                return HealthStatus.CRITICAL
            elif len(errors) >= 1:
                return HealthStatus.UNHEALTHY
            elif len(warnings) >= 1:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY

        # Ajustes de severidad por componente (escalar DEGRADED a HEALTHY o UNHEALTHY)
        adjusted_components: Dict[str, HealthStatus] = {}
        for name, comp in components.items():
            status = comp.status
            override = self.component_severity.get(name)
            if status == HealthStatus.DEGRADED and override == 'healthy_if_degraded':
                status = HealthStatus.HEALTHY
            elif status == HealthStatus.DEGRADED and override == 'unhealthy_if_degraded':
                status = HealthStatus.UNHEALTHY
            adjusted_components[name] = status

        # Contar estados
        statuses = list(adjusted_components.values())

        # Si algún componente crítico está unhealthy, el sistema está unhealthy
        for comp_name in self.critical_components:
            if comp_name in adjusted_components and adjusted_components[comp_name] == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY

        # Si hay errores críticos
        if len(errors) >= 2:
            return HealthStatus.CRITICAL
        elif len(errors) >= 1:
            return HealthStatus.UNHEALTHY

        # Si hay componentes degradados o warnings
        if HealthStatus.DEGRADED in statuses or len(warnings) >= 3:
            return HealthStatus.DEGRADED
        elif len(warnings) >= 1:
            return HealthStatus.DEGRADED

        # Si todos están healthy
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY

        return HealthStatus.DEGRADED

    def _save_to_history(self, health: SystemHealth) -> None:
        """Guarda el health check en el historial"""
        self.check_history.append(health)

        # Mantener solo los últimos N checks
        if len(self.check_history) > self.max_history:
            self.check_history = self.check_history[-self.max_history:]

    def _log_health_check(self, health: SystemHealth) -> None:
        """Log del resultado del health check"""
        status_emoji = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNHEALTHY: "❌",
            HealthStatus.CRITICAL: "🚨",
            HealthStatus.UNKNOWN: "❓"
        }

        emoji = status_emoji.get(health.overall_status, "❓")
        logger.info(
            f"{emoji} Health Check: {health.overall_status.value.upper()} "
            f"({len(health.components)} components checked)"
        )

        if health.errors:
            for error in health.errors:
                logger.error(f"  ❌ {error}")

        if health.warnings:
            for warning in health.warnings:
                logger.warning(f"  ⚠️ {warning}")

        # Log de recursos si está disponible
        if PSUTIL_AVAILABLE and 'cpu_percent' in health.resources:
            logger.info(
                f"  📊 Resources: CPU {health.resources['cpu_percent']:.1f}%, "
                f"Memory {health.resources['memory_percent']:.1f}%, "
                f"Disk {health.resources['disk_percent']:.1f}%"
            )

    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de health checks

        Args:
            limit: Número máximo de entradas a retornar

        Returns:
            Lista de health checks en formato dict
        """
        history = self.check_history[-limit:] if limit > 0 else self.check_history
        return [h.to_dict() for h in history]

    def get_uptime(self) -> float:
        """Obtiene el uptime del sistema en segundos"""
        return time.time() - self.start_time

    def get_uptime_details(self) -> Dict[str, Any]:
        """Obtiene información detallada de uptime del sistema"""
        uptime_seconds = time.time() - self.start_time

        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        return {
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": f"{days}d {hours}h {minutes}m {seconds}s",
            "start_time": self.start_time,
            "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat()
        }

    def get_availability_metrics(self) -> Dict[str, Any]:
        """Calcula métricas de disponibilidad basadas en el historial"""
        if not self.check_history:
            return {
                "availability_percent": 0.0,
                "healthy_checks": 0,
                "total_checks": 0,
                "message": "No health check history available"
            }

        total = len(self.check_history)
        healthy = sum(
            1 for h in self.check_history
            if h.overall_status == HealthStatus.HEALTHY
        )
        degraded = sum(
            1 for h in self.check_history
            if h.overall_status == HealthStatus.DEGRADED
        )
        unhealthy = sum(
            1 for h in self.check_history
            if h.overall_status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
        )

        availability = (healthy / total * 100) if total > 0 else 0.0

        return {
            "availability_percent": round(availability, 2),
            "healthy_checks": healthy,
            "degraded_checks": degraded,
            "unhealthy_checks": unhealthy,
            "total_checks": total,
            "check_history_size": len(self.check_history)
        }


# Instancia global del health checker (lazy initialization)
_global_health_checker: Optional[HealthChecker] = None


def get_health_checker(alert_thresholds: Optional[Dict[str, float]] = None) -> HealthChecker:
    """
    Obtiene la instancia global del health checker (singleton)

    Args:
        alert_thresholds: Umbrales de alerta (solo se usan en primera inicialización)

    Returns:
        HealthChecker: Instancia global
    """
    global _global_health_checker

    if _global_health_checker is None:
        _global_health_checker = HealthChecker(alert_thresholds)

    return _global_health_checker
