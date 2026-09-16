# Architecture

## Dependency graph

The composition root, `jarvis.core.application.create_application`, creates settings, the async database engine, session factory, memory manager, LLM provider, tool manager, and brain. Adapters receive this composed application rather than creating their own dependencies.

```text
Settings -> Application -> {Database, MemoryManager, LLMProvider, ToolManager} -> Brain -> API / CLI
```

## Request flow

1. The API validates a `ChatRequest` and passes it to `Brain`.
2. `Brain` persists the user message and optionally selects a deterministic workflow.
3. The brain sends all tool requests through `ToolManager`; it never invokes a tool class directly.
4. `ToolManager` validates Pydantic parameters, rate-limits calls, asks for confirmation when the tool policy requires it, and returns a typed `ToolResult`.
5. The brain either returns a validated tool result or sends conversation history to the configured LLM provider, then persists the assistant message.

## Safety boundaries

- Providers receive message content only; application configuration and secrets are not placed in prompts.
- Filesystem targets are resolved under `JARVIS_WORKSPACE_ROOT`; traversal outside that directory is rejected.
- Tool failures are converted to non-sensitive results rather than exposing tracebacks to API clients.
- The unconfigured LLM provider avoids accidental outbound requests when configuration is incomplete.
