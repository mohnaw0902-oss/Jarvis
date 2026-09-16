"""Reasoning orchestration. Tool access remains exclusively behind ToolManager."""

from __future__ import annotations

import re
from uuid import UUID, uuid4

from jarvis.llm.provider import LLMProvider
from jarvis.memory.manager import MemoryManager
from jarvis.models.contracts import ChatMessage, ChatResponse
from jarvis.tools.manager import ToolManager

_CALCULATION = re.compile(r"^(?:calculate|compute)\s+(.+)$", re.IGNORECASE)


class Brain:
    """Coordinates history, deterministic tool selection, output validation, and LLM response."""

    def __init__(self, provider: LLMProvider, memory: MemoryManager, tools: ToolManager) -> None:
        self._provider, self._memory, self._tools = provider, memory, tools

    async def respond(self, message: str, conversation_id: UUID | None = None) -> ChatResponse:
        identifier = conversation_id or uuid4()
        incoming = ChatMessage(role="user", content=message)
        await self._memory.save(identifier, incoming)
        tool_name, tool_output = await self._try_tool(message)
        if tool_output is not None:
            answer = tool_output
        else:
            history = await self._memory.recall(identifier)
            system = ChatMessage(
                role="system",
                content=(
                    "You are JARVIS: accurate, concise, privacy-aware. "
                    "Request confirmation for dangerous actions."
                ),
            )
            answer = await self._provider.complete([system, *history])
        await self._memory.save(identifier, ChatMessage(role="assistant", content=answer))
        return ChatResponse(
            conversation_id=identifier, message=answer, tools_used=[tool_name] if tool_name else []
        )

    async def _try_tool(self, message: str) -> tuple[str | None, str | None]:
        match = _CALCULATION.fullmatch(message.strip())
        if match is None:
            return None, None
        result = await self._tools.execute("calculator", {"expression": match.group(1)})
        if result.success:
            return "calculator", str(result.output)
        return "calculator", result.error or "The calculation could not be completed."
