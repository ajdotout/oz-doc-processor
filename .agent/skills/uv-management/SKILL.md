---
name: uv-management
description: Mandatory use of `uv` for all Python-related tasks in the `oz-doc-processor` repository, including dependency management and script execution.
---

# Python Management with `uv`

This repository uses `uv` for ultra-fast Python package and project management. As an AI agent, you **MUST** use `uv` for all Python operations to ensure consistency and speed.

## Core Directives

1. **Always use `uv run`**: Never execute Python scripts directly with `python` or `python3`. Always use `uv run python path/to/script.py`. This ensures the script runs in the correctly managed environment with all dependencies available.
2. **Dependency Management**:
   - To add a dependency: `uv add [package]`
   - To remove a dependency: `uv remove [package]`
   - To add a dev dependency: `uv add --dev [package]`
3. **Environment Synchronization**: If you modify `pyproject.toml` or notice `uv.lock` is out of sync, run `uv sync` to update the local `.venv`.
4. **Tool Execution**: Use `uvx` (or `uv tool run`) for running one-off tools without installing them into the project (e.g., `uvx ruff check .`).

## Workflows

### Running a Script
```bash
uv run python pipeline.py
```

### Adding a New Library
```bash
uv add pandas
```

### Initializing/Updating the Environment
```bash
uv sync
```

## Why `uv`?
- **Speed**: `uv` is significantly faster than `pip` and `poetry`.
- **Reproducibility**: The `uv.lock` file ensures everyone (and the agent) uses the exact same versions.
- **Simplicity**: No need to manually manage virtualenvs; `uv` handles it automatically.
