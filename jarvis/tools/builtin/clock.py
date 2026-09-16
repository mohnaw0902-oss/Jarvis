from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel

from jarvis.models.contracts import ToolResult
from jarvis.tools.base import Tool


class ClockInput(BaseModel):
    pass


class ClockTool(Tool):
    name: ClassVar[str] = "clock"
    description: ClassVar[str] = "Return the current UTC time."
    parameters: ClassVar[type[BaseModel]] = ClockInput

    async def run(self, parameters: BaseModel) -> ToolResult:
        return ToolResult(success=True, output=datetime.now(UTC).isoformat())
