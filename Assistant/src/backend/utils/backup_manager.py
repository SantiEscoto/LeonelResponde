#!/usr/bin/env python3
"""
Backup Manager - Sistema de respaldo automático para memoria y Knowledge Base

Este módulo proporciona funcionalidades para:
- Respaldo automático de memoria conversacional
- Respaldo de Knowledge Base (índices FAISS y documentos)
- Respaldo de configuraciones y cache
- Programación de respaldos automáticos
- Restauración de respaldos
- Limpieza automática de respaldos antiguos
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import zipfile

try:
    from src.backend.utils.unified_logger import get_unified_logger
except ImportError:
    import logging

    def get_unified_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)


logger = get_unified_logger("BackupManager")


@dataclass
class BackupConfig:
    """Configuración para el sistema de respaldos"""

    backup_dir: str
    max_backups: int = 10
    backup_interval_hours: int = 24
    compress_backups: bool = True
    include_cache: bool = False
    auto_cleanup: bool = True
    retention_days: int = 30


@dataclass
class BackupItem:
    """Elemento a respaldar"""

    name: str
    source_path: str
    backup_subdir: str = ""
    is_directory: bool = False
    required: bool = True
    pre_backup_hook: Optional[Callable] = None
    post_backup_hook: Optional[Callable] = None


class BackupManager:
    """
    Gestor de respaldos automáticos para el sistema
    """

    def __init__(self, config: BackupConfig):
        """
        Inicializa el gestor de respaldos

        Args:
            config: Configuración del sistema de respaldos
        """
        self.config = config
        self.backup_items: List[BackupItem] = []
        self.is_running = False
        self.backup_thread: Optional[threading.Thread] = None
        self.last_backup_time: Optional[datetime] = None

        # Crear directorio de respaldos si no existe
        Path(self.config.backup_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"💾 BackupManager inicializado en {self.config.backup_dir}")

    def add_backup_item(self, item: BackupItem) -> None:
        """
        Agrega un elemento al sistema de respaldos

        Args:
            item: Elemento a respaldar
        """
        self.backup_items.append(item)
        logger.info(f"📁 Agregado elemento de respaldo: {item.name}")

    def add_memory_backup(self, memory_dir: str) -> None:
        """
        Agrega respaldo de memoria conversacional

        Args:
            memory_dir: Directorio de memoria
        """
        memory_path = Path(memory_dir)

        # Archivo principal de memoria
        if (memory_path / "conversation_history.json").exists():
            self.add_backup_item(
                BackupItem(
                    name="conversation_history",
                    source_path=str(memory_path / "conversation_history.json"),
                    backup_subdir="memory",
                    required=True,
                )
            )

        # Memoria a largo plazo
        if (memory_path / "long_term_memory.json").exists():
            self.add_backup_item(
                BackupItem(
                    name="long_term_memory",
                    source_path=str(memory_path / "long_term_memory.json"),
                    backup_subdir="memory",
                    required=True,
                )
            )

        # Grupos de memoria
        if (memory_path / "memory_groups.json").exists():
            self.add_backup_item(
                BackupItem(
                    name="memory_groups",
                    source_path=str(memory_path / "memory_groups.json"),
                    backup_subdir="memory",
                    required=False,
                )
            )

        logger.info(f"🧠 Configurado respaldo de memoria desde {memory_dir}")

    def add_knowledge_base_backup(self, kb_dir: str) -> None:
        """
        Agrega respaldo de Knowledge Base

        Args:
            kb_dir: Directorio de Knowledge Base
        """
        kb_path = Path(kb_dir)

        # Índice FAISS
        if (kb_path / "faiss_index.bin").exists():
            self.add_backup_item(
                BackupItem(
                    name="faiss_index",
                    source_path=str(kb_path / "faiss_index.bin"),
                    backup_subdir="knowledge",
                    required=True,
                )
            )

        # Documentos
        if (kb_path / "documents.json").exists():
            self.add_backup_item(
                BackupItem(
                    name="documents",
                    source_path=str(kb_path / "documents.json"),
                    backup_subdir="knowledge",
                    required=True,
                )
            )

        # Cache de embeddings (opcional)
        if self.config.include_cache and (kb_path / "embeddings_cache.pkl").exists():
            self.add_backup_item(
                BackupItem(
                    name="embeddings_cache",
                    source_path=str(kb_path / "embeddings_cache.pkl"),
                    backup_subdir="knowledge",
                    required=False,
                )
            )

        logger.info(f"📚 Configurado respaldo de Knowledge Base desde {kb_dir}")

    def add_config_backup(self, config_file: str) -> None:
        """
        Agrega respaldo de archivo de configuración

        Args:
            config_file: Ruta al archivo de configuración
        """
        if Path(config_file).exists():
            self.add_backup_item(
                BackupItem(
                    name="config", source_path=config_file, backup_subdir="config", required=False
                )
            )
            logger.info(f"⚙️ Configurado respaldo de configuración desde {config_file}")

    def create_backup(self, backup_name: Optional[str] = None) -> Optional[str]:
        """
        Crea un respaldo completo del sistema

        Args:
            backup_name: Nombre opcional para el respaldo

        Returns:
            Ruta del respaldo creado o None si falló
        """
        try:
            # Generar nombre del respaldo
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"backup_{timestamp}"

            backup_path = Path(self.config.backup_dir) / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"🔄 Iniciando respaldo: {backup_name}")

            # Crear manifiesto del respaldo
            manifest = {
                "backup_name": backup_name,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
                "items": [],
                "checksums": {},
            }

            # Respaldar cada elemento
            for item in self.backup_items:
                try:
                    # Ejecutar hook pre-respaldo si existe
                    if item.pre_backup_hook:
                        item.pre_backup_hook()

                    source_path = Path(item.source_path)
                    if not source_path.exists():
                        if item.required:
                            logger.warning(f"⚠️ Archivo requerido no encontrado: {item.source_path}")
                        continue

                    # Crear subdirectorio si es necesario
                    dest_dir = backup_path
                    if item.backup_subdir:
                        dest_dir = backup_path / item.backup_subdir
                        dest_dir.mkdir(parents=True, exist_ok=True)

                    # Copiar archivo o directorio
                    dest_path = dest_dir / source_path.name

                    if item.is_directory:
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source_path, dest_path)

                    # Calcular checksum
                    checksum = self._calculate_checksum(dest_path)

                    # Agregar al manifiesto
                    manifest["items"].append(
                        {
                            "name": item.name,
                            "source_path": str(source_path),
                            "dest_path": str(dest_path.relative_to(backup_path)),
                            "is_directory": item.is_directory,
                            "size_bytes": self._get_size(dest_path),
                        }
                    )

                    manifest["checksums"][item.name] = checksum

                    # Ejecutar hook post-respaldo si existe
                    if item.post_backup_hook:
                        item.post_backup_hook()

                    logger.info(f"✅ Respaldado: {item.name}")

                except Exception as e:
                    logger.error(f"❌ Error respaldando {item.name}: {e}")
                    if item.required:
                        raise

            # Guardar manifiesto
            manifest_path = backup_path / "backup_manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)

            # Comprimir si está habilitado
            final_backup_path = str(backup_path)
            if self.config.compress_backups:
                zip_path = f"{backup_path}.zip"
                self._create_zip(backup_path, zip_path)
                shutil.rmtree(backup_path)  # Eliminar directorio sin comprimir
                final_backup_path = zip_path

            self.last_backup_time = datetime.now()

            logger.info(f"💾 Respaldo completado: {final_backup_path}")
            return final_backup_path

        except Exception as e:
            logger.error(f"❌ Error creando respaldo: {e}")
            return None

    def restore_backup(
        self,
        backup_path: str,
        restore_items: Optional[List[str]] = None,
        restore_dir: Optional[str] = None,
    ) -> bool:
        """
        Restaura un respaldo

        Args:
            backup_path: Ruta del respaldo a restaurar
            restore_items: Lista opcional de elementos específicos a restaurar
            restore_dir: Directorio opcional donde restaurar (si no se especifica,
                        restaura a ubicaciones originales)

        Returns:
            True si la restauración fue exitosa
        """
        try:
            backup_path_obj = Path(backup_path)

            # Manejar archivos comprimidos
            temp_dir = None
            if backup_path.endswith(".zip"):
                temp_dir = Path(self.config.backup_dir) / "temp_restore"
                temp_dir.mkdir(exist_ok=True)

                with zipfile.ZipFile(backup_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Buscar el directorio extraído
                extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
                if extracted_dirs:
                    backup_path_obj = extracted_dirs[0]
                else:
                    backup_path_obj = temp_dir

            # Leer manifiesto
            manifest_path = backup_path_obj / "backup_manifest.json"
            if not manifest_path.exists():
                logger.error("❌ Manifiesto de respaldo no encontrado")
                return False

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            logger.info(f"🔄 Restaurando respaldo: {manifest['backup_name']}")

            # Restaurar elementos
            for item_info in manifest["items"]:
                item_name = item_info["name"]

                # Filtrar elementos si se especificó
                if restore_items and item_name not in restore_items:
                    continue

                try:
                    source_path = backup_path_obj / item_info["dest_path"]

                    if restore_dir:
                        # Restaurar a directorio personalizado
                        relative_path = item_info["dest_path"]
                        dest_path = Path(restore_dir) / relative_path
                    else:
                        # Restaurar a ubicación original
                        dest_path = Path(item_info["source_path"])

                    # Crear directorio padre si no existe
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Restaurar archivo o directorio
                    if item_info["is_directory"]:
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(source_path, dest_path)
                    else:
                        shutil.copy2(source_path, dest_path)

                    # Verificar checksum si está disponible
                    if item_name in manifest["checksums"]:
                        expected_checksum = manifest["checksums"][item_name]
                        actual_checksum = self._calculate_checksum(dest_path)

                        if expected_checksum != actual_checksum:
                            logger.warning(f"⚠️ Checksum no coincide para {item_name}")

                    logger.info(f"✅ Restaurado: {item_name}")

                except Exception as e:
                    logger.error(f"❌ Error restaurando {item_name}: {e}")

            # Limpiar directorio temporal
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir)

            logger.info("✅ Restauración completada")
            return True

        except Exception as e:
            logger.error(f"❌ Error restaurando respaldo: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Lista todos los respaldos disponibles

        Returns:
            Lista de información de respaldos
        """
        backups = []
        backup_dir = Path(self.config.backup_dir)

        if not backup_dir.exists():
            return backups

        # Buscar respaldos (directorios y archivos zip)
        for item in backup_dir.iterdir():
            if item.name.startswith("backup_") and (item.is_dir() or item.suffix == ".zip"):
                try:
                    backup_info = self._get_backup_info(item)
                    if backup_info:
                        backups.append(backup_info)
                except Exception as e:
                    logger.warning(f"⚠️ Error leyendo respaldo {item.name}: {e}")

        # Ordenar por fecha (más reciente primero)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)

        return backups

    def cleanup_old_backups(self) -> int:
        """
        Limpia respaldos antiguos según la configuración

        Returns:
            Número de respaldos eliminados
        """
        if not self.config.auto_cleanup:
            return 0

        backups = self.list_backups()
        deleted_count = 0

        # Eliminar por cantidad máxima
        if len(backups) > self.config.max_backups:
            excess_backups = backups[self.config.max_backups :]
            for backup in excess_backups:
                try:
                    backup_path = Path(backup["path"])
                    if backup_path.exists():
                        if backup_path.is_dir():
                            shutil.rmtree(backup_path)
                        else:
                            backup_path.unlink()
                        deleted_count += 1
                        logger.info(f"🗑️ Eliminado respaldo antiguo: {backup['name']}")
                except Exception as e:
                    logger.error(f"❌ Error eliminando respaldo {backup['name']}: {e}")

        # Eliminar por antigüedad
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
        for backup in backups:
            try:
                backup_date = datetime.fromisoformat(backup["timestamp"])
                if backup_date < cutoff_date:
                    backup_path = Path(backup["path"])
                    if backup_path.exists():
                        if backup_path.is_dir():
                            shutil.rmtree(backup_path)
                        else:
                            backup_path.unlink()
                        deleted_count += 1
                        logger.info(f"🗑️ Eliminado respaldo expirado: {backup['name']}")
            except Exception as e:
                logger.error(f"❌ Error eliminando respaldo expirado {backup['name']}: {e}")

        if deleted_count > 0:
            logger.info(f"🧹 Limpieza completada: {deleted_count} respaldos eliminados")

        return deleted_count

    def start_automatic_backup(self) -> None:
        """
        Inicia el sistema de respaldos automáticos
        """
        if self.is_running:
            logger.warning("⚠️ Sistema de respaldos automáticos ya está ejecutándose")
            return

        self.is_running = True
        self.backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
        self.backup_thread.start()

        logger.info(
            f"🔄 Sistema de respaldos automáticos iniciado (cada "
            f"{self.config.backup_interval_hours}h)"
        )

    def stop_automatic_backup(self) -> None:
        """
        Detiene el sistema de respaldos automáticos
        """
        self.is_running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)

        logger.info("⏹️ Sistema de respaldos automáticos detenido")

    def get_backup_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado del sistema de respaldos

        Returns:
            Diccionario con información del estado
        """
        backups = self.list_backups()

        return {
            "is_running": self.is_running,
            "backup_dir": self.config.backup_dir,
            "total_backups": len(backups),
            "last_backup_time": (
                self.last_backup_time.isoformat() if self.last_backup_time else None
            ),
            "next_backup_time": self._get_next_backup_time(),
            "backup_items_count": len(self.backup_items),
            "config": {
                "max_backups": self.config.max_backups,
                "backup_interval_hours": self.config.backup_interval_hours,
                "compress_backups": self.config.compress_backups,
                "auto_cleanup": self.config.auto_cleanup,
                "retention_days": self.config.retention_days,
            },
            "recent_backups": backups[:5],  # Últimos 5 respaldos
        }

    def _backup_loop(self) -> None:
        """
        Bucle principal para respaldos automáticos
        """
        while self.is_running:
            try:
                # Verificar si es hora de hacer respaldo
                if self._should_create_backup():
                    self.create_backup()
                    self.cleanup_old_backups()

                # Esperar antes de la siguiente verificación
                time.sleep(300)  # Verificar cada 5 minutos

            except Exception as e:
                logger.error(f"❌ Error en bucle de respaldos: {e}")
                time.sleep(60)  # Esperar 1 minuto antes de reintentar

    def _should_create_backup(self) -> bool:
        """
        Determina si es hora de crear un respaldo

        Returns:
            True si debe crear un respaldo
        """
        if not self.last_backup_time:
            return True

        time_since_last = datetime.now() - self.last_backup_time
        return time_since_last.total_seconds() >= (self.config.backup_interval_hours * 3600)

    def _get_next_backup_time(self) -> Optional[str]:
        """
        Calcula la hora del próximo respaldo

        Returns:
            Timestamp del próximo respaldo o None
        """
        if not self.is_running or not self.last_backup_time:
            return None

        next_time = self.last_backup_time + timedelta(hours=self.config.backup_interval_hours)
        return next_time.isoformat()

    def _create_zip(self, source_dir: Path, zip_path: str) -> None:
        """
        Crea un archivo ZIP del directorio de respaldo

        Args:
            source_dir: Directorio a comprimir
            zip_path: Ruta del archivo ZIP
        """
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir.parent)
                    zipf.write(file_path, arcname)

    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calcula el checksum MD5 de un archivo o directorio

        Args:
            file_path: Ruta del archivo o directorio

        Returns:
            Checksum MD5
        """
        md5_hash = hashlib.md5()

        if file_path.is_file():
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
        else:
            # Para directorios, calcular hash de todos los archivos
            root_path = file_path
            for current_file in sorted(file_path.rglob("*")):
                if current_file.is_file():
                    md5_hash.update(str(current_file.relative_to(root_path)).encode())
                    with open(current_file, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            md5_hash.update(chunk)

        return md5_hash.hexdigest()

    def _get_size(self, path: Path) -> int:
        """
        Obtiene el tamaño de un archivo o directorio

        Args:
            path: Ruta del archivo o directorio

        Returns:
            Tamaño en bytes
        """
        if path.is_file():
            return path.stat().st_size
        else:
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

    def _get_backup_info(self, backup_path: Path) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de un respaldo

        Args:
            backup_path: Ruta del respaldo

        Returns:
            Información del respaldo o None
        """
        try:
            # Manejar archivos comprimidos
            manifest_data = None

            if backup_path.suffix == ".zip":
                with zipfile.ZipFile(backup_path, "r") as zip_ref:
                    # Buscar manifiesto en el ZIP
                    for file_info in zip_ref.filelist:
                        if file_info.filename.endswith("backup_manifest.json"):
                            with zip_ref.open(file_info) as f:
                                manifest_data = json.load(f)
                            break
            else:
                manifest_path = backup_path / "backup_manifest.json"
                if manifest_path.exists():
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)

            if manifest_data:
                return {
                    "name": manifest_data["backup_name"],
                    "timestamp": manifest_data["timestamp"],
                    "path": str(backup_path),
                    "size_bytes": self._get_size(backup_path),
                    "items_count": len(manifest_data["items"]),
                    "compressed": backup_path.suffix == ".zip",
                }
            else:
                # Respaldo sin manifiesto (formato antiguo)
                return {
                    "name": backup_path.name,
                    "timestamp": datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat(),
                    "path": str(backup_path),
                    "size_bytes": self._get_size(backup_path),
                    "items_count": 0,
                    "compressed": backup_path.suffix == ".zip",
                }

        except Exception as e:
            # Solo logear como warning si el archivo no existe (puede ser normal durante la creación)
            if "No such file or directory" in str(e):
                logger.debug(f"ℹ️ Respaldo aún no disponible: {backup_path}")
            else:
                logger.error(f"❌ Error obteniendo información de respaldo {backup_path}: {e}")
            return None


# Función de conveniencia para crear un gestor de respaldos configurado
def create_backup_manager(
    config_obj,
    models_dir: Optional[Path] = None,  # ✅ AGREGAR PARÁMETRO
    backup_interval_hours: int = 24,
    max_backups: int = 10,
    compress_backups: bool = True,
    **kwargs,
) -> BackupManager:
    """
    Crea un gestor de respaldos configurado para el sistema

    Args:
        config_obj: Objeto de configuración unificada del sistema
        models_dir: Directorio de modelos (opcional, se toma de config si no se especifica)
        backup_interval_hours: Intervalo entre respaldos automáticos
        max_backups: Número máximo de respaldos a mantener
        compress_backups: Si comprimir los respaldos
        **kwargs: Argumentos adicionales

    Returns:
        Instancia configurada de BackupManager
    """
    # Usar models_dir del parámetro o de la configuración
    if models_dir is None:
        models_dir = Path(config_obj.paths.models_dir)
    else:
        models_dir = Path(models_dir)

    # Configurar directorio de respaldos
    backup_dir = getattr(config_obj.paths, "backup_dir", None) or str(models_dir / "backups")

    # Obtener max_backups de la configuración de backup si existe, sino usar el parámetro
    try:
        config_max_backups = getattr(config_obj, "backup", None)
        if config_max_backups and hasattr(config_max_backups, "max_backups"):
            max_backups = config_max_backups.max_backups or max_backups
    except AttributeError:
        # Usar el valor por defecto si no existe en la configuración
        pass

    config = BackupConfig(
        backup_dir=backup_dir,
        backup_interval_hours=backup_interval_hours,
        max_backups=max_backups,
        compress_backups=compress_backups,
        include_cache=False,  # No incluir cache por defecto
        auto_cleanup=True,
        retention_days=30,
    )

    manager = BackupManager(config)

    # Configurar respaldos automáticos
    memory_dir = Path(config_obj.paths.memory_dir)
    if memory_dir.exists():
        manager.add_memory_backup(str(memory_dir))

    # Usar knowledge_dir si existe, sino usar knowledge_base_dir como fallback
    kb_dir_name = (
        getattr(config_obj.paths, "knowledge_dir", None)
        or getattr(config_obj.paths, "knowledge_base_dir", None)
        or "knowledge_base"
    )
    kb_dir = Path(kb_dir_name) if Path(kb_dir_name).is_absolute() else models_dir / kb_dir_name

    if kb_dir.exists():
        manager.add_knowledge_base_backup(str(kb_dir))

    # Buscar archivo de configuración
    config_file = getattr(config_obj.paths, "config_file", None)
    if config_file:
        config_file = Path(config_file)
        if config_file.exists():
            manager.add_config_backup(str(config_file))

    return manager


# Test del módulo
if __name__ == "__main__":
    print("🧪 Testing BackupManager...")

    # Crear directorio de prueba
    test_dir = Path("/tmp/backup_test")
    test_dir.mkdir(exist_ok=True)

    # Crear archivos de prueba
    (test_dir / "test_memory.json").write_text('{"test": "memory data"}')
    (test_dir / "test_kb.json").write_text('{"test": "kb data"}')

    # Configurar gestor de respaldos
    config = BackupConfig(
        backup_dir=str(test_dir / "backups"),
        max_backups=3,
        backup_interval_hours=1,
        compress_backups=True,
    )

    manager = BackupManager(config)

    # Agregar elementos de prueba
    manager.add_backup_item(
        BackupItem(
            name="test_memory",
            source_path=str(test_dir / "test_memory.json"),
            backup_subdir="memory",
        )
    )

    manager.add_backup_item(
        BackupItem(
            name="test_kb", source_path=str(test_dir / "test_kb.json"), backup_subdir="knowledge"
        )
    )

    # Crear respaldo
    backup_path = manager.create_backup("test_backup")
    if backup_path:
        print(f"✅ Respaldo creado: {backup_path}")

        # Listar respaldos
        backups = manager.list_backups()
        print(f"📋 Respaldos disponibles: {len(backups)}")

        # Obtener estado
        status = manager.get_backup_status()
        print(f"📊 Estado: {status['total_backups']} respaldos")

        print("✅ BackupManager funcionando correctamente")
    else:
        print("❌ Error creando respaldo")

    # Limpiar
    shutil.rmtree(test_dir, ignore_errors=True)
