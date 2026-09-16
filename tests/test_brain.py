from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from jarvis.brain.engine import Brain
from jarvis.llm.provider import LLMResponse, ToolCall
from jarvis.memory.manager import MemoryManager
from jarvis.models.contracts import ChatMessage
from jarvis.tools.builtin.clock import ClockTool
from jarvis.tools.manager import ToolManager


class ToolCallingProvider:
    async def respond(
        self, messages: list[ChatMessage], tools: list[dict[str, object]]
    ) -> LLMResponse:
        if any(message.role == "tool" for message in messages):
            return LLMResponse(text="The clock tool completed.")
        return LLMResponse(tool_calls=[ToolCall(id="call_1", name="clock", arguments={})])

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        yield "streamed"


@pytest.mark.asyncio
async def test_brain_uses_provider_selected_tool(session_factory) -> None:
    tools = ToolManager(rate_limit_per_minute=3)
    tools.register(ClockTool())
    brain = Brain(ToolCallingProvider(), MemoryManager(session_factory), tools)

    response = await brain.respond("What time is it?")

    assert response.message == "The clock tool completed."
    assert response.tools_used == ["clock"]


@pytest.mark.asyncio
async def test_brain_streams_and_persists_response(session_factory) -> None:
    tools = ToolManager(rate_limit_per_minute=3)
    brain = Brain(ToolCallingProvider(), MemoryManager(session_factory), tools)

    chunks = [chunk async for chunk in brain.stream("Hello")]

    assert chunks == ["streamed"]


def test_responses_provider_parses_text_and_function_calls() -> None:
    from jarvis.llm.provider import OpenAIResponsesProvider

    response = OpenAIResponsesProvider._parse_response(
        {
            "output": [
                {"type": "function_call", "call_id": "call_1", "name": "clock", "arguments": "{}"},
                {"type": "message", "content": [{"type": "output_text", "text": "Done."}]},
            ]
        }
    )

    assert response.text == "Done."
    assert response.tool_calls == [ToolCall(id="call_1", name="clock", arguments={})]
