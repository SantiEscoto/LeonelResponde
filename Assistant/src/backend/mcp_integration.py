#!/usr/bin/env python3
"""
MCP Integration Module for LeonelResponde Assistant
Integrates Model Context Protocol servers with the existing memory system
"""

import asyncio
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List

# Import existing memory system and unified config
try:
    from .llm.consolidated_memory_manager import ConsolidatedMemoryManager
    from .memory.faiss_manager import FAISSManager
    from .utils.unified_config import get_config
except ImportError:
    # Fallback for direct execution
    import sys

    sys.path.append(str(Path(__file__).parent))
    from memory.faiss_manager import FAISSManager
    from utils.unified_config import get_config

    from .llm.consolidated_memory_manager import ConsolidatedMemoryManager


class MCPIntegration:
    """
    Manages integration between MCP servers and LeonelResponde's memory system
    """

    def __init__(self, config_obj=None):
        self.unified_config = config_obj or get_config()
        self.config = self._get_mcp_config()
        self.sqlite_db_path = None
        self.memory_manager = None
        self.faiss_manager = None
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self._initialize_components()

    def _get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP configuration from unified config"""
        try:
            return {
                "enabled": getattr(self.unified_config.system, "mcp_enabled", True),
                "timeout": getattr(self.unified_config.system, "mcp_timeout", 30),
                "max_retries": getattr(self.unified_config.system, "mcp_max_retries", 3),
                "servers": getattr(self.unified_config.system, "mcp_servers", {}),
            }
        except Exception as e:
            self.logger.error(f"Error loading MCP config from unified config: {e}")
            return {"servers": {}}

    def _initialize_components(self):
        """Initialize memory management components"""
        try:
            # Extract SQLite database path from config
            if hasattr(self.unified_config, "mcp") and "sqlite" in self.unified_config.mcp.servers:
                sqlite_config = self.unified_config.mcp.servers["sqlite"]
                if sqlite_config.args:
                    self.sqlite_db_path = sqlite_config.args[-1]  # Last argument is DB path

            # Initialize memory managers
            memory_dir = str(self.unified_config.paths.memory_dir)
            self.memory_manager = ConsolidatedMemoryManager(
                memory_dir=memory_dir, enable_user_memory=True, enable_personality=True
            )
            self.faiss_manager = FAISSManager()

            self.logger.info("MCP Integration components initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP components: {e}")

    async def start_mcp_servers(self) -> Dict[str, bool]:
        """Start all enabled MCP servers"""
        results = {}

        for server_name, server_config in self.unified_config.mcp.servers.items():
            if not server_config.enabled:
                self.logger.info(f"Skipping disabled server: {server_name}")
                results[server_name] = False
                continue

            try:
                # Start server process
                command = [server_config.command] + server_config.args
                _ = await asyncio.create_subprocess_exec(
                    *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                self.logger.info(f"Started MCP server: {server_name}")
                results[server_name] = True

            except Exception as e:
                self.logger.error(f"Failed to start MCP server {server_name}: {e}")
                results[server_name] = False

        return results

    def store_conversation(
        self, user_id: str, message: str, response: str, context: str = None
    ) -> bool:
        """Store conversation in SQLite database via MCP"""
        if not self.sqlite_db_path:
            self.logger.error("SQLite database path not configured")
            return False

        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()

            cursor.execute(
                (
                    "INSERT INTO conversations (user_id, message, response, context) "
                    "VALUES (?, ?, ?, ?)"
                ),
                (user_id, message, response, context),
            )

            conn.commit()
            conn.close()

            self.logger.info(f"Stored conversation for user: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store conversation: {e}")
            return False

    def store_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str = "short",
        category: str = None,
        importance: int = 1,
    ) -> bool:
        """Store memory in SQLite database"""
        if not self.sqlite_db_path:
            self.logger.error("SQLite database path not configured")
            return False

        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()

            if memory_type == "short":
                cursor.execute(
                    ("INSERT INTO memory_short (user_id, content, importance) " "VALUES (?, ?, ?)"),
                    (user_id, content, importance),
                )
            elif memory_type == "long":
                cursor.execute(
                    (
                        "INSERT INTO memory_long (user_id, content, category, importance) "
                        "VALUES (?, ?, ?, ?)"
                    ),
                    (user_id, content, category, importance),
                )

            conn.commit()
            conn.close()

            # Also store in FAISS for vector search
            if self.faiss_manager:
                self.faiss_manager.add_memory(content, {"user_id": user_id, "type": memory_type})

            self.logger.info(f"Stored {memory_type} memory for user: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store memory: {e}")
            return False

    def retrieve_memories(
        self, user_id: str, query: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve memories from SQLite and FAISS"""
        memories = []

        if not self.sqlite_db_path:
            self.logger.error("SQLite database path not configured")
            return memories

        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()

            # Get recent memories from SQLite
            cursor.execute(
                "SELECT content, timestamp, importance FROM memory_short WHERE user_id = ? "
                "UNION ALL "
                "SELECT content, timestamp, importance FROM memory_long WHERE user_id = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (user_id, user_id, limit),
            )

            rows = cursor.fetchall()
            for row in rows:
                memories.append({"content": row[0], "timestamp": row[1], "importance": row[2]})

            conn.close()

            # If query provided, also search FAISS for semantic similarity
            if query and self.faiss_manager:
                similar_memories = self.faiss_manager.search_similar(query, k=5)
                memories.extend(similar_memories)

            self.logger.info(f"Retrieved {len(memories)} memories for user: {user_id}")
            return memories

        except Exception as e:
            self.logger.error(f"Failed to retrieve memories: {e}")
            return memories

    def get_server_status(self) -> Dict[str, str]:
        """Get status of all configured MCP servers"""
        status = {}

        for server_name, server_config in self.unified_config.mcp.servers.items():
            if server_config.enabled:
                # Simple check - in production, you'd want more sophisticated health checks
                status[server_name] = "configured"
            else:
                status[server_name] = "disabled"

        return status

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update MCP configuration"""
        try:
            with open(self.config_path, "w") as f:
                json.dump(new_config, f, indent=2)

            self.config = new_config
            self._initialize_components()

            self.logger.info("MCP configuration updated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update MCP configuration: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Initialize MCP integration
    mcp = MCPIntegration()

    # Test storing a conversation
    success = mcp.store_conversation(
        user_id="test_user",
        message="Hola Leonel, ¿cómo estás?",
        response="¡Hola! Estoy muy bien, gracias por preguntar. ¿En qué puedo ayudarte hoy?",
        context="greeting",
    )
    print(f"Conversation stored: {success}")

    # Test storing memory
    success = mcp.store_memory(
        user_id="test_user",
        content="El usuario prefiere comunicarse en español",
        memory_type="long",
        category="preferences",
        importance=3,
    )
    print(f"Memory stored: {success}")

    memories = mcp.retrieve_memories("test_user", limit=5)
    print(f"Retrieved {len(memories)} memories")

    status = mcp.get_server_status()
    print(f"Server status: {status}")
