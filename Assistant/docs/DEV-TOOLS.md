# Dev Tools Guide (Tests, Type Checking, Linting)

This repository includes optional and development configurations to prepare Phases C and D.
No automated linting or type-fixing is executed yet; this guide is for local usage only.

## 1) Install Optional and Dev Dependencies

- Optional (LangChain-based memory):
  pip install -r requirements-optional.txt

- Dev tools (pytest, mypy, ruff, black):
  pip install -r requirements-dev.txt

Note: Keep these in your virtual environment. Optional deps are not required for CI.

## 2) Run Tests

- Run the full test suite quietly:
  pytest -q

- Notes:
  - MemoryService tests will be skipped if LangChain is not installed.
  - To run them, install optional dependencies above.

## 3) Run Type Checking (to be executed after approval)

- Check only critical modules as configured in mypy.ini:
  mypy --config-file mypy.ini backend/memory backend/utils

- You can broaden the scope later (Phase C) after PR approval.

## 4) Run Linting (to be executed after approval)

- Ruff (lint):
  ruff check .

- Black (format check):
  black --check .

- Formatting (only after approval):
  black .

## 5) Pytest Warning Filters

Warning filters are configured in pytest.ini to ignore noisy third-party warnings while keeping project warnings visible.
