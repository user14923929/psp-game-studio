from __future__ import annotations

import os
import stat
import textwrap
from pathlib import Path

import pytest

from pocketpsp.build.toolchain import Toolchain
from pocketpsp.project import create_project

GOOD = textwrap.dedent('''\
    from pocketpsp import Game, Sprite, Button

    game = Game(title="Test Game")
    player = Sprite("assets/player.png", x=100, y=100)
    score = 0
    speed: float = 2


    def clampx(v: float) -> float:
        if v < 0:
            return 0
        elif v > 440:
            return 440
        else:
            return v


    @game.update
    def update():
        global score
        if Button.held("LEFT"):
            player.x -= speed
        if Button.held("RIGHT"):
            player.x += speed
        if Button.pressed("CROSS"):
            score += 1
        player.x = clampx(player.x)


    @game.draw
    def draw():
        game.clear(30, 40, 70)
        player.draw()


    game.run()
''')


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    return create_project("demo", tmp_path)


def make_script(path: Path, body: str) -> Path:
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture
def fake_toolchain(tmp_path: Path):
    """A stand-in toolchain whose 'make' just writes EBOOT.PBP. Tests plumbing only."""
    def factory(make_body: str) -> Toolchain:
        bin_dir = tmp_path / "fakebin"
        bin_dir.mkdir(exist_ok=True)
        sdk = tmp_path / "fakesdk"
        (sdk / "lib").mkdir(parents=True, exist_ok=True)
        (sdk / "lib" / "build.mak").write_text("")
        make = make_script(bin_dir / "make", 'cd "$2"\n' + make_body)  # called as: make -C DIR
        cfg = make_script(bin_dir / "psp-config", f'echo "{sdk}"')
        return Toolchain(cfg, sdk, make, (bin_dir,))
    return factory


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, str]:
    """An environment with an empty PATH so no real tools are found."""
    empty = tmp_path / "emptybin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    make_script(empty / "make", "exit 0")  # present, so tests reach the SDK check
    monkeypatch.delenv("PSPDEV", raising=False)
    monkeypatch.delenv("POCKETPSP_PPSSPP", raising=False)
    return {"PATH": str(empty), "HOME": os.fspath(tmp_path)}
