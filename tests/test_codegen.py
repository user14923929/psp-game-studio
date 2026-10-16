import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import GOOD
from pocketpsp.codegen.generator import c_string, generate_c, module_name
from pocketpsp.frontend.parser import parse_source
from pocketpsp.frontend.validator import validate

ROOT = Path(__file__).resolve().parent
HOST = ROOT / "fixtures" / "host"
RUNTIME_INC = ROOT.parent / "src" / "pocketpsp" / "templates" / "runtime" / "include"


def gen(src: str) -> str:
    return generate_c(validate(parse_source(src, "g.py"), "g.py"))


HEAD = 'from pocketpsp import Game, Sprite, Button\ngame = Game(title="T")\n'


def update_src(body: str, extra: str = "") -> str:
    lines = "\n".join("    " + ln for ln in body.splitlines())
    return f"{HEAD}{extra}\n@game.update\ndef update():\n{lines}\n\ngame.run()\n"


def test_generation_is_deterministic():
    assert gen(GOOD) == gen(GOOD)


def test_good_program_structure():
    c = gen(GOOD)
    assert '#include "pocketpsp/pocketpsp.h"' in c
    assert 'PSP_MODULE_INFO("test_game"' in c
    assert "spr_player.x = (spr_player.x - g_speed);" in c
    assert "pp_button_held(PSP_CTRL_LEFT)" in c
    assert "pp_clear(30, 40, 70);" in c
    assert "pp_sprite_load(&spr_player, \"assets/player.png\", 100.0f, 100.0f);" in c


def test_arithmetic_semantics():
    c = gen(update_src("a = 7\nb = a // 2\nc = a % 3\nd = a / 2\ne = -a"))
    assert "pp_floordiv(v_a, 2)" in c and "pp_mod(v_a, 3)" in c
    assert "((float)v_a / (float)2)" in c


def test_for_range_and_negative_step():
    c = gen(update_src("t = 0\nfor i in range(10, 0, -2):\n    t += i"))
    assert "i_1 > stop_1; i_1 += -2" in c


def test_int_widened_to_float_on_assignment():
    c = gen(update_src("x = 1.5\nx = 2"))
    assert "v_x = ((float)2);" in c


def test_c_string_escapes():
    assert c_string('a"b\\c') == '"a\\"b\\\\c"'
    assert c_string("é") == '"\\303\\251"'
    assert c_string("??/") == '"\\077\\077/"'


def test_module_name():
    assert module_name("Pocket Jumper!") == "pocket_jumper"
    assert module_name("###") == "game"
    assert len(module_name("x" * 100)) <= 26


needs_gcc = pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc not available")


def build_host(tmp_path: Path, src: str) -> Path:
    (tmp_path / "game.c").write_text(gen(src))
    exe = tmp_path / "game"
    r = subprocess.run(
        ["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fwrapv", f"-I{HOST}",
         f"-I{RUNTIME_INC}", str(tmp_path / "game.c"), str(HOST / "harness.c"), "-lm",
         "-o", str(exe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return exe


@needs_gcc
def test_generated_c_compiles_warning_free_on_host(tmp_path):
    build_host(tmp_path, GOOD)


@needs_gcc
def test_generated_code_runs_on_host(tmp_path):
    exe = build_host(tmp_path, GOOD)
    out = subprocess.run([str(exe), "3", "0"], capture_output=True, text=True).stdout
    assert out.strip() == "clears=3 draws=3"


@needs_gcc
def test_python_floor_semantics_match(tmp_path):
    from pocketpsp.codegen.generator import generate_c  # noqa: F401
    src = update_src("a = -7\nb = a // 2\nc = a % 3\nif b != -4:\n    game.clear(0, 0, 0)\n"
                     "if c != 2:\n    game.clear(0, 0, 0)\n")
    exe = build_host(tmp_path, src)
    out = subprocess.run([str(exe), "1", "0"], capture_output=True, text=True).stdout
    assert "clears=0" in out  # -7 // 2 == -4 and -7 % 3 == 2, as in Python
