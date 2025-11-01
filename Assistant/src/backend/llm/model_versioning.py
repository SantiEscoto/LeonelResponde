"""
Sistema de Model Versioning
============================

Módulo para gestión de versiones de modelos LLM con:
- Registro de versiones de modelos
- Metadata de versión (fecha, hash, configuración)
- Comparación de rendimiento entre versiones
- Rollback a versiones anteriores
- Almacenamiento persistente de información de versiones

Autor: Assistant
Fecha: 2025
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

try:
    from src.backend.utils.unified_logger import get_unified_logger
    logger = get_unified_logger("MODEL_VERSIONING")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MODEL_VERSIONING")


class ModelStatus(str, Enum):
    """Estados de un modelo"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"
    ARCHIVED = "archived"


@dataclass
class ModelPerformanceMetrics:
    """Métricas de rendimiento de un modelo"""
    avg_latency_ms: float = 0.0
    tokens_per_second: float = 0.0
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_tokens_generated: float = 0.0

    def update(
        self,
        latency_ms: float,
        tokens_generated: int,
        success: bool = True
    ) -> None:
        """
        Actualiza métricas con una nueva query

        Args:
            latency_ms: Latencia de la query en milisegundos
            tokens_generated: Tokens generados
            success: Si la query fue exitosa
        """
        # Actualizar contadores
        self.total_queries += 1
        if success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1

        # Actualizar promedios (media móvil)
        n = self.total_queries
        self.avg_latency_ms = (
            (self.avg_latency_ms * (n - 1) + latency_ms) / n
        )
        self.avg_tokens_generated = (
            (self.avg_tokens_generated * (n - 1) + tokens_generated) / n
        )

        # Calcular tokens por segundo
        if latency_ms > 0:
            current_tps = (tokens_generated / latency_ms) * 1000
            self.tokens_per_second = (
                (self.tokens_per_second * (n - 1) + current_tps) / n
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelPerformanceMetrics":
        """Crea desde diccionario"""
        return cls(**data)


@dataclass
class ModelVersion:
    """Información de una versión de modelo"""
    version_id: str
    model_path: str
    file_hash: str
    registered_at: float
    status: ModelStatus = ModelStatus.TESTING
    description: str = ""

    # Configuración del modelo
    config: Dict[str, Any] = field(default_factory=dict)

    # Métricas de rendimiento
    metrics: ModelPerformanceMetrics = field(default_factory=ModelPerformanceMetrics)

    # Metadata adicional
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamp de última actualización
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización"""
        return {
            "version_id": self.version_id,
            "model_path": self.model_path,
            "file_hash": self.file_hash,
            "registered_at": self.registered_at,
            "status": self.status.value,
            "description": self.description,
            "config": self.config,
            "metrics": self.metrics.to_dict(),
            "metadata": self.metadata,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelVersion":
        """Crea desde diccionario"""
        # Convertir metrics de dict a objeto
        metrics_data = data.get("metrics", {})
        metrics = ModelPerformanceMetrics.from_dict(metrics_data)

        return cls(
            version_id=data["version_id"],
            model_path=data["model_path"],
            file_hash=data["file_hash"],
            registered_at=data["registered_at"],
            status=ModelStatus(data.get("status", "testing")),
            description=data.get("description", ""),
            config=data.get("config", {}),
            metrics=metrics,
            metadata=data.get("metadata", {}),
            last_updated=data.get("last_updated", time.time())
        )


class ModelVersionManager:
    """
    Gestor de versiones de modelos LLM

    Gestiona el registro, seguimiento y comparación de diferentes
    versiones de modelos, permitiendo rollback y análisis de rendimiento.
    """

    def __init__(self, versions_file: Optional[str] = None):
        """
        Inicializa el gestor de versiones

        Args:
            versions_file: Ruta al archivo de almacenamiento de versiones
        """
        # Determinar ruta del archivo de versiones
        if versions_file:
            self.versions_file = Path(versions_file)
        else:
            # Usar directorio por defecto
            default_dir = Path(__file__).parent.parent.parent / "models" / "versions"
            default_dir.mkdir(parents=True, exist_ok=True)
            self.versions_file = default_dir / "model_versions.json"

        # Almacenamiento de versiones
        self.versions: Dict[str, ModelVersion] = {}

        # Versión activa actual
        self.active_version_id: Optional[str] = None

        # Cargar versiones existentes
        self._load_versions()

        logger.info(f"📚 Model Version Manager inicializado (archivo: {self.versions_file})")

    def _compute_file_hash(self, file_path: str) -> str:
        """
        Calcula el hash SHA256 de un archivo

        Args:
            file_path: Ruta al archivo

        Returns:
            Hash SHA256 del archivo
        """
        sha256 = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                # Leer en chunks para archivos grandes
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)

            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"❌ Error calculando hash de {file_path}: {e}")
            # Retornar hash vacío en caso de error
            return ""

    def register_model(
        self,
        model_path: str,
        version_id: Optional[str] = None,
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        set_as_active: bool = False
    ) -> ModelVersion:
        """
        Registra una nueva versión de modelo

        Args:
            model_path: Ruta al archivo del modelo
            version_id: ID de versión (se genera automáticamente si no se proporciona)
            description: Descripción de la versión
            config: Configuración del modelo
            metadata: Metadata adicional
            set_as_active: Si establecer como versión activa

        Returns:
            ModelVersion registrada
        """
        # Verificar que el archivo existe
        if not os.path.exists(model_path):
            raise ValueError(f"Archivo de modelo no encontrado: {model_path}")

        # Calcular hash del archivo
        file_hash = self._compute_file_hash(model_path)

        # Verificar si ya existe una versión con este hash
        for existing_version in self.versions.values():
            if existing_version.file_hash == file_hash:
                logger.warning(
                    f"⚠️ Modelo con hash {file_hash[:8]}... ya registrado "
                    f"como versión {existing_version.version_id}"
                )
                return existing_version

        # Generar version_id si no se proporciona
        if not version_id:
            # Usar timestamp + primeros 8 caracteres del hash
            timestamp = int(time.time())
            version_id = f"v_{timestamp}_{file_hash[:8]}"

        # Verificar que version_id no existe
        if version_id in self.versions:
            raise ValueError(f"Version ID '{version_id}' ya existe")

        # Crear nueva versión
        model_version = ModelVersion(
            version_id=version_id,
            model_path=model_path,
            file_hash=file_hash,
            registered_at=time.time(),
            status=ModelStatus.ACTIVE if set_as_active else ModelStatus.TESTING,
            description=description,
            config=config or {},
            metadata=metadata or {}
        )

        # Guardar versión
        self.versions[version_id] = model_version

        # Establecer como activa si se solicita
        if set_as_active:
            self.set_active_version(version_id)

        # Persistir cambios
        self._save_versions()

        logger.info(
            f"✅ Modelo registrado: {version_id} "
            f"(hash: {file_hash[:8]}..., activa: {set_as_active})"
        )

        return model_version

    def set_active_version(self, version_id: str) -> bool:
        """
        Establece una versión como activa

        Args:
            version_id: ID de la versión

        Returns:
            True si se estableció correctamente
        """
        if version_id not in self.versions:
            logger.error(f"❌ Versión '{version_id}' no encontrada")
            return False

        # Cambiar estado de versión anterior
        if self.active_version_id and self.active_version_id in self.versions:
            old_version = self.versions[self.active_version_id]
            if old_version.status == ModelStatus.ACTIVE:
                old_version.status = ModelStatus.DEPRECATED
                old_version.last_updated = time.time()

        # Establecer nueva versión activa
        self.active_version_id = version_id
        new_version = self.versions[version_id]
        new_version.status = ModelStatus.ACTIVE
        new_version.last_updated = time.time()

        # Persistir cambios
        self._save_versions()

        logger.info(f"🔄 Versión activa cambiada a: {version_id}")

        return True

    def get_active_version(self) -> Optional[ModelVersion]:
        """Obtiene la versión activa actual"""
        if self.active_version_id and self.active_version_id in self.versions:
            return self.versions[self.active_version_id]
        return None

    def get_version(self, version_id: str) -> Optional[ModelVersion]:
        """Obtiene una versión específica"""
        return self.versions.get(version_id)

    def list_versions(
        self,
        status: Optional[ModelStatus] = None,
        sort_by: str = "registered_at"
    ) -> List[ModelVersion]:
        """
        Lista versiones de modelos

        Args:
            status: Filtrar por estado (None = todas)
            sort_by: Campo por el que ordenar

        Returns:
            Lista de versiones
        """
        versions = list(self.versions.values())

        # Filtrar por estado si se especifica
        if status:
            versions = [v for v in versions if v.status == status]

        # Ordenar
        if sort_by == "registered_at":
            versions.sort(key=lambda v: v.registered_at, reverse=True)
        elif sort_by == "version_id":
            versions.sort(key=lambda v: v.version_id)
        elif sort_by == "performance":
            versions.sort(key=lambda v: v.metrics.tokens_per_second, reverse=True)

        return versions

    def update_metrics(
        self,
        version_id: str,
        latency_ms: float,
        tokens_generated: int,
        success: bool = True
    ) -> bool:
        """
        Actualiza métricas de rendimiento de una versión

        Args:
            version_id: ID de la versión
            latency_ms: Latencia de la query en milisegundos
            tokens_generated: Tokens generados
            success: Si la query fue exitosa

        Returns:
            True si se actualizó correctamente
        """
        version = self.versions.get(version_id)
        if not version:
            logger.error(f"❌ Versión '{version_id}' no encontrada")
            return False

        # Actualizar métricas
        version.metrics.update(latency_ms, tokens_generated, success)
        version.last_updated = time.time()

        # Persistir cambios (solo cada 10 actualizaciones para reducir I/O)
        if version.metrics.total_queries % 10 == 0:
            self._save_versions()

        return True

    def compare_versions(
        self,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """
        Compara dos versiones de modelos

        Args:
            version_id_1: ID de la primera versión
            version_id_2: ID de la segunda versión

        Returns:
            Diccionario con comparación
        """
        v1 = self.versions.get(version_id_1)
        v2 = self.versions.get(version_id_2)

        if not v1 or not v2:
            return {"error": "Una o ambas versiones no encontradas"}

        # Comparar métricas
        comparison = {
            "version_1": {
                "id": v1.version_id,
                "status": v1.status.value,
                "metrics": v1.metrics.to_dict()
            },
            "version_2": {
                "id": v2.version_id,
                "status": v2.status.value,
                "metrics": v2.metrics.to_dict()
            },
            "differences": {
                "latency_diff_ms": v2.metrics.avg_latency_ms - v1.metrics.avg_latency_ms,
                "tps_diff": v2.metrics.tokens_per_second - v1.metrics.tokens_per_second,
                "success_rate_diff": (
                    (v2.metrics.successful_queries / max(v2.metrics.total_queries, 1)) -
                    (v1.metrics.successful_queries / max(v1.metrics.total_queries, 1))
                )
            },
            "winner": {
                "latency": version_id_1 if v1.metrics.avg_latency_ms < v2.metrics.avg_latency_ms else version_id_2,
                "throughput": version_id_1 if v1.metrics.tokens_per_second > v2.metrics.tokens_per_second else version_id_2,
            }
        }

        return comparison

    def rollback_to_version(self, version_id: str) -> bool:
        """
        Hace rollback a una versión anterior

        Args:
            version_id: ID de la versión a restaurar

        Returns:
            True si se hizo rollback correctamente
        """
        if version_id not in self.versions:
            logger.error(f"❌ Versión '{version_id}' no encontrada")
            return False

        logger.info(f"🔙 Haciendo rollback a versión: {version_id}")

        return self.set_active_version(version_id)

    def archive_version(self, version_id: str) -> bool:
        """
        Archiva una versión (cambia estado a ARCHIVED)

        Args:
            version_id: ID de la versión

        Returns:
            True si se archivó correctamente
        """
        version = self.versions.get(version_id)
        if not version:
            logger.error(f"❌ Versión '{version_id}' no encontrada")
            return False

        # No permitir archivar la versión activa
        if version_id == self.active_version_id:
            logger.error(f"❌ No se puede archivar la versión activa")
            return False

        version.status = ModelStatus.ARCHIVED
        version.last_updated = time.time()

        # Persistir cambios
        self._save_versions()

        logger.info(f"📦 Versión archivada: {version_id}")

        return True

    def get_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen del estado de versiones

        Returns:
            Diccionario con resumen
        """
        total_versions = len(self.versions)

        # Contar por estado
        status_counts = {}
        for status in ModelStatus:
            count = sum(1 for v in self.versions.values() if v.status == status)
            if count > 0:
                status_counts[status.value] = count

        # Versión con mejor rendimiento
        best_throughput = None
        best_latency = None

        for version in self.versions.values():
            if version.metrics.total_queries > 0:
                if best_throughput is None or version.metrics.tokens_per_second > best_throughput.metrics.tokens_per_second:
                    best_throughput = version

                if best_latency is None or version.metrics.avg_latency_ms < best_latency.metrics.avg_latency_ms:
                    best_latency = version

        return {
            "total_versions": total_versions,
            "active_version": self.active_version_id,
            "status_counts": status_counts,
            "best_throughput": best_throughput.version_id if best_throughput else None,
            "best_latency": best_latency.version_id if best_latency else None,
            "versions_file": str(self.versions_file)
        }

    def _load_versions(self) -> None:
        """Carga versiones desde el archivo de persistencia"""
        if not self.versions_file.exists():
            logger.info("📝 No hay archivo de versiones existente, creando nuevo")
            return

        try:
            with open(self.versions_file, 'r') as f:
                data = json.load(f)

            # Cargar versiones
            for version_data in data.get("versions", []):
                version = ModelVersion.from_dict(version_data)
                self.versions[version.version_id] = version

            # Cargar versión activa
            self.active_version_id = data.get("active_version_id")

            logger.info(f"✅ Cargadas {len(self.versions)} versiones desde {self.versions_file}")

        except Exception as e:
            logger.error(f"❌ Error cargando versiones: {e}")

    def _save_versions(self) -> None:
        """Guarda versiones en el archivo de persistencia"""
        try:
            # Preparar datos para serialización
            data = {
                "active_version_id": self.active_version_id,
                "versions": [v.to_dict() for v in self.versions.values()],
                "last_save": time.time()
            }

            # Crear directorio si no existe
            self.versions_file.parent.mkdir(parents=True, exist_ok=True)

            # Guardar con formato legible
            with open(self.versions_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"💾 Versiones guardadas en {self.versions_file}")

        except Exception as e:
            logger.error(f"❌ Error guardando versiones: {e}")


# Instancia global del version manager (lazy initialization)
_global_version_manager: Optional[ModelVersionManager] = None


def get_version_manager(versions_file: Optional[str] = None) -> ModelVersionManager:
    """
    Obtiene la instancia global del version manager (singleton)

    Args:
        versions_file: Ruta al archivo de versiones (solo primera inicialización)

    Returns:
        ModelVersionManager: Instancia global
    """
    global _global_version_manager

    if _global_version_manager is None:
        _global_version_manager = ModelVersionManager(versions_file=versions_file)

    return _global_version_manager
