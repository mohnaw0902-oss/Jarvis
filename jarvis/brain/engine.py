"""Reasoning workflow coordinating memory, LLM responses, and guarded tools."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from loguru import logger

from jarvis.llm.provider import LLMProvider
from jarvis.memory.manager import MemoryManager
from jarvis.models.contracts import ChatMessage, ChatResponse
from jarvis.tools.manager import ToolManager

_CALCULATION = re.compile(r"^(?:calculate|compute)\s+(.+)$", re.IGNORECASE)
_MAX_TOOL_ROUNDS = 3
_SYSTEM_PROMPT = (
    "You are JARVIS: accurate, concise, privacy-aware. Use available tools when they improve "
    "accuracy. Never claim an action completed when a tool reports failure or needs confirmation."
)


class Brain:
    """Application service that owns conversation reasoning, not tool implementation."""

    def __init__(self, provider: LLMProvider, memory: MemoryManager, tools: ToolManager) -> None:
        self._provider = provider
        self._memory = memory
        self._tools = tools

    async def respond(self, message: str, conversation_id: UUID | None = None) -> ChatResponse:
        identifier = conversation_id or uuid4()
        await self._memory.save(identifier, ChatMessage(role="user", content=message))
        history = await self._memory.recall(identifier)
        answer, tools_used = await self._reason(history)
        await self._memory.save(identifier, ChatMessage(role="assistant", content=answer))
        return ChatResponse(conversation_id=identifier, message=answer, tools_used=tools_used)

    async def stream(self, message: str, conversation_id: UUID | None = None) -> AsyncIterator[str]:
        """Persist input and yield provider text chunks for responses that do not need a tool."""
        identifier = conversation_id or uuid4()
        await self._memory.save(identifier, ChatMessage(role="user", content=message))
        history = await self._memory.recall(identifier)
        chunks: list[str] = []
        async for chunk in self._provider.stream(
            [ChatMessage(role="system", content=_SYSTEM_PROMPT), *history]
        ):
            chunks.append(chunk)
            yield chunk
        await self._memory.save(identifier, ChatMessage(role="assistant", content="".join(chunks)))

    async def _reason(self, history: list[ChatMessage]) -> tuple[str, list[str]]:
        deterministic = await self._try_deterministic_tool(history[-1].content)
        if deterministic is not None:
            return deterministic

        working_messages = [ChatMessage(role="system", content=_SYSTEM_PROMPT), *history]
        used_tools: list[str] = []
        for round_number in range(_MAX_TOOL_ROUNDS):
            response = await self._provider.respond(working_messages, self._tools.descriptions())
            if not response.tool_calls:
                return response.text or "I could not produce a response.", used_tools
            logger.info("brain_tool_round", round=round_number + 1, calls=len(response.tool_calls))
            for call in response.tool_calls:
                result = await self._tools.execute(call.name, call.arguments)
                used_tools.append(call.name)
                if result.requires_confirmation:
                    return result.error or "Confirmation is required.", used_tools
                working_messages.append(
                    ChatMessage(
                        role="tool",
                        content=json.dumps(
                            {
                                "call_id": call.id,
                                "name": call.name,
                                "output": result.output,
                                "error": result.error,
                            },
                            default=str,
                        ),
                    )
                )
        return "I stopped because the tool workflow exceeded its safety limit.", used_tools

    async def _try_deterministic_tool(self, message: str) -> tuple[str, list[str]] | None:
        match = _CALCULATION.fullmatch(message.strip())
        if match is None:
            return None
        result = await self._tools.execute("calculator", {"expression": match.group(1)})
        if result.success:
            return str(result.output), ["calculator"]
        return result.error or "The calculation could not be completed.", ["calculator"]
