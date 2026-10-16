# PSP Game Studio (`pocketpsp`)

Write Sony PSP homebrew games in a small, restricted subset of Python. `pocketpsp` checks
your code, generates C, builds it with the PSP SDK, produces `EBOOT.PBP` and can launch it in PPSSPP.

```python
from pocketpsp import Game, Sprite, Button

game = Game(title="Pocket Jumper")
player = Sprite("assets/player.png", x=100, y=100)

@game.update
def update():
    if Button.held("LEFT"):
        player.x -= 2
    if Button.held("RIGHT"):
        player.x += 2

@game.draw
def draw():
    game.clear(30, 40, 70)
    player.draw()

game.run()
```

This is **not** a Python interpreter. Your code is parsed with `ast`, validated against an explicit
list of supported constructs, and translated to C. Anything unsupported is a compile error with a
file and line. Nothing is ever run with `exec`/`eval`.

## Quick start

```sh
pip install -e .            # Python 3.11+, no runtime dependencies
pocketpsp doctor            # check make, PSP SDK, PPSSPP
pocketpsp new "My Game" && cd "My Game"
pocketpsp check
pocketpsp run               # build + launch in PPSSPP
```

Commands: `new`, `doctor`, `check`, `build`, `run`, `clean`, `package`.
See [docs/getting-started.md](docs/getting-started.md), [docs/installation.md](docs/installation.md),
[docs/python-api.md](docs/python-api.md) and [docs/architecture.md](docs/architecture.md).

## Status (v0.1.0)

Verified by automated tests (no PSP SDK needed): CLI, project templates, config validation,
the DSL validator, C generation (generated C is compiled warning-free and executed on the host
with a stub runtime), build orchestration and failure handling (with a fake toolchain), PPSSPP
discovery and launch command.

**Not yet verified:** compiling the runtime with a real PSP SDK, running in PPSSPP and on real
hardware. The runtime uses pspsdk APIs written from the SDK's documented samples; the first run on a
machine with pspdev may need small fixes. `tests/test_integration.py` performs a real build when
the SDK is present. There is no debugger and no hot reload.

## Third-party

- [stb_image](https://github.com/nothings/stb) v2.30 (PNG decoding in the runtime): public domain / MIT.
- pspsdk / pspdev and PPSSPP are external tools, installed separately.

License: GPL-3.0-only.
