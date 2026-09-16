# Development

Use `uv sync --extra dev`, then run `uv run pytest`, `uv run ruff check .`, and `uv run mypy jarvis`. Add integrations behind protocols and inject them from the composition root. Keep I/O async and return typed Pydantic models at boundaries.
