# Getting started

```sh
pocketpsp new "My Game"     # creates project.toml, game.py, assets/player.png
cd "My Game"
pocketpsp check             # validate the DSL only (no SDK needed)
pocketpsp build             # check -> C -> PSP SDK make -> build/psp/EBOOT.PBP
pocketpsp run               # build, then launch build/psp/EBOOT.PBP in PPSSPP
pocketpsp package           # dist/PSP/GAME/<name>/ for a memory stick
pocketpsp clean             # removes build/ and dist/ only
```

Use `pocketpsp -C DIR <command>` to operate on another directory.

## project.toml

```toml
[project]
name = "Pocket Jumper"   # shown as title; 1-64 printable characters
version = "0.1.0"
entry = "game.py"        # relative .py path inside the project

[build]
target = "psp"
```

Unknown keys and invalid values are reported by name.

## Build layout

```
build/native/game.c        generated C (never edit)
build/native/runtime/      copy of the runtime sources
build/logs/build.log       full output of make
build/psp/EBOOT.PBP        result, plus build/psp/assets/ (only referenced sprites)
```

Your sources are never overwritten. Examples: `examples/hello-world`, `examples/pocket-jumper`.
