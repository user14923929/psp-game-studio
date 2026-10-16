"""Translate validated statements into C statements."""

from __future__ import annotations

import ast

from pocketpsp.codegen.expressions import ExprEmitter, binary, convert, global_c, local_c, sprite_c
from pocketpsp.frontend.symbols import FuncInfo, Program, body_without_docstring

IND = "    "


class StmtEmitter:
    def __init__(self, program: Program, func: FuncInfo) -> None:
        self.prog = program
        self.func = func
        self.ex = ExprEmitter(program, func)
        self.lines: list[str] = []
        self.tmp = 0

    def body(self) -> list[str]:
        self.block(body_without_docstring(self.func.node), 1)
        return self.lines

    def put(self, depth: int, text: str) -> None:
        self.lines.append(IND * depth + text)

    def block(self, stmts: list[ast.stmt], depth: int) -> None:
        for st in stmts:
            self.stmt(st, depth)

    def var_type(self, name: str) -> str:
        if name in self.func.locals and name not in self.func.declared_globals:
            return self.func.locals[name]
        return self.prog.globals[name].type

    def target(self, node: ast.expr) -> tuple[str, str]:
        """Return (C lvalue, type) for an assignment target."""
        if isinstance(node, ast.Name):
            return self.ex.name(node.id), self.var_type(node.id)
        assert isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
        return f"{sprite_c(node.value.id)}.{node.attr}", "float"

    def stmt(self, st: ast.stmt, d: int) -> None:
        ex = self.ex
        if isinstance(st, (ast.Pass, ast.Global)):
            return
        if isinstance(st, ast.Assign):
            lv, t = self.target(st.targets[0])
            self.put(d, f"{lv} = {ex.emit_as(st.value, t)};")
        elif isinstance(st, ast.AnnAssign):
            assert st.value is not None
            lv, t = self.target(st.target)
            self.put(d, f"{lv} = {ex.emit_as(st.value, t)};")
        elif isinstance(st, ast.AugAssign):
            lv, t = self.target(st.target)
            vt = self.prog.type_of(st.value)
            self.put(d, f"{lv} = {binary(st.op, t, vt, lv, ex.emit(st.value))};")
        elif isinstance(st, ast.If):
            self.if_chain(st, d, "if")
        elif isinstance(st, ast.While):
            self.put(d, f"while ({ex.emit(st.test)}) {{")
            self.block(st.body, d + 1)
            self.put(d, "}")
        elif isinstance(st, ast.For):
            self.for_loop(st, d)
        elif isinstance(st, ast.Break):
            self.put(d, "break;")
        elif isinstance(st, ast.Continue):
            self.put(d, "continue;")
        elif isinstance(st, ast.Return):
            if st.value is None:
                self.put(d, "return;")
            else:
                self.put(d, f"return {ex.emit_as(st.value, self.func.ret)};")
        elif isinstance(st, ast.Expr):
            self.put(d, f"{ex.emit(st.value)};")
        else:
            raise AssertionError(f"validator let through {type(st).__name__}")

    def if_chain(self, st: ast.If, d: int, kw: str) -> None:
        self.lines.append(IND * d + f"{kw} ({self.ex.emit(st.test)}) {{" if kw == "if"
                          else f" {kw} ({self.ex.emit(st.test)}) {{")
        self.block(st.body, d + 1)
        if not st.orelse:
            self.put(d, "}")
        elif len(st.orelse) == 1 and isinstance(st.orelse[0], ast.If):
            self.put(d, "} else")
            self._elif(st.orelse[0], d)
        else:
            self.put(d, "} else {")
            self.block(st.orelse, d + 1)
            self.put(d, "}")

    def _elif(self, st: ast.If, d: int) -> None:
        # Merge the "} else" line with the following "if (...) {" line.
        self.lines[-1] += f" if ({self.ex.emit(st.test)}) {{"
        self.block(st.body, d + 1)
        if not st.orelse:
            self.put(d, "}")
        elif len(st.orelse) == 1 and isinstance(st.orelse[0], ast.If):
            self.put(d, "} else")
            self._elif(st.orelse[0], d)
        else:
            self.put(d, "} else {")
            self.block(st.orelse, d + 1)
            self.put(d, "}")

    def for_loop(self, st: ast.For, d: int) -> None:
        assert isinstance(st.iter, ast.Call) and isinstance(st.target, ast.Name)
        args = st.iter.args
        self.tmp += 1
        n = self.tmp
        start, step = "0", 1
        if len(args) == 1:
            stop = self.ex.emit(args[0])
        else:
            start, stop = self.ex.emit(args[0]), self.ex.emit(args[1])
            if len(args) == 3:
                step_node = args[2]
                if isinstance(step_node, ast.UnaryOp):
                    assert isinstance(step_node.operand, ast.Constant)
                    step = -int(step_node.operand.value)  # type: ignore[arg-type]
                else:
                    assert isinstance(step_node, ast.Constant)
                    step = int(step_node.value)  # type: ignore[arg-type]
        cmp = "<" if step > 0 else ">"
        i, stp = f"i_{n}", f"stop_{n}"
        self.put(d, "{")
        self.put(d + 1, f"int32_t {stp} = {stop};")
        self.put(d + 1, f"for (int32_t {i} = {start}; {i} {cmp} {stp}; {i} += {step}) {{")
        self.put(d + 2, f"{self.ex.name(st.target.id)} = {i};")
        self.block(st.body, d + 2)
        self.put(d + 1, "}")
        self.put(d, "}")


__all__ = ["StmtEmitter", "convert", "global_c", "local_c"]
