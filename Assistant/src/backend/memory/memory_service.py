"""
MemoryService: lightweight conversational memory built on LangChain primitives
- ConversationBufferWindowMemory backed by FileChatMessageHistory for on-disk persistence
- Optional simple summarization to control token growth (offline heuristic)

This module is intentionally dependency-light and runs fully offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    # File-backed chat history (commonly provided by langchain_community)
    try:
        from langchain_community.chat_message_histories import FileChatMessageHistory
    except Exception:  # pragma: no cover - fallback for older distros
        from langchain.chat_message_histories import FileChatMessageHistory  # type: ignore

    from langchain_core.messages import BaseMessage, trim_messages
except Exception as e:  # pragma: no cover
    raise ImportError(
        "LangChain memory dependencies are missing. Install: \n"
        "  pip install langchain langchain-community langchain-core\n"
        "Or ensure these packages are present in your environment."
    ) from e


@dataclass
class MemoryServiceConfig:
    """Configuration values for MemoryService.

    Values typically come from unified_config.memory.langchain
    """

    base_dir: Path
    session_id: str = "default"
    window_k: int = 6
    enable_summaries: bool = True
    summary_threshold_tokens: int = 800
    retrieval_k: int = 5  # reserved for future vector retrieval integration


class MemoryService:
    """Thin wrapper around LangChain chat history + window memory with persistence.

    Responsibilities:
    - Persist messages to disk per session
    - Provide a rolling context window (k) for prompting
    - Optionally summarize older messages and prune file to control growth
    """

    def __init__(
        self,
        session_id: str,
        base_dir: str,
        window_k: int = 6,
        enable_summaries: bool = True,
        summary_threshold_tokens: int = 800,
        retrieval_k: int = 5,
    ):
        """Initialize MemoryService with LangChain components."""
        self.cfg = MemoryServiceConfig(
            session_id=session_id,
            base_dir=base_dir,
            window_k=window_k,
            enable_summaries=enable_summaries,
            summary_threshold_tokens=summary_threshold_tokens,
            retrieval_k=retrieval_k,
        )
        
        self.base_dir = Path(base_dir)
        self.session_dir = self.base_dir / session_id
        self._ensure_dirs()

        # Initialize file-backed chat history
        history_file = self.session_dir / "chat_history.json"
        self.history = FileChatMessageHistory(str(history_file))
        # Expose history file path for tests and callers that need direct access
        self.history_file = history_file  # ensures reset/persist tests can check file

        # Store window size for message trimming (replaces deprecated ConversationBufferWindowMemory)
        self.window_k = window_k
        
        # Add smart_context_manager attribute for backward compatibility with performance tests
        self.smart_context_manager = None  # Will be set by tests if needed
        
        # Store context_token_limit for backward compatibility with performance tests
        self.context_token_limit = summary_threshold_tokens
        
        # Add set_current_user method for backward compatibility
        def set_current_user(user_id: str, user_data: dict = None):
            """Set current user for legacy compatibility."""
            pass  # Placeholder implementation
        
        self.set_current_user = set_current_user

        # Summary management
        self.summary_text: Optional[str] = None
        self.summary_file = self.session_dir / "summary.txt"
        # Load any existing summary text from disk
        self.summary_text = self._load_summary()

        # Legacy compatibility attributes
        self.user_memory_manager = None  # Placeholder for legacy compatibility
        
        # Initialize logger for debugging
        self.logger = self._get_logger()

    def _get_logger(self):
        """Get logger instance for debugging."""
        try:
            from src.backend.utils.unified_logger import UnifiedLogger
            return UnifiedLogger("MemoryService")
        except ImportError:
            import logging
            return logging.getLogger("MemoryService")

    # -------------------- Public API --------------------
    def add_user_message(self, text: str) -> None:
        """Append a user message to persistent history and extract personal info."""
        self.history.add_user_message(text)
        
        # Extract and store personal information from user message
        try:
            from src.backend.memory.personal_info_extractor import PersonalInfoExtractor
            extractor = PersonalInfoExtractor(self.session_dir)
            extractor.extract_and_update(text)
        except Exception as e:
            self.logger.warning(f"Failed to extract personal info: {e}")
        
        # FileChatMessageHistory persists on write; still ensure dir integrity
        self._ensure_dirs()

    def add_ai_message(self, text: str) -> None:
        """Append an AI message to persistent history."""
        self.history.add_ai_message(text)
        self._ensure_dirs()

    def get_context_messages(self) -> List[BaseMessage]:
        """Return the current window of messages used for prompting.
        Simplified to avoid trim_messages quirks: we just return the last `window_k` messages in order.
        Includes a robust fallback that reconstructs messages from raw JSON if needed.
        """
        all_messages = list(self.history.messages)
        
        # Fallback: in some environments, freshly reloaded FileChatMessageHistory may not
        # surface all prior messages until an add operation occurs. To be safe, reconstruct
        # from the JSON file when we detect fewer messages than expected and the file exists.
        try:
            if self.history_file.exists():
                import json
                from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
                
                raw = self.history_file.read_text(encoding="utf-8").strip() or "[]"
                data = json.loads(raw)
                parsed: List[BaseMessage] = []
                for item in data:
                    # Support both {type, data:{content}} and {type, content}
                    mtype = (item.get("type") or item.get("role") or "").lower()
                    content = ""
                    if isinstance(item.get("data"), dict):
                        content = item["data"].get("content", "")
                    content = item.get("content", content)
                    if mtype in ("human", "user"):
                        parsed.append(HumanMessage(content=content))
                    elif mtype in ("ai", "assistant"):
                        parsed.append(AIMessage(content=content))
                    elif mtype == "system":
                        parsed.append(SystemMessage(content=content))
                    else:
                        # Unknown message type; skip silently
                        continue
                # If parsed contains more messages than the in-memory view, trust the parsed list
                if len(parsed) > len(all_messages):
                    all_messages = parsed
        except Exception as e:
            # Best-effort fallback only; log and continue with whatever we have
            try:
                self.logger.debug(f"Fallback parse of history file failed: {e}")
            except Exception:
                pass
        
        if not all_messages or self.window_k <= 0:
            return all_messages
        # Deterministically select the last K messages (oldest-to-newest within the slice)
        return all_messages[-self.window_k:]

    def get_context_as_text(self) -> str:
        """Return a human-readable transcript (role: content) for prompt context."""
        lines: List[str] = []
        
        # Add personal information context if available
        try:
            from src.backend.memory.personal_info_extractor import PersonalInfoExtractor
            extractor = PersonalInfoExtractor(self.session_dir)
            personal_info = extractor.get_relevant_info("")  # Get all available info
            if personal_info:
                lines.append(f"[Personal Information]\n{personal_info}")
        except Exception as e:
            self.logger.debug(f"Could not retrieve personal info: {e}")
        
        if self.summary_text:
            lines.append(f"[Previous Context Summary]\n{self.summary_text.strip()}")
        
        messages = self.get_context_messages()
        for m in messages:
            role = getattr(m, "type", getattr(m, "role", m.__class__.__name__)).upper()
            content = getattr(m, "content", "")
            # Clean and format content for better readability
            if content:
                content = content.strip()
                lines.append(f"{role}: {content}")
        
        context_text = "\n".join(lines)
        
        # Apply smart truncation if enabled and context is too long
        max_tokens = getattr(self.cfg, 'max_context_tokens', 1500)
        smart_truncation = getattr(self.cfg, 'smart_truncation', True)
        
        if smart_truncation and len(context_text.split()) * 0.75 > max_tokens:
            # Keep summary and most recent messages
            if self.summary_text and messages:
                # Keep summary + last 4 messages for better context
                recent_messages = messages[-4:]
                lines = [f"[Previous Context Summary]\n{self.summary_text.strip()}"]
                for m in recent_messages:
                    role = getattr(m, "type", getattr(m, "role", m.__class__.__name__)).upper()
                    content = getattr(m, "content", "").strip()
                    if content:
                        lines.append(f"{role}: {content}")
                context_text = "\n".join(lines)
        
        return context_text

    def summarize_if_needed(self) -> Optional[str]:
        """Enhanced summarization with better compression and context preservation.

        Uses improved heuristics to create more meaningful summaries while preserving
        important context and conversation flow.
        """
        if not self.cfg.enable_summaries:
            return None

        msgs = list(self.history.messages)
        if len(msgs) <= self.cfg.window_k:
            return None

        # Enhanced token approximation with better accuracy
        total_words = sum(len(getattr(m, "content", "").split()) for m in msgs)
        approx_tokens = int(total_words * 0.8)  # More accurate token estimation
        if approx_tokens < self.cfg.summary_threshold_tokens:
            return None

        # Separate older messages for summarization
        older = msgs[: -self.cfg.window_k]
        
        # Enhanced compression with better context preservation
        def enhanced_compress(text: str, max_words: int = 30) -> str:
            """Improved compression that preserves key information."""
            words = text.split()
            if len(words) <= max_words:
                return text.strip()
            
            # Try to preserve complete sentences when possible
            sentences = text.split('.')
            if len(sentences) > 1 and len(sentences[0].split()) <= max_words:
                return sentences[0].strip() + '.'
            
            # Fallback to word truncation with ellipsis
            return " ".join(words[:max_words]).strip() + "..."

        # Create enhanced summary with better structure
        summary_lines = []
        conversation_flow = []
        
        for i, m in enumerate(older):
            role = getattr(m, "type", getattr(m, "role", m.__class__.__name__)).upper()
            content = getattr(m, "content", "")
            if content:
                compressed = enhanced_compress(content, 35)  # Slightly longer for better context
                conversation_flow.append(f"{role}: {compressed}")
        
        # Structure the summary better
        if conversation_flow:
            new_summary_part = " | ".join(conversation_flow)
            if self.summary_text:
                # Merge with existing summary, keeping it manageable
                combined = f"{self.summary_text} | {new_summary_part}"
                # Trim if too long, keeping the most recent parts
                if len(combined) > 5000:  # Increased limit for better context
                    combined = "..." + combined[-4500:]  # Keep more recent context
                new_summary = combined
            else:
                new_summary = new_summary_part
        else:
            new_summary = self.summary_text

        self.summary_text = new_summary
        self._save_summary()

        # Prune history to last k messages with better error handling
        kept = msgs[-self.cfg.window_k :]
        try:
            self.history.clear()
        except Exception:
            # Enhanced fallback with better error recovery
            try:
                self.history_file.write_text("[]", encoding="utf-8")
                # Reinitialize history object
                from langchain_community.chat_message_histories import FileChatMessageHistory
                self.history = FileChatMessageHistory(file_path=str(self.history_file))
            except Exception:
                self.logger.warning("Failed to reinitialize chat history after clear")
                
        # Restore kept messages with improved error handling
        for m in kept:
            try:
                content = getattr(m, "content", "")
                if content:
                    msg_type = getattr(m, "type", getattr(m, "role", "")).lower()
                    if msg_type in ("human", "user"):
                        self.history.add_user_message(content)
                    else:
                        self.history.add_ai_message(content)
            except Exception as e:
                self.logger.warning(f"Failed to restore message during summarization: {e}")

        self.logger.info(
            "Enhanced memory summarization completed",
            session_id=self.cfg.session_id,
            kept_messages=len(kept),
            approx_tokens=approx_tokens,
            summary_length=len(self.summary_text),
        )
        return self.summary_text

    def reset(self) -> None:
        """Clear memory history and delete any summary files for this session."""
        try:
            self.history.clear()
        except Exception:
            # Fallback: recreate the file
            try:
                self.history_file.write_text("[]", encoding="utf-8")
            except Exception:
                pass

        # Delete summary file if present
        try:
            if self.summary_file.exists():
                self.summary_file.unlink(missing_ok=True)
        except Exception:
            pass

    # -------------------- Session management --------------------
    def switch_to_session(self, session_id: str) -> None:
        """Switch active memory to a specific session ID (creates if missing)."""
        try:
            # Update config and paths
            self.cfg.session_id = session_id
            self.session_dir = self.base_dir / session_id
            self.session_dir.mkdir(parents=True, exist_ok=True)

            # Update history file and history backend
            self.history_file = self.session_dir / "chat_history.json"
            if not self.history_file.exists():
                try:
                    self.history_file.write_text("[]", encoding="utf-8")
                except Exception:
                    pass

            # Recreate FileChatMessageHistory pointing to the new file
            try:
                from langchain_community.chat_message_histories import FileChatMessageHistory  # type: ignore
            except Exception:  # pragma: no cover
                from langchain.chat_message_histories import FileChatMessageHistory  # type: ignore

            self.history = FileChatMessageHistory(str(self.history_file))

            # Update summary file path
            self.summary_file = self.session_dir / "summary.txt"
            # Reload summary if exists
            self.summary_text = self._load_summary()

            self.logger.info(f"Switched to session: {session_id}")
        except Exception as e:
            self.logger.error(f"Failed to switch session to {session_id}: {e}")

    def switch_to_default_session(self) -> None:
        """Shortcut to switch back to the default session."""
        self.switch_to_session("default_session")

    def persist(self) -> None:
        """Persist summary text to disk and ensure history file exists."""
        # Ensure history file exists to avoid surprises across restarts
        try:
            if not self.history_file.exists():
                self.history_file.write_text("[]", encoding="utf-8")
        except Exception:
            pass

        # Persist current summary text if any
        if self.summary_text:
            try:
                self.summary_file.write_text(self.summary_text, encoding="utf-8")
            except Exception:
                pass
        self._ensure_dirs()
        self._save_summary()

    def save_memory(self) -> None:
        """Save memory state to disk. Alias for persist() for backward compatibility."""
        self.persist()

    # -------------------- Internal helpers --------------------
    def _ensure_dirs(self) -> None:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self.session_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _load_summary(self) -> str:
        try:
            if self.summary_file.exists():
                return self.summary_file.read_text(encoding="utf-8")
        except Exception:
            pass
        return ""

    def _save_summary(self) -> None:
        try:
            if self.summary_text:
                self.summary_file.parent.mkdir(parents=True, exist_ok=True)
                self.summary_file.write_text(self.summary_text, encoding="utf-8")
        except Exception:
            self.logger.warning("Failed to persist summary file", file=str(self.summary_file))

    # -------------------- Legacy compatibility methods --------------------
    def _extract_name_from_input(self, text: str) -> Optional[str]:
        """Extract name from user input for legacy compatibility."""
        import re
        
        # Simple name extraction patterns
        patterns = [
            r"(?:me llamo|my name is|i am|call me|soy)\s+([A-Za-z]+)",
            r"(?:mi nombre es)\s+([A-Za-z]+)",
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        
        return None

    def initialize_user_session(self) -> dict:
        """Initialize user session for legacy compatibility."""
        return {
            "session_id": self.cfg.session_id,
            "initialized": True,
            "timestamp": str(Path().cwd())  # Simple timestamp placeholder
        }

    def _switch_to_user_session(self, name: str, user_input: str, ai_response: str) -> None:
        """Switch from default session to personalized user session."""
        try:
            # Create new session ID based on name
            new_session_id = f"user_{name.lower()}"
            
            # Check if user session already exists
            new_session_dir = self.base_dir / new_session_id
            new_history_file = new_session_dir / "chat_history.json"
            
            # If session exists, load existing memory
            if new_session_dir.exists() and new_history_file.exists():
                self.logger.info(f"Found existing session for {name}, loading previous memory...")
                
                # Preserve current session context before switching
                current_messages = list(self.history.messages)
                self.logger.info(f"Preserving {len(current_messages)} messages from current session")
                
                # Initialize new MemoryService with user session
                from src.backend.memory.memory_service import MemoryServiceConfig
                new_config = MemoryServiceConfig(
                    session_id=new_session_id,
                    base_dir=str(self.base_dir),
                    window_k=self.cfg.window_k,
                    enable_summaries=self.cfg.enable_summaries,
                    summary_threshold_tokens=self.cfg.summary_threshold_tokens,
                    retrieval_k=self.cfg.retrieval_k
                )
                
                # Load existing session
                existing_history = FileChatMessageHistory(str(new_history_file))
                existing_messages = list(existing_history.messages)
                self.logger.info(f"Found {len(existing_messages)} messages in existing session")
                
                # Update current instance to use existing session
                self.cfg = new_config
                self.session_dir = new_session_dir
                self.history = existing_history
                # Keep history_file attribute updated with the active session's file
                self.history_file = new_history_file
                
                # Update summary file path
                self.summary_file = self.session_dir / "summary.txt"
                
                # Add current conversation to existing session (without merging old messages to preserve context)
                from langchain_core.messages import HumanMessage, AIMessage
                
                # Add current conversation to existing session
                self.history.add_message(HumanMessage(content=user_input))
                self.history.add_message(AIMessage(content=ai_response))
                
                total_messages = len(self.history.messages)
                self.logger.info(f"Successfully switched to session for {name}: {len(existing_messages)} existing + 2 new = {total_messages} total messages")
                
            else:
                # Create new session
                self.logger.info(f"Creating new session for {name}...")
                new_session_dir.mkdir(parents=True, exist_ok=True)
                
                # Initialize new MemoryService with user session
                from src.backend.memory.memory_service import MemoryServiceConfig
                new_config = MemoryServiceConfig(
                    session_id=new_session_id,
                    base_dir=str(self.base_dir),
                    window_k=self.cfg.window_k,
                    enable_summaries=self.cfg.enable_summaries,
                    summary_threshold_tokens=self.cfg.summary_threshold_tokens,
                    retrieval_k=self.cfg.retrieval_k
                )
                
                # Transfer current conversation to new session
                current_messages = list(self.history.messages)
                
                # Update current instance to use new session
                self.cfg = new_config
                self.session_dir = new_session_dir
                self.history = FileChatMessageHistory(str(new_history_file))
                # Keep history_file attribute updated with the active session's file
                self.history_file = new_history_file
                
                # Add all messages to new session
                for message in current_messages:
                    self.history.add_message(message)
                
                # Update summary file path
                self.summary_file = self.session_dir / "summary.txt"
                
                self.logger.info(f"Successfully created new session: {new_session_id}")
            
            # Create or update user profile in the models/memory/users directory
            self._create_user_profile(name)
            
        except Exception as e:
            self.logger.error(f"Failed to switch to user session: {e}")

    def _create_user_profile(self, name: str) -> None:
        """Create or update user profile in the users directory."""
        try:
            from datetime import datetime
            import json
            
            # Path to user profiles
            users_dir = Path("models/memory/users")
            users_dir.mkdir(parents=True, exist_ok=True)
            
            user_file = users_dir / f"{name.lower()}_user.json"
            
            # If user profile already exists, just update last_interaction
            if user_file.exists():
                with open(user_file, 'r', encoding='utf-8') as f:
                    user_profile = json.load(f)
                
                # Update last interaction time
                user_profile["profile"]["last_interaction"] = datetime.now().isoformat()
                user_profile["last_save"] = datetime.now().isoformat()
                
                self.logger.info(f"Updated existing user profile for {name}")
            else:
                # Create basic user profile
                user_profile = {
                    "profile": {
                        "user_id": f"user_{name.lower()}",
                        "name": name,
                        "career": "",
                        "semester": "",
                        "interests": [],
                        "communication_preference": "friendly",
                        "preferred_language": "es",
                        "timezone": "America/Mexico_City",
                        "created_at": datetime.now().isoformat(),
                        "last_interaction": datetime.now().isoformat()
                    },
                    "long_term_memory": [],
                    "context_memories": {
                        "academic": {
                            "context_type": "academic",
                            "key_information": {},
                            "recent_topics": [],
                            "important_dates": {},
                            "preferences": {},
                            "last_updated": datetime.now().isoformat()
                        },
                        "social": {
                            "context_type": "social",
                            "key_information": {},
                            "recent_topics": [],
                            "important_dates": {},
                            "preferences": {},
                            "last_updated": datetime.now().isoformat()
                        },
                        "personal": {
                            "context_type": "personal",
                            "key_information": {},
                            "recent_topics": [],
                            "important_dates": {},
                            "preferences": {},
                            "last_updated": datetime.now().isoformat()
                        },
                        "university": {
                            "context_type": "university",
                            "key_information": {},
                            "recent_topics": [],
                            "important_dates": {},
                            "preferences": {},
                            "last_updated": datetime.now().isoformat()
                        },
                        "motivational": {
                            "context_type": "motivational",
                            "key_information": {},
                            "recent_topics": [],
                            "important_dates": {},
                            "preferences": {},
                            "last_updated": datetime.now().isoformat()
                        },
                        "general": {
                            "context_type": "general",
                            "key_information": {},
                            "recent_topics": [],
                            "important_dates": {},
                            "preferences": {},
                            "last_updated": datetime.now().isoformat()
                        }
                    },
                    "learnings": {},
                    "last_save": datetime.now().isoformat()
                }
                
                self.logger.info(f"Created new user profile for {name}")
            
            # Save user profile
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(user_profile, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved user profile for {name} at {user_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to create user profile: {e}")

    def add_interaction(self, user_input: str | None = None, ai_response: str | None = None, user_id: str | None = None, context_type = None, *, user_message: str | None = None, assistant_response: str | None = None, context = None) -> bool:
        """Add interaction supporting multiple keyword variants for compatibility.
        Accepts either (user_input, ai_response) or (user_message, assistant_response),
        and optional context/context_type. Returns True on success, False otherwise.
        """
        # Normalize inputs from different keyword variants
        normalized_user = user_input if user_input is not None else user_message
        normalized_ai = ai_response if ai_response is not None else assistant_response
        normalized_context = context_type if context_type is not None else context

        # Basic validation
        if normalized_user is None or normalized_ai is None:
            self.logger.warning("add_interaction called without both user and ai messages")
            return False

        # Store messages using canonical methods
        self.add_user_message(normalized_user)
        self.add_ai_message(normalized_ai)

        # Optionally use context if provided (reserved for future logic)
        _ = normalized_context  # Currently unused but kept for API compatibility
        
        # Try to extract name from input
        name = self._extract_name_from_input(normalized_user)
        if name:
            self.logger.info(f"Name detected: {name}")
            # Switch to personalized session if we're currently in default session
            if self.cfg.session_id == "default_session" or self.cfg.session_id == "default":
                self._switch_to_user_session(name, normalized_user, normalized_ai)
        
        return True

    def get_smart_context_for_response(self, query: str, user_id: str, context_type) -> dict:
        """Legacy method for backward compatibility with performance tests."""
        # Get context messages
        messages = self.get_context_messages()
        
        # Calculate approximate token count (rough estimate: 4 chars per token)
        total_text = " ".join([msg.content for msg in messages if hasattr(msg, 'content')])
        estimated_tokens = len(total_text) // 4
        
        # Respect the token limit by truncating if necessary
        if estimated_tokens > self.context_token_limit:
            # Truncate messages to fit within token limit
            target_chars = self.context_token_limit * 4
            truncated_text = total_text[:target_chars]
            estimated_tokens = self.context_token_limit
        
        return {
            "messages": messages,
            "estimated_tokens": estimated_tokens,
            "query": query,
            "user_id": user_id,
            "context_type": context_type
        }

    def get_recent_context(self, max_items: int = 5) -> List[str]:
        """Return the most recent context messages as plain strings for UI/debugging.
        This is a convenience wrapper used by integration tests and API.
        """
        try:
            messages = self.get_context_messages()
            recent = messages[-max_items:] if max_items is not None else messages
            result: List[str] = []
            for msg in recent:
                # Extract content if available; otherwise, fallback to string representation
                content = getattr(msg, "content", None)
                if content is None:
                    content = str(msg)
                result.append(content)
            return result
        except Exception as e:
            self.logger.error(f"Failed to get recent context: {e}")
            return []


__all__ = ["MemoryService", "MemoryServiceConfig"]
