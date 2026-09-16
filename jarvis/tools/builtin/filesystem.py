"""Workspace-confined asynchronous file operations."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, Field

from jarvis.models.contracts import ToolResult
from jarvis.tools.base import Tool


class FilesystemInput(BaseModel):
    operation: Literal["read", "write", "delete"]
    path: str = Field(min_length=1, max_length=1_024)
    content: str = Field(default="", max_length=1_000_000)


class FilesystemTool(Tool):
    name: ClassVar[str] = "filesystem"
    description: ClassVar[str] = (
        "Read, write, or delete files confined to the configured workspace."
    )
    parameters: ClassVar[type[BaseModel]] = FilesystemInput
    permissions: ClassVar[frozenset[str]] = frozenset({"filesystem"})

    def __init__(self, workspace_root: Path, max_read_bytes: int = 1_000_000) -> None:
        self._root = workspace_root.resolve()
        self._max_read_bytes = max_read_bytes

    def confirmation_required(self, parameters: BaseModel) -> bool:
        return FilesystemInput.model_validate(parameters).operation == "delete"

    async def run(self, parameters: BaseModel) -> ToolResult:
        args = FilesystemInput.model_validate(parameters)
        target = (self._root / args.path).resolve()
        if not target.is_relative_to(self._root):
            return ToolResult(success=False, error="Path escapes workspace.")
        try:
            if args.operation == "read":
                metadata = await asyncio.to_thread(target.stat)
                if metadata.st_size > self._max_read_bytes:
                    return ToolResult(
                        success=False, error="File exceeds the configured read limit."
                    )
                return ToolResult(
                    success=True, output=await asyncio.to_thread(target.read_text, encoding="utf-8")
                )
            if args.operation == "write":
                await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
                await asyncio.to_thread(target.write_text, args.content, encoding="utf-8")
                return ToolResult(success=True, output="File written.")
            await asyncio.to_thread(target.unlink)
            return ToolResult(success=True, output="File deleted.")
        except (OSError, UnicodeError):
            return ToolResult(success=False, error="Filesystem operation could not be completed.")
