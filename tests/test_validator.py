import pytest

from conftest import GOOD
from pocketpsp.frontend.diagnostics import DiagnosticError
from pocketpsp.frontend.parser import parse_source
from pocketpsp.frontend.validator import validate

HEAD = 'from pocketpsp import Game, Sprite, Button\ngame = Game(title="T")\n'
TAIL = "\ngame.run()\n"


def check(src: str):
    return validate(parse_source(src, "g.py"), "g.py")


def errors(src: str) -> list[str]:
    with pytest.raises(DiagnosticError) as exc:
        check(src)
    return [d.message for d in exc.value.diagnostics]


def body(fn_body: str, ret: str = "") -> str:
    lines = "\n".join("    " + ln for ln in fn_body.strip().splitlines())
    return f"{HEAD}\n@game.update\ndef update():\n{lines}\n{TAIL}".replace("update():", f"update(){ret}:")


def test_good_program():
    p = check(GOOD)
    assert p.title == "Test Game"
    assert set(p.funcs) == {"clampx", "update", "draw"}
    assert p.globals["speed"].type == "float"


def test_minimal_program_without_callbacks():
    assert check(HEAD + TAIL).title == "T"


@pytest.mark.parametrize("snippet,expected", [
    ("import os", "only 'from pocketpsp import"),
    ("from os import path", "only 'pocketpsp'"),
    ("from pocketpsp import Foo", "not part of the pocketpsp API"),
    ("class A: pass", "unsupported syntax: ClassDef"),
    ("x = [1, 2]", "module-level values"),
    ("with open('f') as f: pass", "unsupported syntax: With"),
])
def test_rejects_unsupported_module_level(snippet, expected):
    assert any(expected in m for m in errors(HEAD + snippet + TAIL))


@pytest.mark.parametrize("code,expected", [
    ("eval('1')", "unknown function 'eval'"),
    ("exec('x=1')", "unknown function 'exec'"),
    ("print(1)", "unknown function 'print'"),
    ("x = [1]", "unsupported syntax: List"),
    ("x = 'abc'", "string/other literals"),
    ("x = 1 if True else 2", "unsupported syntax: IfExp"),
    ("x = 2 ** 3", "unsupported syntax: operator Pow"),
    ("for i in [1, 2]:\n    pass", "range"),
    ("try:\n    pass\nexcept Exception:\n    pass", "unsupported syntax: Try"),
    ("lambda: 1", "has no effect"),
    ("x = undefined_name", "undefined name"),
    ("x = 1\nx = 1.5", "cannot assign float to int"),
    ("x = 1 < 2 < 3", "chained comparisons"),
    ("if 1:\n    pass", "condition must be a bool"),
    ("x = 7.5 // 2", "'//' and '%' only support int"),
    ("x = 1 // 0", "division by zero"),
    ("break", "outside a loop"),
    ("x = Button.held('NOPE')", "unknown button"),
    ("x = Button.held('LEFT') + 1", "arithmetic needs numbers"),
    ("game.clear(1, 2)", "expected game.clear"),
    ("while True:\n    pass\nelse:\n    pass", "'else' on loops"),
    ("x = 1e999", "out of range"),
    ("x = 99999999999", "32 bits"),
])
def test_rejects_unsupported_statements(code, expected):
    assert any(expected in m for m in errors(body(code)))


def test_diagnostics_carry_line_and_column():
    with pytest.raises(DiagnosticError) as exc:
        check(body("x = [1]"))
    d = exc.value.diagnostics[0]
    assert d.file == "g.py" and d.line == 6 and d.column == 9


def test_collects_multiple_errors():
    assert len(errors(body("a = eval('1')\nb = exec('2')"))) >= 2


def test_missing_game_and_run():
    msgs = errors("x = 1\n")
    assert any("missing game declaration" in m for m in msgs)
    assert any("missing game.run()" in m for m in msgs)


def test_run_must_be_last():
    assert any("last statement" in m for m in errors(HEAD + "\ngame.run()\nx = 1\n"))


def test_assigning_module_var_needs_global():
    src = HEAD + "n = 0\n@game.update\ndef update():\n    n = 1\n" + TAIL
    assert any("already defined" in m for m in errors(src))


def test_function_must_return_on_all_paths():
    src = HEAD + "def f(a: int) -> int:\n    if a > 0:\n        return 1\n" + TAIL
    assert any("may end without returning" in m for m in errors(src))


def test_call_argument_types_checked():
    src = HEAD + "def f(a: int) -> int:\n    return a\n@game.update\ndef u():\n    x = f(1.5)\n" + TAIL
    assert any("expected int argument" in m for m in errors(src))


def test_params_need_annotations():
    assert any("annotation" in m for m in errors(HEAD + "def f(a):\n    pass\n" + TAIL))


def test_sprite_path_must_be_safe():
    for path in ("../x.png", "/etc/x.png", "a.txt"):
        src = HEAD + f'p = Sprite("{path}")\n' + TAIL
        assert any("relative .png path" in m for m in errors(src)), path


def test_unsupported_decorator():
    src = HEAD + "@other\ndef f():\n    pass\n" + TAIL
    assert any("unsupported decorator" in m for m in errors(src))


def test_duplicate_update():
    src = HEAD + "@game.update\ndef a():\n    pass\n@game.update\ndef b():\n    pass\n" + TAIL
    assert any("only one" in m for m in errors(src))
