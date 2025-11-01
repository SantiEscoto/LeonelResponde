#!/usr/bin/env python3
"""
🔧 Unified Configuration Manager for LeonelResponde Assistant
Consolidates all configuration from config.py, constants.py, and mcp_config.json
Provides a single source of truth for all application settings
"""

from dataclasses import asdict, dataclass, field
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Import unified logger with error handling
try:
    from .unified_logger import get_unified_logger

    logger = get_unified_logger("CONFIG")
except ImportError as e:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("CONFIG")
    logger.warning(f"Could not import unified_logger: {e}")

# Error handling imports with fallbacks
try:
    from .error_types import ErrorCategory, ErrorSeverity
    from .error_handler import (
        ErrorContext,
        get_error_handler,
        resilient_operation,
    )

    error_handler = get_error_handler()
except ImportError as e:
    logger.warning(f"Could not import error_handler: {e}")

    # Fallback implementations
    def resilient_operation(operation_name: str, max_retries: int = 3, timeout: int = 30):
        def decorator(func):
            return func

        return decorator

    class ErrorContext:
        def __init__(self, **kwargs):
            pass

    from .error_types import ErrorSeverity, ErrorCategory

    def get_error_handler():
        return None

    error_handler = None

# PyTorch availability check with error handling
try:
    import torch

    TORCH_AVAILABLE = True
    MPS_AVAILABLE = torch.backends.mps.is_available() if hasattr(torch.backends, "mps") else False
except ImportError:
    TORCH_AVAILABLE = False
    MPS_AVAILABLE = False
    logger.info("PyTorch not available, using CPU-only mode")


@dataclass
class PathConfig:
    """
    Configuración de rutas del sistema

    Attributes:
        project_root: Directorio raíz del proyecto
        models_dir: Directorio para modelos de IA
        logs_dir: Directorio para archivos de log
        memory_dir: Directorio para archivos de memoria
        knowledge_dir: Directorio para base de conocimiento
        cache_dir: Directorio para archivos de caché
        backup_dir: Directorio para respaldos
        user_memory_dir: Directorio para memoria específica de usuarios
        user_data_dir: Directorio para datos de usuario
        memory_dir_name: Nombre del directorio de memoria (para compatibilidad)
        knowledge_dir_name: Nombre del directorio de conocimiento (para compatibilidad)
        knowledge_base_dir: Directorio específico para la base de conocimiento
    """

    project_root: Path
    models_dir: Path
    logs_dir: Path
    memory_dir: Path
    knowledge_dir: Path
    cache_dir: Path
    backup_dir: Path
    user_memory_dir: Path
    # Missing attributes that main.py expects
    memory_dir_name: str = "memory"
    knowledge_dir_name: str = "knowledge"
    # Atributos faltantes críticos identificados en los logs
    knowledge_base_dir: Optional[Path] = None
    user_data_dir: Optional[Path] = None

    def __post_init__(self) -> None:
        """Inicialización posterior para configurar rutas derivadas"""
        if self.knowledge_base_dir is None:
            self.knowledge_base_dir = self.knowledge_dir / "base"
        if self.user_data_dir is None:
            self.user_data_dir = self.models_dir / "user_data"

    @classmethod
    def from_project_root(cls, root: Optional[Path] = None) -> "PathConfig":
        if root is None:
            # Calcular desde src/backend/utils/ hasta la raíz del proyecto Assistant
            root = Path(__file__).parent.parent.parent.parent

        models_dir = root / "data" / "models"
        return cls(
            project_root=root,
            models_dir=models_dir,
            logs_dir=root / "logs",
            memory_dir=models_dir / "memory",
            knowledge_dir=models_dir / "knowledge",
            cache_dir=models_dir / "cache",
            backup_dir=models_dir / "backups",
            user_memory_dir=models_dir / "memory" / "users",
            memory_dir_name="memory",
            knowledge_dir_name="knowledge",
        )


@dataclass
class LLMConfig:
    """LLM model configuration - Optimized for performance"""

    model_name: str = "mistral-7b-instruct-v0.1.Q4_K_M.gguf"
    max_tokens: int = 400  # Reduced from 800 for faster responses
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.15
    n_gpu_layers: int = 10  # Further reduced to prevent GPU overload
    n_ctx: int = 1024  # Further reduced for better performance
    n_threads: int = 2  # Further reduced to prevent CPU overload
    batch_size: int = 128  # Further reduced for lower memory usage
    device: str = "auto"
    response_timeout: int = 15  # Reduced from 30 to 15 seconds
    use_mlock: bool = True
    use_mmap: bool = True
    low_vram: bool = True  # Enable low VRAM mode for better memory management
    disable_mps: bool = True  # Disable MPS on macOS to prevent hanging issues


@dataclass
class SystemConfig:
    """System-wide configuration - Optimized for performance"""

    log_level: str = "WARNING"  # Reduced logging for better performance
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    debug_mode: bool = False  # Disabled debug mode for better performance
    enable_gpu: bool = True
    batch_size: int = 16  # Reduced from 32 for lower memory usage
    enable_caching: bool = True
    cpu_threshold: float = 50.0  # Even lower threshold for earlier warnings
    memory_threshold: float = 60.0  # Even lower threshold for earlier warnings
    gpu_threshold: float = 70.0  # Even lower threshold for earlier warnings
    enable_performance_logs: bool = False  # Disabled for better performance
    log_rotation_size: int = 5  # Reduced from 10 MB
    request_timeout: int = 15  # Reduced from 30 seconds
    max_concurrent_requests: int = 2  # Reduced from 4 for lower resource usage


@dataclass
class KnowledgeBaseConfig:
    """Knowledge base and embedding configuration - Optimized for performance"""

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    chunk_size: int = 300  # Reduced from 500 for faster processing
    chunk_overlap: int = 30  # Reduced from 50
    max_results: int = 3  # Reduced from 5 for faster retrieval
    similarity_threshold: float = 0.8  # Increased from 0.7 for better precision
    enable_reranking: bool = False
    index_type: str = "IVF"
    auto_update_index: bool = False  # Disabled for better performance
    index_save_interval: int = 200  # Increased from 100 for less frequent saves
    cache_embeddings: bool = True
    max_cache_size: int = 500  # Reduced from 1000 for lower memory usage
    faiss_index_filename: str = "faiss_index.bin"
    documents_filename: str = "documents.json"


@dataclass
class LangChainMemoryConfig:
    """LangChain conversational memory configuration - Optimized for performance"""

    enable: bool = False  # Default disabled; can be toggled via env ENABLE_LANGCHAIN_MEMORY
    window_k: int = 6  # Reduced from 12 for lower memory usage
    summary_threshold_tokens: int = 300  # Reduced from 500 for faster processing
    retrieval_k: int = 3  # Reduced from 5 for faster retrieval
    persist_dir: Optional[Path] = None  # Directory to persist chat history
    vectorstores_dir: Optional[Path] = None  # Directory to persist vector stores
    enable_summaries: bool = True  # Whether to enable summaries (future use)
    max_context_tokens: int = 1500  # Maximum tokens for context assembly
    smart_truncation: bool = True  # Enable intelligent context truncation


@dataclass
class MemoryConfig:
    """Memory management configuration - Optimized for performance"""

    conversation_history_filename: str = "conversation_history.json"
    memory_groups_filename: str = "memory_groups.json"
    max_memory_mb: int = 256  # Reduced from 512 for lower memory usage
    cleanup_threshold: float = 0.7  # Reduced from 0.8 for earlier cleanup
    enable_compression: bool = True
    auto_save_interval: int = 60  # Increased from 30 for less frequent saves
    max_conversation_length: int = 50  # Reduced from 100 for lower memory usage
    enable_long_term_memory: bool = True
    max_short_term_memory: int = 20  # Reduced from 40 for lower memory usage
    auto_transition_threshold: int = 15  # Reduced from 35 for faster transitions
    smart_transition_enabled: bool = True
    summary_interval: int = 20  # Increased from 10 for less frequent summaries
    auto_save: bool = True
    backup_frequency: int = 100  # Increased from 50 for less frequent backups
    cache_summaries: bool = True
    async_operations: bool = False  # Disabled for better performance
    context_token_limit: int = 400  # Reduced from 800 for faster processing
    enable_user_memory: bool = True
    user_cache_timeout_hours: int = 12  # Reduced from 24 for faster cleanup
    max_user_interactions_short: int = 4  # Reduced from 8 for lower memory usage
    max_user_interactions_long: int = 500  # Reduced from 1000 for lower memory usage
    context_relevance_days: int = 14  # Reduced from 30 for faster cleanup
    cache_size: int = 50  # Reduced from 100 for lower memory usage
    # New: LangChain memory sub-config
    langchain: LangChainMemoryConfig = field(default_factory=LangChainMemoryConfig)


@dataclass
class ResourceMonitorConfig:
    """Resource monitoring configuration - Optimized for performance"""

    monitor_interval: float = 60.0  # Increased from 30.0 for less frequent monitoring
    history_size: int = 10  # Reduced from 20 for lower memory usage
    average_usage_samples: int = 3  # Reduced from 5 for faster calculations


@dataclass
class BackupConfig:
    """Backup management configuration"""

    interval_hours: int = 24
    max_backups: int = 7
    compress_backups: bool = True
    enabled: bool = True
    backup_interval: int = 24  # horas


@dataclass
class CacheConfig:
    """Caching configuration"""

    enable_embedding_cache: bool = True
    embedding_cache_size: int = 1000
    enable_model_cache: bool = True
    preload_models: bool = True
    enable_query_optimization: bool = True


@dataclass
class EmbeddingsConfig:
    """
    Config for embeddings and vectorization

    Attributes:
        default_model: Default model for generating embeddings
        device: Device to run embeddings on ("cpu" by default for offline/low resource)
        cache_dir: Directory to cache embeddings/model files
        cache_embeddings: Whether to cache generated embeddings
        max_cache_size: Max cache size for embeddings
        embedding_dimension: Dimension of the embedding vectors
    """

    default_model: str = "all-MiniLM-L6-v2"
    device: str = "cpu"
    cache_dir: Optional[Path] = None
    cache_embeddings: bool = True
    max_cache_size: int = 1000
    embedding_dimension: int = 384


@dataclass
class MonitoringConfig:
    """
    Configuración para monitoreo del sistema

    Attributes:
        enabled: Si el monitoreo está habilitado
        resource_monitor_interval: Intervalo en segundos para monitorear recursos
        memory_threshold: Umbral de memoria en porcentaje para alertas
        cpu_threshold: Umbral de CPU en porcentaje para alertas
        disk_threshold: Umbral de disco en porcentaje para alertas
        enable_performance_tracking: Si habilitar seguimiento de rendimiento
        log_resource_usage: Si registrar el uso de recursos en logs
    """

    enabled: bool = True
    resource_monitor_interval: float = 30.0
    memory_threshold: float = 0.85  # 85%
    cpu_threshold: float = 0.80  # 80%
    disk_threshold: float = 0.90  # 90%
    enable_performance_tracking: bool = True
    log_resource_usage: bool = True


@dataclass
class TracingConfig:
    """Performance tracing configuration"""

    enabled: bool = True
    enable_e2e_timing: bool = True
    enable_detailed_spans: bool = True
    enable_streaming_metrics: bool = True
    flush_console_output: bool = True
    export_csv_on_exit: bool = False
    clear_traces_on_start: bool = True
    log_file: Optional[str] = None


@dataclass
class ConsoleConfig:
    """Console behavior flags (kept separate from tracing for clarity)"""

    enable_e2e_timing: bool = True
    flush_console_output: bool = True


@dataclass
class MCPServerConfig:
    """MCP server configuration"""

    command: str
    args: list
    description: str
    enabled: bool = True


@dataclass
class MCPConfig:
    """MCP (Model Context Protocol) configuration"""

    servers: Dict[str, MCPServerConfig]
    version: str = "1.0.0"
    description: str = "Configuración MCP para LeonelResponde - Asistente Multimodal Offline"


@dataclass
class UIConfig:
    """User interface configuration"""

    separator_line: str = "═" * 50
    sub_separator_line: str = "─" * 30

@dataclass
class VoiceConfig:
    """Configuración del servidor de voz (WS/STT/TTS)"""
    ws_host: str = "127.0.0.1"
    ws_port: int = 8010
    vosk_model_path: Optional[str] = None


@dataclass
class EnvironmentConfig:
    """Environment variables configuration"""

    tmp_dir: str = "/tmp"
    pytorch_mps_fallback: str = "1"
    tokenizers_parallelism: str = "false"
    sys_path_index: int = 0


class UnifiedConfig:
    """
    Configuración unificada del sistema

    Esta clase centraliza toda la configuración del sistema, incluyendo:
    - Configuración de rutas y directorios
    - Configuración de modelos LLM
    - Configuración de memoria y caché
    - Configuración de base de conocimiento
    - Configuración de respaldos
    - Configuración de embeddings
    - Configuración de monitoreo
    - Configuración de trazado de rendimiento
    - Configuración de servidores MCP

    Attributes:
        paths: Configuración de rutas del sistema
        llm: Configuración de modelos de lenguaje
        memory: Configuración de memoria y caché
        knowledge: Configuración de base de conocimiento
        backup: Configuración de respaldos
        embeddings: Configuración de embeddings
        monitoring: Configuración de monitoreo
        tracing: Configuración de trazado de rendimiento
        mcp_servers: Lista de configuraciones de servidores MCP
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Inicializa la configuración unificada

        Args:
            config_dir: Ruta opcional al directorio de configuración
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent.parent

        self.config_dir = config_dir
        self.paths = PathConfig.from_project_root(config_dir)

        # Initialize error handler
        self.error_handler = get_error_handler()

        # Initialize all configuration sections
        self.llm = LLMConfig()
        self.system = SystemConfig()
        self.knowledge_base = KnowledgeBaseConfig()
        self.memory = MemoryConfig()
        self.resource_monitor = ResourceMonitorConfig()
        self.backup = BackupConfig()
        self.cache = CacheConfig()
        self.tracing = TracingConfig()
        self.embeddings = EmbeddingsConfig()  # Add missing embeddings config
        self.monitoring = MonitoringConfig()  # Add missing monitoring config
        self.ui = UIConfig()
        self.environment = EnvironmentConfig()
        # New: Console section
        self.console = ConsoleConfig()
        # New: Voice server configuration
        self.voice = VoiceConfig()

        # Backwards-compatible attributes expected by callers
        self.FLUSH_CONSOLE_OUTPUT = self.tracing.flush_console_output
        self.ENABLE_E2E_TIMING = self.tracing.enable_e2e_timing

        # Defaults wiring for new fields/paths
        # Embeddings cache directory
        if self.embeddings.cache_dir is None:
            self.embeddings.cache_dir = self.paths.cache_dir / "embeddings"
        # LangChain memory persistence directories
        if self.memory.langchain.persist_dir is None:
            self.memory.langchain.persist_dir = self.paths.memory_dir / "langchain"
        if self.memory.langchain.vectorstores_dir is None:
            self.memory.langchain.vectorstores_dir = self.paths.memory_dir / "vectorstores"
        # Optional: allow env flag to toggle LangChain memory
        # If env is set, it overrides the default (which is disabled by default)
        env_flag = os.environ.get("ENABLE_LANGCHAIN_MEMORY")
        if env_flag is not None:
            self.memory.langchain.enable = str(env_flag).lower() in {"1", "true", "yes"}

        # Optional: Allow overriding LLM model name via environment variable
        # Useful for minimal Jetson/RPi setups with smaller GGUF models
        env_llm_model = os.environ.get("LLM_MODEL_NAME")
        if env_llm_model:
            try:
                self.llm.model_name = str(env_llm_model)
                logger.info(f"🔧 LLM model override via env: {self.llm.model_name}")
            except Exception as e:
                logger.warning(f"Failed to apply LLM_MODEL_NAME env override: {e}")

        # Load MCP configuration
        self.mcp = self._load_mcp_config()

        # Create necessary directories
        self._create_directories()

        # Set environment variables
        self._set_environment_variables()

        logger.info("🔧 Unified configuration initialized")
        self._log_configuration_summary()

    def _load_mcp_config(self) -> MCPConfig:
        """Load MCP configuration from JSON file"""
        mcp_config_path = self.config_dir / "mcp_config.json"

        if not mcp_config_path.exists():
            logger.warning(f"MCP config file not found: {mcp_config_path}")
            return MCPConfig(servers={})

        try:
            with open(mcp_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # DRY: extraer configuración de servidor de voz (host/port/model) desde mcp_config.json
            try:
                mcp_servers_list = data.get("mcp_servers") or data.get("mcpServersList")
                if isinstance(mcp_servers_list, list):
                    for entry in mcp_servers_list:
                        if isinstance(entry, dict) and entry.get("name") == "voice_server":
                            cfg = entry.get("config") or {}
                            host = cfg.get("host")
                            port = cfg.get("port")
                            model = cfg.get("vosk_model_path") or cfg.get("model_path")
                            if host:
                                self.voice.ws_host = str(host)
                            if port:
                                self.voice.ws_port = int(port)
                            if model:
                                self.voice.vosk_model_path = str(model)
                            break
            except Exception as e:
                logger.warning(f"Could not parse voice server settings from mcp_config.json: {e}")

            servers = {}
            for name, config in data.get("mcpServers", {}).items():
                servers[name] = MCPServerConfig(
                    command=config["command"],
                    args=config["args"],
                    description=config["description"],
                    enabled=config.get("enabled", True),
                )

            return MCPConfig(
                servers=servers,
                version=data.get("version", "1.0.0"),
                description=data.get("description", "MCP Configuration"),
            )

        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return MCPConfig(servers={})

    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.paths.models_dir,
            self.paths.logs_dir,
            self.paths.memory_dir,
            self.paths.knowledge_dir,
            self.paths.cache_dir,
            self.paths.backup_dir,
            self.paths.user_memory_dir,
            # New: LangChain persistence dirs
            self.memory.langchain.persist_dir,
            self.memory.langchain.vectorstores_dir,
        ]
        for directory in directories:
            if directory is None:
                continue
            directory.mkdir(parents=True, exist_ok=True)

    def _set_environment_variables(self) -> None:
        """Set environment variables from configuration"""
        os.environ.update(
            {
                "TMPDIR": self.environment.tmp_dir,
                "TEMP": self.environment.tmp_dir,
                "PYTORCH_ENABLE_MPS_FALLBACK": self.environment.pytorch_mps_fallback,
                "TOKENIZERS_PARALLELISM": self.environment.tokenizers_parallelism,
            }
        )

    def _log_configuration_summary(self) -> None:
        """Log a concise summary of important configuration values"""
        logger.info(f"📁 Models directory: {self.paths.models_dir}")
        logger.info(f"📁 Logs directory: {self.paths.logs_dir}")
        logger.info(f"🧠 Device: {self.llm.device}")
        logger.info(f"🤖 Model: {self.llm.model_name}")
        logger.info(f"📚 Embedding model: {self.knowledge_base.embedding_model}")
        if MPS_AVAILABLE:
            logger.info("🚀 Apple Silicon MPS: ✅ Enabled")
        else:
            logger.info("💻 Using CPU (normal on Intel/CPU systems)")

    def get_file_paths(self) -> Dict[str, str]:
        """Get commonly used file paths for other modules"""
        return {
            "memory_file": str(self.paths.memory_dir / self.memory.conversation_history_filename),
            "memory_groups_file": str(self.paths.memory_dir / self.memory.memory_groups_filename),
            "memory_backup_dir": str(self.paths.backup_dir),
            "user_memory_dir": str(self.paths.user_memory_dir),
            "index_path": str(self.paths.knowledge_dir / self.knowledge_base.faiss_index_filename),
            "documents_path": str(
                self.paths.knowledge_dir / self.knowledge_base.documents_filename
            ),
            "trace_log_file": str(self.paths.logs_dir / "trace_data.jsonl"),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "paths": asdict(self.paths),
            "llm": asdict(self.llm),
            "system": asdict(self.system),
            "knowledge_base": asdict(self.knowledge_base),
            "memory": asdict(self.memory),
            "resource_monitor": asdict(self.resource_monitor),
            "backup": asdict(self.backup),
            "cache": asdict(self.cache),
            "tracing": asdict(self.tracing),
            "console": asdict(self.console),
            "ui": asdict(self.ui),
            "environment": asdict(self.environment),
            "voice": asdict(self.voice),
            "mcp": {
                "servers": {name: asdict(server) for name, server in self.mcp.servers.items()},
                "version": self.mcp.version,
                "description": self.mcp.description,
            },
        }

    def save_config(self, filepath: Optional[Path] = None):
        """Save current configuration to JSON file"""
        if filepath is None:
            filepath = self.config_dir / "unified_config.json"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
            logger.info(f"Configuration saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")


# Global configuration instance
_config_instance: Optional[UnifiedConfig] = None


def get_config() -> UnifiedConfig:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = UnifiedConfig()
    return _config_instance


def reload_config() -> UnifiedConfig:
    """Reload the global configuration instance"""
    global _config_instance
    _config_instance = UnifiedConfig()
    return _config_instance


# Convenience functions for backward compatibility
def get_llm_config() -> LLMConfig:
    return get_config().llm


def get_system_config() -> SystemConfig:
    return get_config().system


def get_paths() -> PathConfig:
    return get_config().paths


def get_file_paths() -> Dict[str, str]:
    return get_config().get_file_paths()


# Export commonly used values for backward compatibility
config = get_config()
LLM_CONFIG = asdict(config.llm)
SYSTEM_CONFIG = asdict(config.system)
KB_CONFIG = asdict(config.knowledge_base)
MEMORY_CONFIG = asdict(config.memory)
CACHE_CONFIG = asdict(config.cache)
TRACE_CONFIG = asdict(config.tracing)

# Export paths
PROJECT_ROOT = config.paths.project_root
MODELS_DIR = config.paths.models_dir
LOGS_DIR = config.paths.logs_dir

# Export commonly used constants
API_HOST = config.system.api_host
API_PORT = config.system.api_port
DEBUG_MODE = config.system.debug_mode
TRACE_ENABLED = config.tracing.enabled
TRACE_LOG_FILE = str(config.paths.logs_dir / "trace_data.jsonl")
# Keep backwards-compatible uppercase constants, sourced from tracing by default
ENABLE_E2E_TIMING = config.tracing.enable_e2e_timing
FLUSH_CONSOLE_OUTPUT = config.tracing.flush_console_output
# Note: console section is available at config.console for future use
ENABLE_E2E_TIMING = config.tracing.enable_e2e_timing
FLUSH_CONSOLE_OUTPUT = config.tracing.flush_console_output

# Export hardware detection
TORCH_AVAILABLE = TORCH_AVAILABLE
MPS_AVAILABLE = MPS_AVAILABLE

if __name__ == "__main__":
    # Test the configuration system
    test_config = UnifiedConfig()
    print("✅ Unified configuration system test completed")
    test_config.save_config()
