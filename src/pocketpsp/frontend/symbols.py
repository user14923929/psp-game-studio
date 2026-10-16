"""Symbol tables produced by the validator and consumed by code generation."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

INT = "int"
FLOAT = "float"
BOOL = "bool"
VOID = "void"
NUMERIC = (INT, FLOAT)

BUTTONS: dict[str, str] = {
    name: f"PSP_CTRL_{name}"
    for name in (
        "LEFT", "RIGHT", "UP", "DOWN", "CROSS", "CIRCLE", "SQUARE",
        "TRIANGLE", "START", "SELECT", "LTRIGGER", "RTRIGGER",
    )
}


@dataclass
class GlobalVar:
    name: str
    type: str
    value: int | float | bool
    line: int


@dataclass
class SpriteDecl:
    name: str
    path: str
    x: float
    y: float
    line: int


@dataclass
class FuncInfo:
    name: str
    node: ast.FunctionDef
    kind: str  # "update", "draw" or "user"
    params: list[tuple[str, str]] = field(default_factory=list)
    ret: str = VOID
    locals: dict[str, str] = field(default_factory=dict)  # includes params
    declared_globals: set[str] = field(default_factory=set)


@dataclass
class Program:
    """A validated game, ready for C generation."""

    filename: str
    title: str = ""
    game_name: str = ""
    globals: dict[str, GlobalVar] = field(default_factory=dict)
    sprites: dict[str, SpriteDecl] = field(default_factory=dict)
    funcs: dict[str, FuncInfo] = field(default_factory=dict)
    types: dict[int, str] = field(default_factory=dict)  # id(expr node) -> type

    def type_of(self, node: ast.expr) -> str:
        return self.types[id(node)]


def body_without_docstring(fn: ast.FunctionDef) -> list[ast.stmt]:
    """Return a function body without its leading docstring, if any."""
    body = fn.body
    if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        return body[1:]
    return body
