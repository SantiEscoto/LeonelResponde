import importlib
import importlib.util
from pathlib import Path
from typing import List

import pytest

# Attempt to import the memory module and skip the entire test module if unavailable
try:
    memory_mod = importlib.import_module("backend.memory.memory_service")
except Exception as e:  # ImportError or runtime deps missing
    pytest.skip(f"LangChain memory not available: {e}", allow_module_level=True)
else:
    MemoryService = getattr(memory_mod, "MemoryService")


@pytest.fixture()
def memory_service(tmp_path: Path):
    def _factory(
        session_id: str = "test-session",
        base_dir: Path = tmp_path,
        window_k: int = 3,
        enable_summaries: bool = True,
        summary_threshold_tokens: int = 50,
        retrieval_k: int = 3,
    ) -> "MemoryService":
        return MemoryService(
            session_id=session_id,
            base_dir=str(base_dir),
            window_k=window_k,
            enable_summaries=enable_summaries,
            summary_threshold_tokens=summary_threshold_tokens,
            retrieval_k=retrieval_k,
        )

    return _factory


def _roles_of(messages: List[object]) -> List[str]:
    roles: List[str] = []
    for m in messages:
        role = getattr(m, "type", getattr(m, "role", m.__class__.__name__)).lower()
        roles.append(role)
    return roles


def _contents_of(messages: List[object]) -> List[str]:
    return [getattr(m, "content", "") for m in messages]


def test_persistence_across_restarts(memory_service, tmp_path: Path) -> None:
    svc1 = memory_service(session_id="persist1", base_dir=tmp_path, window_k=2)

    svc1.add_user_message("hello")
    svc1.add_ai_message("hi there")
    svc1.add_user_message("how are you?")
    # Ensure metadata files exist
    svc1.persist()

    # Recreate service simulating restart
    svc2 = memory_service(session_id="persist1", base_dir=tmp_path, window_k=2)

    ctx = svc2.get_context_messages()
    assert len(ctx) == 2
    # Expect last two messages in order
    assert _roles_of(ctx) == ["ai", "human"] or _roles_of(ctx) == ["ai", "user"]
    assert _contents_of(ctx) == ["hi there", "how are you?"]


def test_summarization_prunes_history(memory_service, tmp_path: Path) -> None:
    svc = memory_service(
        session_id="sum1",
        base_dir=tmp_path,
        window_k=2,
        enable_summaries=True,
        summary_threshold_tokens=10,  # very low to trigger easily
    )

    # Add enough content to cross threshold
    for i in range(6):
        svc.add_user_message(f"user says something long {i} " + ("words " * 5))
        svc.add_ai_message(f"ai responds with detail {i} " + ("tokens " * 5))

    summary = svc.summarize_if_needed()
    assert summary is not None and len(summary) > 0

    # Underlying history should be pruned to last k messages
    ctx = svc.get_context_messages()
    assert len(ctx) == 2

    # Summary file should exist and be non-empty
    assert svc.summary_file.exists()
    assert len(svc.summary_file.read_text(encoding="utf-8")) > 0


def test_reset_clears_files(memory_service, tmp_path: Path) -> None:
    svc = memory_service(session_id="reset1", base_dir=tmp_path, window_k=2)

    svc.add_user_message("hello")
    svc.add_ai_message("hi")
    svc.persist()

    # Files should exist after persist (history file created by LC, summary may be empty)
    assert svc.history_file.exists()

    # Write a summary then reset
    svc.summary_text = "some summary"
    svc.persist()
    assert svc.summary_file.exists()

    # Reset should clear history and delete summary file
    svc.reset()

    # History file may be deleted or truncated to [] by fallback
    if svc.history_file.exists():
        assert svc.history_file.read_text(encoding="utf-8").strip() in {"[]", ""}
    # Summary file should be gone
    assert not svc.summary_file.exists()
