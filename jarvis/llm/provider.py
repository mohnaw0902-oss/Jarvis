"""Provider-neutral LLM protocol and OpenAI-compatible implementation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, Protocol

import httpx

from jarvis.models.contracts import ChatMessage


class LLMProvider(Protocol):
    async def complete(self, messages: list[ChatMessage]) -> str: ...
    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]: ...


class OpenAICompatibleProvider:
    """OpenAI Chat Completions adapter, including Server-Sent Event streaming."""

    def __init__(self, base_url: str, api_key: str, model: str, temperature: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._temperature = temperature

    def _payload(self, messages: list[ChatMessage], stream: bool = False) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [item.model_dump(mode="json", exclude={"created_at"}) for item in messages],
            "temperature": self._temperature,
            "stream": stream,
        }

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def complete(self, messages: list[ChatMessage]) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=self._payload(messages),
                headers=self._headers,
            )
            response.raise_for_status()
        return str(response.json()["choices"][0]["message"]["content"])

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=self._payload(messages, stream=True),
                headers=self._headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ")
                    if data == "[DONE]":
                        return
                    payload = json.loads(data)
                    content = payload.get("choices", [{}])[0].get("delta", {}).get("content")
                    if isinstance(content, str) and content:
                        yield content


class UnconfiguredProvider:
    async def complete(self, messages: list[ChatMessage]) -> str:
        return (
            "The LLM provider is not configured. Set JARVIS_LLM_BASE_URL, "
            "JARVIS_LLM_MODEL, and JARVIS_LLM_API_KEY."
        )

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        yield await self.complete(messages)
