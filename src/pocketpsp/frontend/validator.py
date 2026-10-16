"""Validate a parsed game against the supported DSL subset.

Only explicitly supported constructs are accepted. Everything else produces a
diagnostic with file, line and column. Validation also infers expression types
and records them in the resulting :class:`Program`.
"""

from __future__ import annotations

import ast
import math
import posixpath

from pocketpsp.frontend.diagnostics import Diagnostic, DiagnosticError
from pocketpsp.frontend.symbols import (
    BOOL,
    BUTTONS,
    FLOAT,
    INT,
    NUMERIC,
    VOID,
    FuncInfo,
    GlobalVar,
    Program,
    SpriteDecl,
    body_without_docstring,
)

ALLOWED_IMPORTS = ("Game", "Sprite", "Button")
SCALARS = {"int": INT, "float": FLOAT, "bool": BOOL}
BUILTINS = ("abs", "min", "max", "int", "float", "range")
INT_MIN, INT_MAX = -(2**31), 2**31 - 1
FLOAT_MAX = 3.4028234663852886e38  # largest finite C float

_ARITH = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod)
_CMP = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)


def validate(tree: ast.Module, filename: str) -> Program:
    """Validate ``tree`` and return a :class:`Program`, or raise DiagnosticError."""
    v = _Validator(tree, filename)
    program = v.run()
    if v.diags:
        raise DiagnosticError(v.diags)
    return program


class _Validator:
    def __init__(self, tree: ast.Module, filename: str) -> None:
        self.tree = tree
        self.filename = filename
        self.diags: list[Diagnostic] = []
        self.prog = Program(filename=filename)
        self.imported: set[str] = set()
        self.has_run = False
        self.func: FuncInfo | None = None
        self.loop_depth = 0

    # ------------------------------------------------------------ helpers
    def err(self, node: ast.AST, msg: str) -> None:
        line = getattr(node, "lineno", None)
        col = getattr(node, "col_offset", None)
        self.diags.append(
            Diagnostic(msg, self.filename, line, None if col is None else col + 1)
        )

    def unsupported(self, node: ast.AST, what: str = "") -> None:
        name = what or type(node).__name__
        self.err(node, f"unsupported syntax: {name}")

    def taken(self, name: str) -> bool:
        p = self.prog
        return (
            name in p.globals or name in p.sprites or name in p.funcs
            or name == p.game_name or name in self.imported or name in BUILTINS
        )

    # ------------------------------------------------------------ module
    def run(self) -> Program:
        body = self.tree.body
        self._declare_game(body)
        funcs: list[FuncInfo] = []
        for i, st in enumerate(body):
            if isinstance(st, ast.ImportFrom):
                self._import(st)
            elif isinstance(st, ast.Import):
                self.err(st, "only 'from pocketpsp import ...' is supported")
            elif (isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant)
                  and isinstance(st.value.value, str) and i == 0):
                continue  # module docstring
            elif isinstance(st, (ast.Assign, ast.AnnAssign)):
                self._module_assign(st)
            elif isinstance(st, ast.FunctionDef):
                info = self._declare_function(st)
                if info:
                    funcs.append(info)
            elif self._is_game_run(st):
                if i != len(body) - 1:
                    self.err(st, "game.run() must be the last statement in the file")
                if self.has_run:
                    self.err(st, "game.run() may only appear once")
                self.has_run = True
            else:
                self.unsupported(st)
        if not self.prog.game_name:
            self.diags.append(Diagnostic(
                "missing game declaration: add  game = Game(title=\"...\")",
                self.filename))
        if not self.has_run:
            self.diags.append(Diagnostic(
                "missing game.run() at the end of the file", self.filename))
        for info in funcs:
            self._function_body(info)
        return self.prog

    def _import(self, st: ast.ImportFrom) -> None:
        if st.module != "pocketpsp" or st.level != 0:
            self.err(st, f"import not allowed: only 'pocketpsp' can be imported "
                         f"(got '{st.module}')")
            return
        for alias in st.names:
            if alias.name not in ALLOWED_IMPORTS:
                self.err(st, f"'{alias.name}' is not part of the pocketpsp API "
                             f"(available: {', '.join(ALLOWED_IMPORTS)})")
            elif alias.asname:
                self.err(st, "import aliases are not supported")
            else:
                self.imported.add(alias.name)

    def _declare_game(self, body: list[ast.stmt]) -> None:
        for st in body:
            if (isinstance(st, ast.Assign) and len(st.targets) == 1
                    and isinstance(st.targets[0], ast.Name)
                    and self._call_name(st.value) == "Game"):
                if self.prog.game_name:
                    self.err(st, "only one Game(...) may be declared")
                    continue
                call = st.value
                assert isinstance(call, ast.Call)
                self.prog.game_name = st.targets[0].id
                self.prog.title = self._game_title(call)
                if "Game" not in self.imported and not any(
                        isinstance(s, ast.ImportFrom) and any(a.name == "Game" for a in s.names)
                        for s in body):
                    self.err(st, "'Game' is not imported")

    def _game_title(self, call: ast.Call) -> str:
        if call.args or len(call.keywords) != 1 or call.keywords[0].arg != "title":
            self.err(call, "Game() takes exactly one keyword argument: title=\"...\"")
            return ""
        val = call.keywords[0].value
        if not (isinstance(val, ast.Constant) and isinstance(val.value, str)):
            self.err(val, "Game title must be a string literal")
            return ""
        title = val.value
        if not title.strip() or len(title) > 64 or any(ord(c) < 32 for c in title):
            self.err(val, "Game title must be 1-64 printable characters")
            return ""
        return title

    @staticmethod
    def _call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return node.func.id
        return None

    def _is_game_run(self, st: ast.stmt) -> bool:
        return (
            isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
            and isinstance(st.value.func, ast.Attribute)
            and isinstance(st.value.func.value, ast.Name)
            and st.value.func.value.id == self.prog.game_name
            and st.value.func.attr == "run" and not st.value.args
            and not st.value.keywords
        )

    def _const(self, node: ast.expr) -> tuple[str, int | float | bool] | None:
        neg = False
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            neg = isinstance(node.op, ast.USub)
            node = node.operand
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                return None if neg else (BOOL, v)
            if isinstance(v, int):
                v = -v if neg else v
                if not INT_MIN <= v <= INT_MAX:
                    self.err(node, "integer literal does not fit in 32 bits")
                    return None
                return INT, v
            if isinstance(v, float):
                if not math.isfinite(v) or abs(v) > FLOAT_MAX:
                    self.err(node, "float literal is out of range")
                    return None
                return FLOAT, (-v if neg else v)
        return None

    def _module_assign(self, st: ast.Assign | ast.AnnAssign) -> None:
        if isinstance(st, ast.Assign):
            if len(st.targets) != 1 or not isinstance(st.targets[0], ast.Name):
                self.err(st, "only simple 'name = value' assignments are supported")
                return
            target, value, ann = st.targets[0], st.value, None
        else:
            if not isinstance(st.target, ast.Name) or st.value is None:
                self.err(st, "only simple 'name: type = value' assignments are supported")
                return
            target, value = st.target, st.value
            ann = self._annotation(st.annotation)
            if ann is None:
                return
        name = target.id
        if name == self.prog.game_name and self._call_name(value) == "Game":
            return
        if self.taken(name):
            self.err(target, f"name '{name}' is already defined")
            return
        if self._call_name(value) == "Sprite":
            self._sprite_decl(name, value, st)  # type: ignore[arg-type]
            return
        c = self._const(value)
        if c is None:
            self.err(value, "module-level values must be number or bool literals "
                            "(or Game(...)/Sprite(...) declarations)")
            return
        typ, val = c
        if ann is not None:
            if ann == typ or (ann == FLOAT and typ == INT):
                typ, val = ann, (float(val) if ann == FLOAT else val)
            else:
                self.err(value, f"cannot initialise {ann} variable with {typ} value")
                return
        self.prog.globals[name] = GlobalVar(name, typ, val, st.lineno)

    def _sprite_decl(self, name: str, call: ast.Call, st: ast.stmt) -> None:
        if "Sprite" not in self.imported:
            self.err(call, "'Sprite' is not imported")
        if len(call.args) != 1 or not (
                isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)):
            self.err(call, 'Sprite() needs a string literal path first: Sprite("assets/x.png", x=0, y=0)')
            return
        path = call.args[0].value
        norm = posixpath.normpath(path)
        if (path.startswith("/") or "\\" in path or norm.startswith("..")
                or not path.lower().endswith(".png") or "\x00" in path):
            self.err(call.args[0], "sprite path must be a relative .png path inside the project")
            return
        pos = {"x": 0.0, "y": 0.0}
        for kw in call.keywords:
            c = self._const(kw.value)
            if kw.arg not in pos or c is None or c[0] == BOOL:
                self.err(kw.value if kw.arg in pos else call,
                         "Sprite() accepts only numeric literal keywords x= and y=")
                return
            pos[kw.arg] = float(c[1])
        self.prog.sprites[name] = SpriteDecl(name, norm, pos["x"], pos["y"], st.lineno)

    # ------------------------------------------------------------ functions
    def _annotation(self, node: ast.expr | None) -> str | None:
        if isinstance(node, ast.Name) and node.id in SCALARS:
            return SCALARS[node.id]
        if node is not None:
            self.err(node, "type annotation must be one of: int, float, bool")
        return None

    def _declare_function(self, fn: ast.FunctionDef) -> FuncInfo | None:
        a = fn.args
        if a.vararg or a.kwarg or a.kwonlyargs or a.posonlyargs or a.defaults or a.kw_defaults:
            self.err(fn, "only plain positional parameters are supported")
            return None
        kind = "user"
        if fn.decorator_list:
            dec = fn.decorator_list[0]
            ok = (len(fn.decorator_list) == 1 and isinstance(dec, ast.Attribute)
                  and isinstance(dec.value, ast.Name)
                  and dec.value.id == self.prog.game_name
                  and dec.attr in ("update", "draw"))
            if not ok:
                self.err(dec, f"unsupported decorator (use @{self.prog.game_name or 'game'}"
                              ".update or .draw)")
                return None
            assert isinstance(dec, ast.Attribute)
            kind = dec.attr
            if any(f.kind == kind for f in self.prog.funcs.values()):
                self.err(fn, f"only one @{self.prog.game_name}.{kind} function is allowed")
                return None
        if self.taken(fn.name):
            self.err(fn, f"name '{fn.name}' is already defined")
            return None
        params: list[tuple[str, str]] = []
        seen: set[str] = set()
        for arg in a.args:
            t = self._annotation(arg.annotation) if arg.annotation else None
            if arg.annotation is None:
                self.err(arg, f"parameter '{arg.arg}' needs a type annotation (int, float or bool)")
            if arg.arg in seen or self.taken(arg.arg):
                self.err(arg, f"parameter name '{arg.arg}' is already used")
            seen.add(arg.arg)
            params.append((arg.arg, t or INT))
        ret = VOID
        if fn.returns is not None:
            if isinstance(fn.returns, ast.Constant) and fn.returns.value is None:
                ret = VOID
            else:
                ret = self._annotation(fn.returns) or VOID
        if kind != "user" and (params or ret != VOID):
            self.err(fn, f"@{self.prog.game_name}.{kind} functions take no parameters "
                         "and return nothing")
        info = FuncInfo(fn.name, fn, kind, params, ret, dict(params))
        self.prog.funcs[fn.name] = info
        return info

    def _function_body(self, info: FuncInfo) -> None:
        self.func = info
        self.loop_depth = 0
        body = body_without_docstring(info.node)
        for st in body:
            self._stmt(st)
        if info.ret != VOID and not self._always_returns(body):
            self.err(info.node, f"function '{info.name}' may end without returning a value")
        self.func = None

    def _always_returns(self, body: list[ast.stmt]) -> bool:
        if not body:
            return False
        last = body[-1]
        if isinstance(last, ast.Return):
            return True
        if isinstance(last, ast.If):
            return (bool(last.orelse) and self._always_returns(last.body)
                    and self._always_returns(last.orelse))
        return False

    # ------------------------------------------------------------ statements
    def _stmt(self, st: ast.stmt) -> None:
        f = self.func
        assert f is not None
        if isinstance(st, ast.Pass):
            return
        if isinstance(st, ast.Assign):
            if len(st.targets) != 1:
                self.err(st, "chained assignment is not supported")
                return
            self._assign(st.targets[0], st.value, st, None)
        elif isinstance(st, ast.AnnAssign):
            if st.value is None:
                self.err(st, "annotated declarations need a value")
                return
            self._assign(st.target, st.value, st, self._annotation(st.annotation))
        elif isinstance(st, ast.AugAssign):
            self._augassign(st)
        elif isinstance(st, ast.If):
            self._cond(st.test)
            for s in st.body + st.orelse:
                self._stmt(s)
        elif isinstance(st, ast.While):
            if st.orelse:
                self.err(st, "'else' on loops is not supported")
            self._cond(st.test)
            self.loop_depth += 1
            for s in st.body:
                self._stmt(s)
            self.loop_depth -= 1
        elif isinstance(st, ast.For):
            self._for(st)
        elif isinstance(st, (ast.Break, ast.Continue)):
            if self.loop_depth == 0:
                self.err(st, f"'{type(st).__name__.lower()}' outside a loop")
        elif isinstance(st, ast.Return):
            self._return(st)
        elif isinstance(st, ast.Global):
            self._global(st)
        elif isinstance(st, ast.Expr):
            if isinstance(st.value, ast.Call):
                self._expr(st.value, allow_void=True)
            else:
                self.err(st, "expression statement has no effect; only calls are allowed")
        else:
            self.unsupported(st)

    def _global(self, st: ast.Global) -> None:
        assert self.func is not None
        for n in st.names:
            if n not in self.prog.globals:
                self.err(st, f"'{n}' is not a module-level variable")
            elif n in self.func.locals:
                self.err(st, f"name '{n}' is used before global declaration")
            else:
                self.func.declared_globals.add(n)

    def _cond(self, node: ast.expr) -> None:
        if self._expr(node) != BOOL:
            self.err(node, "condition must be a bool; use a comparison (e.g. x != 0)")

    def _for(self, st: ast.For) -> None:
        if st.orelse:
            self.err(st, "'else' on loops is not supported")
        it = st.iter
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name)
                and it.func.id == "range" and 1 <= len(it.args) <= 3 and not it.keywords):
            self.err(st.iter, "for loops must iterate over range(stop), range(start, stop) "
                              "or range(start, stop, step)")
        else:
            for i, arg in enumerate(it.args):
                if i == 2:
                    c = self._const(arg)
                    if c is None or c[0] != INT or c[1] == 0:
                        self.err(arg, "range step must be a non-zero integer literal")
                elif self._expr(arg) != INT:
                    self.err(arg, "range arguments must be int")
            self.prog.types[id(it)] = VOID
        if not isinstance(st.target, ast.Name):
            self.err(st.target, "loop variable must be a simple name")
        else:
            self._bind_local(st.target, INT, st.target.id)
        self.loop_depth += 1
        for s in st.body:
            self._stmt(s)
        self.loop_depth -= 1

    def _return(self, st: ast.Return) -> None:
        assert self.func is not None
        want = self.func.ret
        if st.value is None:
            if want != VOID:
                self.err(st, f"function must return a {want} value")
            return
        if want == VOID:
            self.err(st, "this function does not return a value (add '-> int', '-> float' or '-> bool')")
            self._expr(st.value)
            return
        got = self._expr(st.value)
        if not self._assignable(want, got):
            self.err(st.value, f"cannot return {got} from a function declared '-> {want}'")

    @staticmethod
    def _assignable(target: str, value: str) -> bool:
        return target == value or (target == FLOAT and value == INT)

    def _bind_local(self, node: ast.AST, typ: str, name: str) -> bool:
        assert self.func is not None
        if name in self.func.declared_globals:
            return True
        if self.taken(name):
            self.err(node, f"cannot use '{name}' as a variable: the name is already defined "
                           "at module level (use 'global' to modify a module variable)"
                     if name in self.prog.globals else
                     f"cannot use '{name}' as a variable: the name is already defined")
            return False
        have = self.func.locals.get(name)
        if have is None:
            self.func.locals[name] = typ
        elif not self._assignable(have, typ):
            self.err(node, f"cannot assign {typ} to {have} variable '{name}' "
                           f"(declare it as float first, e.g. {name} = 0.0)")
            return False
        return True

    def _assign(self, target: ast.expr, value: ast.expr, st: ast.stmt, ann: str | None) -> None:
        assert self.func is not None
        vt = self._expr(value)
        if vt in (VOID, "sprite", "game"):
            self.err(value, "this expression has no usable value")
            return
        if isinstance(target, ast.Name):
            name = target.id
            if name in self.func.declared_globals:
                gt = self.prog.globals[name].type
                if not self._assignable(gt, vt):
                    self.err(value, f"cannot assign {vt} to {gt} variable '{name}'")
                return
            if ann is not None:
                if not self._assignable(ann, vt):
                    self.err(value, f"cannot initialise {ann} variable with {vt} value")
                    return
                vt = ann
            self._bind_local(target, vt, name)
        elif isinstance(target, ast.Attribute):
            self._attr_target(target, vt, value)
        else:
            self.err(target, "assignment target must be a variable or a sprite's x/y")

    def _attr_target(self, target: ast.Attribute, vt: str, value: ast.expr) -> None:
        if (isinstance(target.value, ast.Name) and target.value.id in self.prog.sprites
                and target.attr in ("x", "y")):
            if vt not in NUMERIC:
                self.err(value, f"sprite.{target.attr} must be a number, got {vt}")
        else:
            self.err(target, "only sprite.x and sprite.y can be assigned")

    def _augassign(self, st: ast.AugAssign) -> None:
        assert self.func is not None
        if not isinstance(st.op, _ARITH):
            self.unsupported(st.op, f"operator {type(st.op).__name__}")
            return
        t = st.target
        if isinstance(t, ast.Name):
            ctype = self._name_type(t)
            if ctype is None:
                return
            if t.id in self.prog.globals and t.id not in self.func.declared_globals:
                self.err(t, f"assignment to module variable '{t.id}' needs 'global {t.id}'")
                return
        elif (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
              and t.value.id in self.prog.sprites and t.attr in ("x", "y")):
            ctype = FLOAT
        else:
            self.err(t, "augmented assignment target must be a variable or sprite x/y")
            return
        vt = self._expr(st.value)
        rt = self._arith(st, st.op, ctype, vt, st.value)
        if rt is not None and not self._assignable(ctype, rt):
            self.err(st, f"result type {rt} cannot be stored in {ctype} variable"
                         + (" ('/' always gives float)" if isinstance(st.op, ast.Div) else ""))
        self.prog.types[id(st)] = rt or ctype

    # ------------------------------------------------------------ expressions
    def _name_type(self, node: ast.Name) -> str | None:
        assert self.func is not None
        n = node.id
        if n in self.func.locals:
            return self.func.locals[n]
        if n in self.prog.globals:
            return self.prog.globals[n].type
        if n in self.prog.sprites:
            return "sprite"
        self.err(node, f"undefined name '{n}'")
        return None

    def _expr(self, node: ast.expr, allow_void: bool = False) -> str:
        t = self._expr_inner(node)
        if t == VOID and not allow_void:
            self.err(node, "function returns no value")
        self.prog.types[id(node)] = t
        return t

    def _expr_inner(self, node: ast.expr) -> str:
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                return BOOL
            if isinstance(v, int):
                if not INT_MIN <= v <= INT_MAX:
                    self.err(node, "integer literal does not fit in 32 bits")
                return INT
            if isinstance(v, float):
                if not math.isfinite(v) or abs(v) > FLOAT_MAX:
                    self.err(node, "float literal is out of range")
                return FLOAT
            self.err(node, "string/other literals are only allowed as API arguments")
            return INT
        if isinstance(node, ast.Name):
            t = self._name_type(node)
            if t == "sprite":
                self.err(node, f"sprite '{node.id}' can only be used as {node.id}.x, "
                               f"{node.id}.y, {node.id}.draw()")
            return t if t and t != "sprite" else INT
        if isinstance(node, ast.Attribute):
            if (isinstance(node.value, ast.Name) and node.value.id in self.prog.sprites):
                if node.attr in ("x", "y"):
                    return FLOAT
                if node.attr in ("width", "height"):
                    return INT
            self.err(node, "unsupported attribute access (sprites expose x, y, width, height)")
            return INT
        if isinstance(node, ast.BinOp):
            lt, rt = self._expr(node.left), self._expr(node.right)
            return self._arith(node, node.op, lt, rt, node.right) or INT
        if isinstance(node, ast.UnaryOp):
            t = self._expr(node.operand)
            if isinstance(node.op, ast.Not):
                if t != BOOL:
                    self.err(node, "'not' needs a bool operand")
                return BOOL
            if isinstance(node.op, (ast.USub, ast.UAdd)):
                if t not in NUMERIC:
                    self.err(node, "unary +/- needs a number")
                    return INT
                return t
            self.unsupported(node.op, f"operator {type(node.op).__name__}")
            return INT
        if isinstance(node, ast.BoolOp):
            for operand in node.values:
                if self._expr(operand) != BOOL:
                    self.err(operand, "'and'/'or' operands must be bool; use comparisons")
            return BOOL
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                self.err(node, "chained comparisons are not supported; use 'and'")
            elif not isinstance(node.ops[0], _CMP):
                self.unsupported(node.ops[0], f"operator {type(node.ops[0]).__name__}")
            lt = self._expr(node.left)
            for c in node.comparators:
                rt = self._expr(c)
                if lt == BOOL or rt == BOOL:
                    if lt != rt or not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                        self.err(node, "bool values can only be compared to bool with == or !=")
            return BOOL
        if isinstance(node, ast.Call):
            return self._call(node)
        self.unsupported(node)
        return INT

    def _arith(self, node: ast.AST, op: ast.operator, lt: str, rt: str,
               right: ast.expr) -> str | None:
        if lt not in NUMERIC or rt not in NUMERIC:
            self.err(node, f"arithmetic needs numbers (int/float), got {lt} and {rt}")
            return None
        if isinstance(op, (ast.Div, ast.FloorDiv, ast.Mod)):
            c = self._const(right)
            if c is not None and c[1] == 0:
                self.err(right, "division by zero")
        if isinstance(op, ast.Div):
            return FLOAT
        if isinstance(op, (ast.FloorDiv, ast.Mod)):
            if lt != INT or rt != INT:
                self.err(node, "'//' and '%' only support int operands")
                return None
            return INT
        if isinstance(op, _ARITH):
            return FLOAT if FLOAT in (lt, rt) else INT
        self.unsupported(node, f"operator {type(op).__name__}")
        return None

    def _call(self, node: ast.Call) -> str:
        f = node.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            base, attr = f.value.id, f.attr
            if base == "Button" and "Button" in self.imported:
                return self._button_call(node, attr)
            if base == self.prog.game_name and attr == "clear":
                self._args(node, [INT, INT, INT], "game.clear(r, g, b)")
                return VOID
            if base == self.prog.game_name and attr == "run":
                self.err(node, "game.run() is only allowed as the last statement of the file")
                return VOID
            if base in self.prog.sprites and attr == "draw":
                if node.args or node.keywords:
                    self.err(node, f"{base}.draw() takes no arguments")
                return VOID
            self.err(node, f"unknown API call '{base}.{attr}()'")
            return VOID
        if isinstance(f, ast.Name):
            return self._named_call(node, f.id)
        self.err(node, "unsupported call target")
        return VOID

    def _button_call(self, node: ast.Call, attr: str) -> str:
        if attr not in ("held", "pressed"):
            self.err(node, f"unknown API call 'Button.{attr}()' (use held or pressed)")
            return BOOL
        a = node.args
        if len(a) != 1 or node.keywords or not (
                isinstance(a[0], ast.Constant) and isinstance(a[0].value, str)):
            self.err(node, f'Button.{attr}() takes one string literal, e.g. Button.{attr}("LEFT")')
        elif a[0].value not in BUTTONS:
            self.err(a[0], f"unknown button '{a[0].value}' (valid: {', '.join(BUTTONS)})")
        return BOOL

    def _args(self, node: ast.Call, want: list[str], sig: str) -> list[str]:
        if node.keywords or len(node.args) != len(want):
            self.err(node, f"expected {sig}")
            for a in node.args:
                self._expr(a)
            return []
        got = []
        for a, w in zip(node.args, want, strict=True):
            t = self._expr(a)
            if not self._assignable(w, t):
                self.err(a, f"expected {w} argument, got {t}")
            got.append(t)
        return got

    def _named_call(self, node: ast.Call, name: str) -> str:
        if name in self.prog.funcs:
            fn = self.prog.funcs[name]
            if fn.kind != "user":
                self.err(node, f"'{name}' is an engine callback and cannot be called directly")
                return VOID
            self._args(node, [t for _, t in fn.params],
                       f"{name}({', '.join(f'{p}: {t}' for p, t in fn.params)})")
            return fn.ret
        if name == "range":
            self.err(node, "range() is only allowed in a for loop")
            return INT
        if name in ("abs", "min", "max"):
            n = 1 if name == "abs" else 2
            if node.keywords or len(node.args) != n:
                self.err(node, f"{name}() takes {n} argument(s)")
                return INT
            ts = [self._expr(a) for a in node.args]
            if any(t not in NUMERIC for t in ts):
                self.err(node, f"{name}() needs numbers")
                return INT
            return FLOAT if FLOAT in ts else INT
        if name in ("int", "float"):
            if node.keywords or len(node.args) != 1:
                self.err(node, f"{name}() takes one argument")
                return INT if name == "int" else FLOAT
            if self._expr(node.args[0]) not in NUMERIC:
                self.err(node, f"{name}() needs a number")
            return INT if name == "int" else FLOAT
        self.err(node, f"unknown function '{name}'")
        for a in node.args:
            self._expr(a)
        return INT
