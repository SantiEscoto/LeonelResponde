"""
Sistema de Graceful Shutdown Avanzado
======================================

Módulo para manejo avanzado de shutdown del sistema con:
- Manejo de señales del sistema (SIGINT, SIGTERM)
- Timeout configurable para shutdown
- Limpieza ordenada y thread-safe de recursos
- Sistema de callbacks para componentes
- Logging detallado del proceso de shutdown

Autor: Assistant
Fecha: 2025
"""

import signal
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

try:
    from src.backend.utils.unified_logger import get_unified_logger
    logger = get_unified_logger("SHUTDOWN")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("SHUTDOWN")


class ShutdownPhase(str, Enum):
    """Fases del proceso de shutdown"""
    NOT_STARTED = "not_started"
    SIGNAL_RECEIVED = "signal_received"
    STOPPING_NEW_REQUESTS = "stopping_new_requests"
    WAITING_ACTIVE_REQUESTS = "waiting_active_requests"
    CLEANING_RESOURCES = "cleaning_resources"
    SAVING_STATE = "saving_state"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FORCED = "forced"


@dataclass
class ShutdownCallback:
    """Callback a ejecutar durante el shutdown"""
    name: str
    callback: Callable
    priority: int = 0  # Mayor prioridad se ejecuta primero
    timeout: float = 5.0  # Timeout individual para el callback
    critical: bool = False  # Si es crítico, forzar espera


@dataclass
class ShutdownStats:
    """Estadísticas del proceso de shutdown"""
    start_time: float = 0.0
    end_time: float = 0.0
    signal_received: Optional[int] = None
    phase: ShutdownPhase = ShutdownPhase.NOT_STARTED
    callbacks_executed: int = 0
    callbacks_failed: int = 0
    forced_shutdown: bool = False
    errors: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Duración total del shutdown en segundos"""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time if self.start_time > 0 else 0.0


class GracefulShutdownManager:
    """
    Gestor avanzado de graceful shutdown

    Maneja el proceso completo de apagado del sistema de forma ordenada,
    ejecutando callbacks registrados en orden de prioridad y con timeouts.
    """

    def __init__(self, timeout: float = 30.0, force_timeout: float = 5.0):
        """
        Inicializa el gestor de shutdown

        Args:
            timeout: Tiempo máximo total para shutdown graceful (segundos)
            force_timeout: Tiempo adicional antes de forzar salida (segundos)
        """
        self.timeout = timeout
        self.force_timeout = force_timeout
        self.shutdown_requested = False
        self.shutdown_lock = threading.Lock()
        self.callbacks: List[ShutdownCallback] = []
        self.stats = ShutdownStats()
        self.original_handlers: Dict[int, Any] = {}

        logger.info(
            f"🛡️ Graceful Shutdown Manager inicializado "
            f"(timeout: {timeout}s, force: {force_timeout}s)"
        )

    def register_callback(
        self,
        name: str,
        callback: Callable,
        priority: int = 0,
        timeout: float = 5.0,
        critical: bool = False
    ) -> None:
        """
        Registra un callback para ejecutar durante el shutdown

        Args:
            name: Nombre descriptivo del callback
            callback: Función a ejecutar
            priority: Prioridad (mayor = ejecuta primero)
            timeout: Timeout individual para este callback
            critical: Si es crítico, esperar obligatoriamente su finalización
        """
        shutdown_callback = ShutdownCallback(
            name=name,
            callback=callback,
            priority=priority,
            timeout=timeout,
            critical=critical
        )
        self.callbacks.append(shutdown_callback)

        # Ordenar callbacks por prioridad (mayor primero)
        self.callbacks.sort(key=lambda x: x.priority, reverse=True)

        logger.info(
            f"✅ Callback registrado: {name} "
            f"(priority: {priority}, timeout: {timeout}s, critical: {critical})"
        )

    def setup_signal_handlers(self) -> None:
        """Configura los manejadores de señales del sistema"""
        # Guardar handlers originales
        try:
            self.original_handlers[signal.SIGINT] = signal.signal(
                signal.SIGINT, self._signal_handler
            )
            self.original_handlers[signal.SIGTERM] = signal.signal(
                signal.SIGTERM, self._signal_handler
            )
            logger.info("✅ Manejadores de señales configurados (SIGINT, SIGTERM)")
        except Exception as e:
            logger.error(f"❌ Error configurando manejadores de señales: {e}")

    def _signal_handler(self, signum: int, frame) -> None:
        """
        Manejador de señales del sistema

        Args:
            signum: Número de la señal recibida
            frame: Frame actual de ejecución
        """
        signal_names = {
            signal.SIGINT: "SIGINT (Ctrl+C)",
            signal.SIGTERM: "SIGTERM (Terminación)"
        }
        signal_name = signal_names.get(signum, f"Señal {signum}")

        logger.info(f"🛑 {signal_name} recibida, iniciando graceful shutdown...")

        with self.shutdown_lock:
            if self.shutdown_requested:
                logger.warning("⚠️ Shutdown ya en progreso, señal duplicada recibida")

                # Si es la segunda señal, forzar salida inmediata
                if self.stats.phase not in [ShutdownPhase.COMPLETED, ShutdownPhase.FORCED]:
                    logger.warning("⚠️ Segunda señal recibida, forzando salida...")
                    self._force_shutdown(signum)
                return

            self.shutdown_requested = True
            self.stats.signal_received = signum
            self.stats.phase = ShutdownPhase.SIGNAL_RECEIVED

        # Iniciar shutdown en thread separado
        shutdown_thread = threading.Thread(
            target=self._execute_graceful_shutdown,
            name="graceful-shutdown-thread",
            daemon=False  # No daemon para asegurar ejecución completa
        )
        shutdown_thread.start()

        # Esperar con timeout
        shutdown_thread.join(timeout=self.timeout)

        if shutdown_thread.is_alive():
            logger.error(
                f"❌ Timeout en shutdown después de {self.timeout}s, "
                f"esperando {self.force_timeout}s adicionales..."
            )
            shutdown_thread.join(timeout=self.force_timeout)

            if shutdown_thread.is_alive():
                logger.error("❌ Timeout final alcanzado, forzando salida...")
                self._force_shutdown(signum)

    def _execute_graceful_shutdown(self) -> None:
        """Ejecuta el proceso de graceful shutdown"""
        self.stats.start_time = time.time()

        try:
            # Fase 1: Detener nuevos requests
            self._phase_stop_new_requests()

            # Fase 2: Esperar requests activos
            self._phase_wait_active_requests()

            # Fase 3: Limpiar recursos
            self._phase_clean_resources()

            # Fase 4: Guardar estado
            self._phase_save_state()

            # Fase 5: Finalizar
            self._phase_finalize()

            self.stats.phase = ShutdownPhase.COMPLETED
            self.stats.end_time = time.time()

            logger.info(
                f"✅ Graceful shutdown completado en {self.stats.duration:.2f}s "
                f"({self.stats.callbacks_executed} callbacks ejecutados, "
                f"{self.stats.callbacks_failed} fallidos)"
            )

        except Exception as e:
            logger.error(f"❌ Error durante graceful shutdown: {e}")
            self.stats.errors.append(str(e))
            self.stats.phase = ShutdownPhase.FORCED
            raise

    def _phase_stop_new_requests(self) -> None:
        """Fase 1: Detener aceptación de nuevos requests"""
        self.stats.phase = ShutdownPhase.STOPPING_NEW_REQUESTS
        logger.info("🛑 Fase 1: Deteniendo aceptación de nuevos requests...")

        # Ejecutar callbacks de esta fase
        self._execute_callbacks_for_phase("stop_requests")

    def _phase_wait_active_requests(self) -> None:
        """Fase 2: Esperar completitud de requests activos"""
        self.stats.phase = ShutdownPhase.WAITING_ACTIVE_REQUESTS
        logger.info("⏳ Fase 2: Esperando completitud de requests activos...")

        # Dar tiempo para que requests activos terminen
        wait_time = 2.0
        logger.info(f"⏳ Esperando {wait_time}s para requests activos...")
        time.sleep(wait_time)

    def _phase_clean_resources(self) -> None:
        """Fase 3: Limpiar recursos del sistema"""
        self.stats.phase = ShutdownPhase.CLEANING_RESOURCES
        logger.info("🗑️ Fase 3: Limpiando recursos del sistema...")

        # Ejecutar todos los callbacks registrados
        self._execute_all_callbacks()

    def _phase_save_state(self) -> None:
        """Fase 4: Guardar estado del sistema"""
        self.stats.phase = ShutdownPhase.SAVING_STATE
        logger.info("💾 Fase 4: Guardando estado del sistema...")

        # Ejecutar callbacks de guardado de estado
        self._execute_callbacks_for_phase("save_state")

    def _phase_finalize(self) -> None:
        """Fase 5: Finalización"""
        self.stats.phase = ShutdownPhase.FINALIZING
        logger.info("🏁 Fase 5: Finalizando shutdown...")

        # Ejecutar callbacks de finalización
        self._execute_callbacks_for_phase("finalize")

    def _execute_all_callbacks(self) -> None:
        """Ejecuta todos los callbacks registrados"""
        logger.info(f"🔄 Ejecutando {len(self.callbacks)} callbacks...")

        for callback_info in self.callbacks:
            self._execute_single_callback(callback_info)

    def _execute_callbacks_for_phase(self, phase: str) -> None:
        """
        Ejecuta callbacks específicos de una fase

        Args:
            phase: Nombre de la fase
        """
        matching_callbacks = [
            cb for cb in self.callbacks
            if phase in cb.name.lower()
        ]

        if matching_callbacks:
            logger.info(f"🔄 Ejecutando {len(matching_callbacks)} callbacks de fase '{phase}'...")
            for callback_info in matching_callbacks:
                self._execute_single_callback(callback_info)

    def _execute_single_callback(self, callback_info: ShutdownCallback) -> None:
        """
        Ejecuta un callback individual con timeout

        Args:
            callback_info: Información del callback a ejecutar
        """
        logger.info(f"🔄 Ejecutando callback: {callback_info.name}...")

        start_time = time.time()
        success = False

        try:
            # Ejecutar callback en thread con timeout
            callback_thread = threading.Thread(
                target=callback_info.callback,
                name=f"shutdown-callback-{callback_info.name}"
            )
            callback_thread.daemon = not callback_info.critical
            callback_thread.start()

            # Esperar con timeout
            callback_thread.join(timeout=callback_info.timeout)

            if callback_thread.is_alive():
                if callback_info.critical:
                    # Para callbacks críticos, esperar más tiempo
                    logger.warning(
                        f"⚠️ Callback crítico '{callback_info.name}' excedió timeout, "
                        f"esperando finalización..."
                    )
                    callback_thread.join(timeout=callback_info.timeout * 2)
                else:
                    logger.warning(
                        f"⚠️ Callback '{callback_info.name}' excedió timeout de "
                        f"{callback_info.timeout}s"
                    )

            success = not callback_thread.is_alive()
            duration = time.time() - start_time

            if success:
                logger.info(f"✅ Callback '{callback_info.name}' completado en {duration:.2f}s")
                self.stats.callbacks_executed += 1
            else:
                logger.error(f"❌ Callback '{callback_info.name}' no completó a tiempo")
                self.stats.callbacks_failed += 1
                self.stats.errors.append(f"Timeout en callback '{callback_info.name}'")

        except Exception as e:
            logger.error(f"❌ Error ejecutando callback '{callback_info.name}': {e}")
            self.stats.callbacks_failed += 1
            self.stats.errors.append(f"Error en callback '{callback_info.name}': {str(e)}")

    def _force_shutdown(self, signum: int) -> None:
        """
        Fuerza el shutdown inmediato del sistema

        Args:
            signum: Señal que causó el force shutdown
        """
        self.stats.phase = ShutdownPhase.FORCED
        self.stats.forced_shutdown = True
        self.stats.end_time = time.time()

        logger.error("🚨 FORZANDO SHUTDOWN INMEDIATO")
        logger.error(f"📊 Estadísticas finales: {self._get_stats_summary()}")

        # Restaurar handlers originales si existen
        self._restore_original_handlers()

        # Forzar salida
        sys.exit(1)

    def _restore_original_handlers(self) -> None:
        """Restaura los manejadores de señales originales"""
        try:
            for sig, handler in self.original_handlers.items():
                if handler is not None:
                    signal.signal(sig, handler)
            logger.info("✅ Manejadores de señales originales restaurados")
        except Exception as e:
            logger.warning(f"⚠️ Error restaurando handlers originales: {e}")

    def _get_stats_summary(self) -> str:
        """Obtiene un resumen de las estadísticas de shutdown"""
        return (
            f"duration={self.stats.duration:.2f}s, "
            f"callbacks_ok={self.stats.callbacks_executed}, "
            f"callbacks_failed={self.stats.callbacks_failed}, "
            f"phase={self.stats.phase.value}, "
            f"forced={self.stats.forced_shutdown}"
        )

    def get_stats(self) -> ShutdownStats:
        """Obtiene las estadísticas del shutdown"""
        return self.stats

    def is_shutdown_requested(self) -> bool:
        """Verifica si se ha solicitado el shutdown"""
        return self.shutdown_requested


# Instancia global del shutdown manager (lazy initialization)
_global_shutdown_manager: Optional[GracefulShutdownManager] = None


def get_shutdown_manager(
    timeout: float = 30.0,
    force_timeout: float = 5.0
) -> GracefulShutdownManager:
    """
    Obtiene la instancia global del shutdown manager (singleton)

    Args:
        timeout: Timeout total para shutdown (solo primera inicialización)
        force_timeout: Timeout adicional antes de forzar (solo primera inicialización)

    Returns:
        GracefulShutdownManager: Instancia global
    """
    global _global_shutdown_manager

    if _global_shutdown_manager is None:
        _global_shutdown_manager = GracefulShutdownManager(
            timeout=timeout,
            force_timeout=force_timeout
        )

    return _global_shutdown_manager
