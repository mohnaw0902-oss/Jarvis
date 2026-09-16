from pathlib import Path

import pytest

from jarvis.tools.builtin.calculator import CalculatorTool
from jarvis.tools.builtin.filesystem import FilesystemTool
from jarvis.tools.manager import ToolManager


@pytest.mark.asyncio
async def test_calculator_is_registered_and_validated() -> None:
    manager = ToolManager(rate_limit_per_minute=2)
    manager.register(CalculatorTool())
    result = await manager.execute("calculator", {"expression": "2 * (3 + 4)"})
    assert result.success is True
    assert result.output == 14


@pytest.mark.asyncio
async def test_filesystem_delete_requires_confirmation(tmp_path: Path) -> None:
    (tmp_path / "note.txt").write_text("safe", encoding="utf-8")
    manager = ToolManager(rate_limit_per_minute=2)
    manager.register(FilesystemTool(tmp_path))
    result = await manager.execute("filesystem", {"operation": "delete", "path": "note.txt"})
    assert result.requires_confirmation is True


@pytest.mark.asyncio
async def test_terminal_requires_confirmation_for_package_install(tmp_path: Path) -> None:
    from jarvis.tools.builtin.terminal import TerminalTool

    manager = ToolManager(rate_limit_per_minute=2)
    manager.register(TerminalTool(tmp_path))
    result = await manager.execute("terminal", {"command": "python -m pip install sample"})
    assert result.requires_confirmation is True
