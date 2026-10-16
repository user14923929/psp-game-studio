"""Translate validated expressions into C expressions."""

from __future__ import annotations

import ast

from pocketpsp.frontend.symbols import BOOL, BUTTONS, FLOAT, INT, FuncInfo, Program

C_TYPES = {INT: "int32_t", FLOAT: "float", BOOL: "bool", "void": "void"}

_BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*"}
_CMP = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}


def global_c(name: str) -> str:
    return f"g_{name}"


def local_c(name: str) -> str:
    return f"v_{name}"


def func_c(name: str) -> str:
    return f"f_{name}"


def sprite_c(name: str) -> str:
    return f"spr_{name}"


def float_literal(value: float) -> str:
    text = repr(float(value))
    if "." not in text and "e" not in text and "E" not in text:
        text += ".0"
    return text + "f"


def convert(code: str, have: str, want: str) -> str:
    """Widen int to float where the destination type requires it."""
    if want == FLOAT and have == INT:
        return f"((float){code})"
    return code


def binary(op: ast.operator, lt: str, rt: str, left: str, right: str) -> str:
    if isinstance(op, ast.Div):
        return f"((float){left} / (float){right})"
    if isinstance(op, ast.FloorDiv):
        return f"pp_floordiv({left}, {right})"
    if isinstance(op, ast.Mod):
        return f"pp_mod({left}, {right})"
    return f"({left} {_BIN[type(op)]} {right})"


class ExprEmitter:
    def __init__(self, program: Program, func: FuncInfo) -> None:
        self.prog = program
        self.func = func

    def name(self, name: str) -> str:
        return local_c(name) if name in self.func.locals else global_c(name)

    def emit(self, node: ast.expr) -> str:
        p = self.prog
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                return "true" if v else "false"
            if isinstance(v, int):
                return str(v)
            if isinstance(v, float):
                return float_literal(v)
        elif isinstance(node, ast.Name):
            return self.name(node.id)
        elif isinstance(node, ast.Attribute):
            assert isinstance(node.value, ast.Name)
            return f"{sprite_c(node.value.id)}.{node.attr}"
        elif isinstance(node, ast.BinOp):
            lt, rt = p.type_of(node.left), p.type_of(node.right)
            return binary(node.op, lt, rt, self.emit(node.left), self.emit(node.right))
        elif isinstance(node, ast.UnaryOp):
            inner = self.emit(node.operand)
            sym = {ast.USub: "-", ast.UAdd: "+", ast.Not: "!"}[type(node.op)]
            return f"({sym}{inner})"
        elif isinstance(node, ast.BoolOp):
            sym = "&&" if isinstance(node.op, ast.And) else "||"
            return "(" + f" {sym} ".join(self.emit(v) for v in node.values) + ")"
        elif isinstance(node, ast.Compare):
            return (f"({self.emit(node.left)} {_CMP[type(node.ops[0])]} "
                    f"{self.emit(node.comparators[0])})")
        elif isinstance(node, ast.Call):
            return self.call(node)
        raise AssertionError(f"validator let through {type(node).__name__}")

    def emit_as(self, node: ast.expr, want: str) -> str:
        return convert(self.emit(node), self.prog.type_of(node), want)

    def call(self, node: ast.Call) -> str:
        p = self.prog
        f = node.func
        if isinstance(f, ast.Attribute):
            assert isinstance(f.value, ast.Name)
            base, attr = f.value.id, f.attr
            if base == "Button":
                arg = node.args[0]
                assert isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                return f"pp_button_{attr}({BUTTONS[arg.value]})"
            if base == p.game_name:
                a = ", ".join(self.emit(x) for x in node.args)
                return f"pp_clear({a})"
            return f"pp_sprite_draw(&{sprite_c(base)})"
        assert isinstance(f, ast.Name)
        name = f.id
        if name in p.funcs:
            fn = p.funcs[name]
            args = ", ".join(self.emit_as(a, t) for a, (_, t) in zip(node.args, fn.params, strict=True))
            return f"{func_c(name)}({args})"
        types = [p.type_of(a) for a in node.args]
        if name == "abs":
            return f"pp_abs_{'f' if types[0] == FLOAT else 'i'}({self.emit(node.args[0])})"
        if name in ("min", "max"):
            if FLOAT in types:
                a, b = (self.emit_as(x, FLOAT) for x in node.args)
                return f"pp_{name}_f({a}, {b})"
            a, b = (self.emit(x) for x in node.args)
            return f"pp_{name}_i({a}, {b})"
        if name == "int":
            inner = self.emit(node.args[0])
            return f"pp_f2i({inner})" if types[0] == FLOAT else inner
        if name == "float":
            return self.emit_as(node.args[0], FLOAT)
        raise AssertionError(f"validator let through call to {name}")
