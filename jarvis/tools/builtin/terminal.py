"""Workspace-confined terminal execution with policy-based confirmation."""

from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from jarvis.models.contracts import ToolResult
from jarvis.tools.base import Tool


class TerminalInput(BaseModel):
    command: str = Field(min_length=1, max_length=4_000)
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)


class TerminalTool(Tool):
    """Execute a non-shell command inside the configured workspace."""

    name: ClassVar[str] = "terminal"
    description: ClassVar[str] = "Run a non-interactive command in the configured workspace."
    parameters: ClassVar[type[BaseModel]] = TerminalInput
    permissions: ClassVar[frozenset[str]] = frozenset({"terminal"})
    _dangerous_commands: ClassVar[frozenset[str]] = frozenset(
        {"rm", "sudo", "apt", "apt-get", "brew", "dnf", "yum"}
    )

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root.resolve()

    def confirmation_required(self, parameters: BaseModel) -> bool:
        args = shlex.split(TerminalInput.model_validate(parameters).command)
        if not args:
            return False
        return Path(args[0]).name in self._dangerous_commands or "install" in args

    async def run(self, parameters: BaseModel) -> ToolResult:
        args = shlex.split(TerminalInput.model_validate(parameters).command)
        if not args:
            return ToolResult(success=False, error="Command must not be empty.")
        timeout = TerminalInput.model_validate(parameters).timeout_seconds
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                cwd=self._root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            return ToolResult(success=False, error=f"Command exceeded {timeout:g} seconds.")
        except OSError:
            return ToolResult(success=False, error="Command could not be started.")
        return ToolResult(
            success=process.returncode == 0,
            output=stdout.decode("utf-8", errors="replace"),
            error=stderr.decode("utf-8", errors="replace") or None,
            metadata={"exit_code": process.returncode},
        )
