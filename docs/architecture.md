# Architecture

```
game.py ─ parser ─ validator ─ Program ─ codegen ─ game.c ─┐
                                                           ├─ make (PSP SDK) ─ EBOOT.PBP ─ PPSSPP
runtime/ (C, stb_image) ───────────────────────────────────┘
```

| Stage | Module | Notes |
|-------|--------|-------|
| Read/parse | `frontend/parser.py` | `ast.parse` only; syntax errors become diagnostics |
| Validate | `frontend/validator.py`, `symbols.py` | allow-list of constructs, type inference, symbol tables, collects all errors |
| Generate | `codegen/` | deterministic C from the typed AST (no string substitution of Python source) |
| Stage/build | `build/builder.py`, `toolchain.py` | copies runtime, runs `make -C build/native`, verifies `EBOOT.PBP` |
| Package | `build/package.py` | `dist/PSP/GAME/<name>/` |
| Run | `runner/ppsspp.py` | locate emulator, `<ppsspp> <EBOOT.PBP>` |
| CLI | `cli.py` | thin; `check --format json` feeds editors |

Design rules: the frontend never touches the SDK, so it is tested without it; external programs are
run with argument lists (no shell); a stale `EBOOT.PBP` is removed before each native build so a
failed build can never look successful; generated files live only in `build/` and `dist/`.

Editor integration: `editors/vscode` only calls the CLI (`build`, `run`, `check --format json`).
A level editor can reuse the same `frontend` package. Decisions: the runtime lives inside the Python
package (`templates/runtime`) so an installed `pocketpsp` is self-contained; `runner/debug.py` was
not created because no debugging is implemented.

Runtime notes (unverified on hardware): 2D rendering uses `sceGu` textured sprites; PNG decoding
uses stb_image; exiting via HOME uses the standard exit callback.
