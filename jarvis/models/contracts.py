"""Stable boundary models shared by API, brain, tools, and providers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(min_length=1, max_length=100_000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=20_000)


class ChatResponse(BaseModel):
    conversation_id: UUID = Field(default_factory=uuid4)
    message: str
    tools_used: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    success: bool
    output: Any = None
    error: str | None = None
    requires_confirmation: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
