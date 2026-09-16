"""Plugin contract for every assistant capability."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from jarvis.models.contracts import ToolResult


class Tool(ABC):
    """A validated, independently testable assistant tool."""

    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[type[BaseModel]]
    permissions: ClassVar[frozenset[str]] = frozenset()
    examples: ClassVar[tuple[str, ...]] = ()
    requires_confirmation: ClassVar[bool] = False

    def confirmation_required(self, parameters: BaseModel) -> bool:
        """Decide confirmation after parameter validation; override for selective actions."""
        return self.requires_confirmation

    @abstractmethod
    async def run(self, parameters: BaseModel) -> ToolResult:
        """Execute with already validated input and return a non-throwing result."""


class ConfirmationRequiredError(PermissionError):
    pass
