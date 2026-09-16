"""Safe arithmetic tool without Python eval."""

from __future__ import annotations

import ast
import operator
from typing import ClassVar

from pydantic import BaseModel, Field

from jarvis.models.contracts import ToolResult
from jarvis.tools.base import Tool


class CalculatorInput(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


class CalculatorTool(Tool):
    name: ClassVar[str] = "calculator"
    description: ClassVar[str] = "Evaluate a basic arithmetic expression."
    parameters: ClassVar[type[BaseModel]] = CalculatorInput
    examples: ClassVar[tuple[str, ...]] = ("2 * (3 + 4)",)
    _operators: ClassVar[dict[type[ast.operator], object]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
    }

    async def run(self, parameters: BaseModel) -> ToolResult:
        expression = CalculatorInput.model_validate(parameters).expression
        try:
            value = self._evaluate(ast.parse(expression, mode="eval").body)
            return ToolResult(success=True, output=value)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
            return ToolResult(success=False, error="Expression contains unsupported arithmetic.")

    def _evaluate(self, node: ast.expr) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = self._evaluate(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp) and type(node.op) in self._operators:
            left, right = self._evaluate(node.left), self._evaluate(node.right)
            operation = self._operators[type(node.op)]
            if not callable(operation):
                raise ValueError("Unsupported operation")
            return operation(left, right)  # type: ignore[no-any-return]
        raise ValueError("Unsupported expression")
