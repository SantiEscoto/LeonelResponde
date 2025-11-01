"""
Component initialization functions for the Assistant application.
Separates initialization logic from main.py for better modularity and testability.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Any

from src.backend.utils.unified_config import get_config
from src.backend.utils.unified_logger import get_unified_logger

# Import components with fallbacks
try:
    from src.backend.memory.memory_service import MemoryService
except ImportError:
    MemoryService = None

try:
    from src.backend.llm.model_manager import LLMManager
except ImportError:
    LLMManager = None

try:
    from src.backend.llm.knowledge_base import KnowledgeBase
except ImportError:
    KnowledgeBase = None

try:
    from src.backend.utils.backup_manager import create_backup_manager
except ImportError:
    create_backup_manager = None

try:
    from src.backend.utils.resource_monitor import get_resource_monitor
except ImportError:
    get_resource_monitor = None


config = get_config()
logger = get_unified_logger("ComponentInitializers")


def init_memory_service(models_dir: Path) -> Optional[MemoryService]:
    """Initialize the Memory Service with LangChain components."""
    if MemoryService is None:
        logger.warning("MemoryService no disponible, usando memoria básica")
        return None
        
    memory_dir = models_dir / config.paths.memory_dir
    memory_dir.mkdir(exist_ok=True, parents=True)
    
    return MemoryService(
        session_id="default_session",
        base_dir=str(memory_dir),
        window_k=config.memory.max_token_limit if hasattr(config.memory, 'max_token_limit') else 6,
        enable_summaries=True,
        summary_threshold_tokens=4000
    )


def init_llm_manager() -> Optional[Any]:
    """Initialize LLM manager"""
    try:
        from src.backend.llm.model_manager import LLMManager
        from src.backend.utils.unified_config import get_config
        
        config = get_config()
        
        logger.info("🔧 Initializing LLMManager...")
        
        # Get model path from config
        model_path = str(config.paths.models_dir / config.llm.model_name)
        
        # Initialize LLMManager with only model_path parameter
        llm_manager = LLMManager(model_path=model_path)
        
        logger.info("✅ LLMManager initialized successfully")
        return llm_manager
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLMManager: {e}")
        return None


def init_knowledge_base() -> Optional[Any]:
    """Initialize knowledge base"""
    try:
        from src.backend.llm.knowledge_base import KnowledgeBase
        from src.backend.utils.unified_config import get_config
        
        config = get_config()
        kb_config = config.knowledge_base
        
        logger.info("🔧 Initializing KnowledgeBase...")
        
        # Initialize KnowledgeBase with correct parameters
        knowledge_base = KnowledgeBase(
            embedding_model=kb_config.embedding_model,
            index_path=str(config.paths.knowledge_dir / "knowledge_index"),
            documents_path=str(config.paths.knowledge_dir / "documents"),
            cache_size=kb_config.cache_size
        )
        
        logger.info("✅ KnowledgeBase initialized successfully")
        return knowledge_base
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize KnowledgeBase: {e}")
        return None


def init_backup_manager() -> Optional[Any]:
    """Initialize backup manager"""
    try:
        from src.backend.utils.backup_manager import BackupManager, BackupConfig
        from src.backend.utils.unified_config import get_config
        
        config = get_config()
        backup_config = config.backup
        
        logger.info("🔧 Initializing BackupManager...")
        
        # Create BackupConfig object for BackupManager
        backup_config_obj = BackupConfig(
            backup_dir=str(config.paths.backup_dir),
            max_backups=backup_config.max_backups,
            backup_interval_hours=backup_config.interval_hours,
            compress_backups=backup_config.compress_backups,
            include_cache=False,
            auto_cleanup=True,
            retention_days=30
        )
        
        # Initialize BackupManager with BackupConfig object
        backup_manager = BackupManager(backup_config_obj)
        
        logger.info("✅ BackupManager initialized successfully")
        return backup_manager
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize BackupManager: {e}")
        return None


def init_resource_monitor() -> Optional[Any]:
    """Initialize resource monitor"""
    try:
        from src.backend.utils.resource_monitor import ResourceMonitor
        from src.backend.utils.unified_config import get_config
        
        config = get_config()
        monitoring_config = config.monitoring
        
        logger.info("🔧 Initializing ResourceMonitor...")
        
        # Initialize ResourceMonitor with correct parameter names
        resource_monitor = ResourceMonitor(
            monitoring_interval=monitoring_config.resource_monitor_interval,
            cpu_threshold=monitoring_config.cpu_threshold,
            memory_threshold=monitoring_config.memory_threshold,
            alerts_enabled=monitoring_config.enabled
        )
        
        logger.info("✅ ResourceMonitor initialized successfully")
        return resource_monitor
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize ResourceMonitor: {e}")
        return None