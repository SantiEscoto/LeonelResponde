import os
import importlib
import importlib.util
from contextlib import contextmanager

import pytest

# Skip if LangChain not installed? Not required for this config toggle test.


@contextmanager
def env_overrides(**env):
    old = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            if v is None and k in os.environ:
                del os.environ[k]
            elif v is not None:
                os.environ[k] = str(v)
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _reload_config_module():
    # Import here to avoid path issues
    from backend.utils import unified_config as uc
    importlib.reload(uc)
    return uc


def test_toggle_flag_by_env(monkeypatch):
    # Ensure clean env
    monkeypatch.delenv("ENABLE_LANGCHAIN_MEMORY", raising=False)
    uc = _reload_config_module()
    cfg = uc.get_config()
    assert cfg.memory.langchain.enable is False

    # Enable via env and reload
    with env_overrides(ENABLE_LANGCHAIN_MEMORY="1"):
        uc = _reload_config_module()
        cfg = uc.reload_config()
        assert cfg.memory.langchain.enable is True

    # Disable again
    monkeypatch.delenv("ENABLE_LANGCHAIN_MEMORY", raising=False)
    uc = _reload_config_module()
    cfg = uc.reload_config()
    assert cfg.memory.langchain.enable is False
