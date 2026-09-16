"""Central guarded access point for tool plugins."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from pydantic import ValidationError

from jarvis.models.contracts import ToolResult
from jarvis.tools.base import Tool


class ToolManager:
    def __init__(self, rate_limit_per_minute: int) -> None:
        self._tools: dict[str, Tool] = {}
        self._calls: deque[datetime] = deque()
        self._rate_limit = rate_limit_per_minute

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def descriptions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.name,
                "description": item.description,
                "parameters": item.parameters.model_json_schema(),
                "permissions": sorted(item.permissions),
            }
            for item in self._tools.values()
        ]

    async def execute(
        self, name: str, raw_parameters: dict[str, Any], confirmed: bool = False
    ) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=1)
        while self._calls and self._calls[0] < cutoff:
            self._calls.popleft()
        if len(self._calls) >= self._rate_limit:
            return ToolResult(success=False, error="Tool rate limit exceeded.")
        try:
            parameters = tool.parameters.model_validate(raw_parameters)
        except ValidationError as error:
            return ToolResult(success=False, error=f"Invalid parameters: {error}")
        try:
            requires_confirmation = tool.confirmation_required(parameters)
        except (TypeError, ValueError):
            return ToolResult(success=False, error="Tool parameters could not be processed safely.")
        if requires_confirmation and not confirmed:
            return ToolResult(
                success=False,
                requires_confirmation=True,
                error=f"Confirmation is required before running {name}.",
            )
        self._calls.append(now)
        logger.info("tool_execution_started", tool=name)
        try:
            result = await tool.run(parameters)
        except Exception:
            logger.exception("tool_execution_failed", tool=name)
            return ToolResult(success=False, error="Tool execution failed safely.")
        logger.info("tool_execution_finished", tool=name, success=result.success)
        return result
