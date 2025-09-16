"""
MemoryService: lightweight conversational memory built on LangChain primitives
- ConversationBufferWindowMemory backed by FileChatMessageHistory for on-disk persistence
- Optional simple summarization to control token growth (offline heuristic)

This module is intentionally dependency-light and runs fully offline.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

try:
    # Core memory container (stable import path)
    from langchain.memory import ConversationBufferWindowMemory
    # File-backed chat history (commonly provided by langchain_community)
    try:
        from langchain_community.chat_message_histories import FileChatMessageHistory
    except Exception:  # pragma: no cover - fallback for older distros
        from langchain.chat_message_histories import FileChatMessageHistory  # type: ignore

    from langchain.schema import BaseMessage
except Exception as e:  # pragma: no cover
    raise ImportError(
        "LangChain memory dependencies are missing. Install: \n"
        "  pip install langchain langchain-community\n"
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

    def __init__(self, session_id: str, base_dir: str, window_k: int,
                 enable_summaries: bool, summary_threshold_tokens: int,
                 retrieval_k: int) -> None:
        from backend.utils.unified_logger import get_unified_logger

        self.logger = get_unified_logger("MemoryService")
        self.cfg = MemoryServiceConfig(
            base_dir=Path(base_dir),
            session_id=session_id,
            window_k=window_k,
            enable_summaries=enable_summaries,
            summary_threshold_tokens=summary_threshold_tokens,
            retrieval_k=retrieval_k,
        )

        # Prepare directories
        self.base_dir: Path = self.cfg.base_dir
        self.sessions_dir: Path = self.base_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Files for this session
        self.history_file: Path = self.sessions_dir / f"{self.cfg.session_id}.json"
        self.summary_file: Path = self.base_dir / f"{self.cfg.session_id}.summary.txt"

        # Initialize file-backed history and windowed memory
        self.history = FileChatMessageHistory(file_path=str(self.history_file))
        self.memory = ConversationBufferWindowMemory(
            k=self.cfg.window_k,
            return_messages=True,
            chat_memory=self.history,
        )

        # Load summary if it exists
        self.summary_text: str = self._load_summary()
        self.logger.info(
            "LangChain MemoryService initialized",
            session_id=self.cfg.session_id,
            base_dir=str(self.base_dir),
            window_k=self.cfg.window_k,
            summaries=self.cfg.enable_summaries,
        )

    # -------------------- Public API --------------------
    def add_user_message(self, text: str) -> None:
        """Append a user message to persistent history."""
        self.memory.chat_memory.add_user_message(text)
        # FileChatMessageHistory persists on write; still ensure dir integrity
        self._ensure_dirs()

    def add_ai_message(self, text: str) -> None:
        """Append an AI message to persistent history."""
        self.memory.chat_memory.add_ai_message(text)
        self._ensure_dirs()

    def get_context_messages(self) -> List[BaseMessage]:
        """Return the current window of messages used for prompting."""
        # ConversationBufferWindowMemory already limits to k for .buffer,
        # but the underlying history contains all messages. We slice explicitly.
        msgs = list(self.history.messages)
        if self.cfg.window_k > 0:
            msgs = msgs[-self.cfg.window_k :]
        return msgs

    def get_context_as_text(self) -> str:
        """Return a human-readable transcript (role: content) for prompt context."""
        lines: List[str] = []
        if self.summary_text:
            lines.append(f"[Summary]\n{self.summary_text.strip()}")
        for m in self.get_context_messages():
            role = getattr(m, "type", getattr(m, "role", m.__class__.__name__)).upper()
            content = getattr(m, "content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def summarize_if_needed(self) -> Optional[str]:
        """Heuristically summarize older messages and prune if threshold exceeded.

        Offline heuristic: approximate tokens as words*0.75. If older+current exceeds
        threshold, compress older messages into a textual summary and keep last k.
        """
        if not self.cfg.enable_summaries:
            return None

        msgs = list(self.history.messages)
        if len(msgs) <= self.cfg.window_k:
            return None

        # Token approximation (very lightweight)
        total_words = sum(len(getattr(m, "content", "").split()) for m in msgs)
        approx_tokens = int(total_words * 0.75)
        if approx_tokens < self.cfg.summary_threshold_tokens:
            return None

        older = msgs[:-self.cfg.window_k]
        # Simple compression: keep first sentence or first ~24 words per message
        def compress(text: str, max_words: int = 24) -> str:
            words = text.split()
            return " ".join(words[:max_words]).strip()

        summary_lines = []
        for m in older:
            role = getattr(m, "type", getattr(m, "role", m.__class__.__name__)).upper()
            content = getattr(m, "content", "")
            if content:
                summary_lines.append(f"{role}: {compress(content)}")
        new_summary = (self.summary_text + "\n" if self.summary_text else "") + " | ".join(summary_lines)
        # Trim very long summary to avoid unbounded growth
        if len(new_summary) > 4000:
            new_summary = new_summary[-4000:]

        self.summary_text = new_summary
        self._save_summary()

        # Prune history to last k messages
        kept = msgs[-self.cfg.window_k :]
        try:
            self.history.clear()  # type: ignore[attr-defined]
        except Exception:
            # Fallback: recreate the file
            try:
                self.history_file.write_text("[]", encoding="utf-8")
            except Exception:
                pass
        for m in kept:
            content = getattr(m, "content", "")
            if getattr(m, "type", getattr(m, "role", "")).lower() in ("human", "user"):
                self.history.add_user_message(content)
            else:
                self.history.add_ai_message(content)

        self.logger.info(
            "Memory summarized and pruned",
            session_id=self.cfg.session_id,
            kept=len(kept),
            approx_tokens=approx_tokens,
        )
        return self.summary_text

    def reset(self) -> None:
        """Clear memory history and delete any summary files for this session."""
        try:
            self.history.clear()
        except Exception:
            # Best-effort clear: truncate the underlying file
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

    # -------------------- Internal helpers --------------------
    def _ensure_dirs(self) -> None:
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
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


__all__ = ["MemoryService", "MemoryServiceConfig"]
