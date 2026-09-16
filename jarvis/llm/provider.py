"""Provider-neutral interface and OpenAI-compatible Responses API adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from jarvis.models.contracts import ChatMessage


class ToolCall(BaseModel):
    """A provider-requested function invocation."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Normalized non-streaming model output."""

    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)


class LLMProvider(Protocol):
    @staticmethod
    def _to_responses_input(message: ChatMessage) -> dict[str, Any]:
        if message.role != "tool":
            return {"role": message.role, "content": message.content}
        payload = json.loads(message.content)
        return {
            "type": "function_call_output",
            "call_id": payload["call_id"],
            "output": json.dumps(payload),
        }

    async def respond(
        self, messages: list[ChatMessage], tools: list[dict[str, Any]]
    ) -> LLMResponse: ...

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]: ...


class OpenAIResponsesProvider:
    """Adapter for OpenAI-compatible `/responses` endpoints."""

    def __init__(self, base_url: str, api_key: str, model: str, temperature: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._temperature = temperature

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _payload(
        self, messages: list[ChatMessage], tools: list[dict[str, Any]], stream: bool = False
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "input": [self._to_responses_input(message) for message in messages],
            "tools": [
                {
                    "type": "function",
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                }
                for tool in tools
            ],
            "temperature": self._temperature,
            "stream": stream,
        }

    async def respond(
        self, messages: list[ChatMessage], tools: list[dict[str, Any]]
    ) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/responses",
                json=self._payload(messages, tools),
                headers=self._headers,
            )
            response.raise_for_status()
        return self._parse_response(response.json())

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/responses",
                json=self._payload(messages, [], stream=True),
                headers=self._headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line.removeprefix("data: "))
                    if event.get("type") == "response.output_text.delta":
                        delta = event.get("delta")
                        if isinstance(delta, str):
                            yield delta

    @staticmethod
    def _parse_response(payload: dict[str, Any]) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for item in payload.get("output", []):
            if item.get("type") == "function_call":
                raw_arguments = item.get("arguments", "{}")
                try:
                    arguments = (
                        json.loads(raw_arguments)
                        if isinstance(raw_arguments, str)
                        else raw_arguments
                    )
                except json.JSONDecodeError:
                    arguments = {}
                if isinstance(arguments, dict):
                    tool_calls.append(
                        ToolCall(
                            id=str(item.get("call_id", item.get("id", ""))),
                            name=str(item["name"]),
                            arguments=arguments,
                        )
                    )
            elif item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text" and isinstance(
                        content.get("text"), str
                    ):
                        text_parts.append(content["text"])
        return LLMResponse(text="".join(text_parts), tool_calls=tool_calls)


class UnconfiguredProvider:
    async def respond(
        self, messages: list[ChatMessage], tools: list[dict[str, Any]]
    ) -> LLMResponse:
        return LLMResponse(
            text=(
                "The LLM provider is not configured. Set JARVIS_LLM_BASE_URL, "
                "JARVIS_LLM_MODEL, and JARVIS_LLM_API_KEY."
            )
        )

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        yield (await self.respond(messages, [])).text
