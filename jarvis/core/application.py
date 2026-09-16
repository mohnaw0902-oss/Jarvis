"""Dependency-injection composition root."""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.brain.engine import Brain
from jarvis.config.settings import Settings
from jarvis.database.session import AsyncEngine, create_schema, create_session_factory
from jarvis.llm.provider import LLMProvider, OpenAICompatibleProvider, UnconfiguredProvider
from jarvis.memory.manager import MemoryManager
from jarvis.tools.builtin.calculator import CalculatorTool
from jarvis.tools.builtin.clock import ClockTool
from jarvis.tools.builtin.filesystem import FilesystemTool
from jarvis.tools.builtin.terminal import TerminalTool
from jarvis.tools.manager import ToolManager
from jarvis.utils.logging import configure_logging


@dataclass(slots=True)
class Application:
    settings: Settings
    engine: AsyncEngine
    brain: Brain
    tools: ToolManager

    async def start(self) -> None:
        await create_schema(self.engine)

    async def stop(self) -> None:
        await self.engine.dispose()


def create_application(settings: Settings | None = None) -> Application:
    current = settings or Settings()
    configure_logging(current.log_level)
    engine, sessions = create_session_factory(current.database_url)
    provider: LLMProvider = UnconfiguredProvider()
    if current.llm_base_url and current.llm_model and current.llm_api_key:
        provider = OpenAICompatibleProvider(
            current.llm_base_url,
            current.llm_api_key.get_secret_value(),
            current.llm_model,
            current.llm_temperature,
        )
    tools = ToolManager(current.tool_rate_limit_per_minute)
    tools.register(CalculatorTool())
    tools.register(ClockTool())
    tools.register(FilesystemTool(current.workspace_root, current.max_file_read_bytes))
    tools.register(TerminalTool(current.workspace_root))
    return Application(current, engine, Brain(provider, MemoryManager(sessions), tools), tools)
