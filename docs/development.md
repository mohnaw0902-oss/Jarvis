# Development and validation

## Local environment

Use Python 3.13+ and install the declared runtime and development dependencies before running checks:

```bash
uv sync --extra dev
```

The service reads local settings from `.env`. Copy `.env.example` and leave credential values blank until secrets are supplied through your local environment or deployment secret manager.

## Required validation

Run the complete validation sequence before opening a pull request:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy jarvis
uv run pytest
```

`pytest` uses a temporary SQLite database and does not require an LLM credential. Provider behavior is isolated behind `LLMProvider` test doubles; unit tests must not make network calls.

## Development rules

Keep I/O async, maintain strict type annotations on package code, and compose dependencies in `create_application` rather than introducing global state. New tools must be registered through `ToolManager` so validation, confirmation, rate limiting, and structured execution logs are retained.
