# JARVIS AI Assistant

JARVIS is an async-first, security-conscious backend foundation for a desktop AI assistant. It provides a typed API, persistent conversations, provider-neutral LLM integration, and a guarded plugin system designed to grow into voice, vision, automation, coding, and web-assistance features.

> **Current scope:** this repository intentionally provides the core platform and three safe built-in tools. Voice, vision, browser, operating-system automation, and third-party providers are extension packages planned on top of these contracts; they are not represented as non-functional placeholder tools.

## Features

- **Typed, composable architecture:** Pydantic contracts, async SQLAlchemy persistence, and a dependency-injected composition root.
- **Secure tool boundary:** the brain delegates every tool call to `ToolManager`, which validates inputs, enforces confirmation policies, and rate-limits execution.
- **Persistent conversation memory:** SQLite is the default; the database URL is environment-configurable.
- **LLM portability:** a protocol-based provider boundary includes OpenAI-compatible APIs and a safe unconfigured fallback.
- **Local API:** FastAPI endpoints and a WebSocket chat endpoint are ready for a desktop interface.

## Requirements

- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync --extra dev
cp .env.example .env
uv run jarvis serve
```

The service listens on `http://127.0.0.1:8000` by default. Interactive API documentation is available at [`/docs`](http://127.0.0.1:8000/docs).

### Configure an OpenAI-compatible provider

All configuration is loaded from environment variables. Set these values in your local `.env` file or deployment environment:

```dotenv
JARVIS_LLM_BASE_URL=https://provider.example/v1
JARVIS_LLM_MODEL=your-model-name
JARVIS_LLM_API_KEY=your-secret-managed-key
```

`JARVIS_LLM_API_KEY` is intentionally blank in `.env.example`; never commit credentials. If the provider settings are absent, JARVIS responds with a configuration message instead of attempting a network call.

## API examples

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/tools
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"calculate 2 * (3 + 4)"}'
```

The `/v1/ws/chat` WebSocket accepts JSON `ChatRequest` payloads and returns JSON `ChatResponse` payloads.

## Built-in tools

| Tool | Capability | Safety behavior |
| --- | --- | --- |
| `calculator` | Evaluates basic arithmetic using a restricted AST. | Does not use `eval`. |
| `clock` | Returns the current UTC timestamp. | No side effects. |
| `filesystem` | Reads, writes, and deletes files under `JARVIS_WORKSPACE_ROOT`. | Refuses path traversal, constrains read size, and requires explicit confirmation for deletion. |
| `terminal` | Runs non-interactive commands in the configured workspace. | Avoids a shell; destructive, privileged, and package-install commands require confirmation. |

## Development

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy jarvis
uv run pytest
```

## Documentation

- [Architecture overview](docs/architecture.md)
- [Development guide](docs/development.md)
- [Tool creation guide](docs/tool-creation.md)

## Security model

Secrets are read from the environment and are not logged. Tool parameters are validated before execution. Destructive filesystem actions are confirmation-gated, and the filesystem tool resolves every target against its configured workspace root. Future integrations must preserve the same policy boundary by registering with `ToolManager` rather than being called from the brain directly.
