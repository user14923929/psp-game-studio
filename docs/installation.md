# Installation

System dependencies and Python dependencies are separate. `pocketpsp` itself has **no** Python
runtime dependencies. No root rights are needed to create projects, build or run games.

## 1. pocketpsp

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e .          # or: pip install -e ".[dev]" for tests and linters
```

Arch/CachyOS users can use the provided `PKGBUILD`; Debian/Mint users the `debian/` directory
(untested package builds).

## 2. System tools

| Tool | Arch / CachyOS | Linux Mint (Ubuntu/Debian) |
|------|----------------|----------------------------|
| Python 3.11+, make | `sudo pacman -S python make` | `sudo apt install python3 python3-venv make` |
| PPSSPP (optional, for `run`) | `sudo pacman -S ppsspp` | `sudo apt install ppsspp` or `flatpak install flathub org.ppsspp.PPSSPP` |

## 3. PSP SDK (pspdev)

Install **pspdev** following the official instructions at <https://pspdev.github.io/> (a prebuilt
toolchain release or building from source). Then make it discoverable by one of:

- `export PSPDEV=/path/to/pspdev` and `export PATH="$PSPDEV/bin:$PATH"` (add to your shell profile),
- or install to `/usr/local/pspdev`, which `pocketpsp` also checks.

Verify with `pocketpsp doctor`. `pocketpsp` locates the SDK via `psp-config --pspsdk-path`
and requires `lib/build.mak` in it.

## PPSSPP lookup order

`--ppsspp PATH`, then `$POCKETPSP_PPSSPP`, then `PPSSPPSDL`, `ppsspp`, `PPSSPPQt`, `PPSSPP` in
`PATH`, then the Flatpak `org.ppsspp.PPSSPP`. Flatpak sandboxing may prevent access to project
directories outside your home; if the game does not start, use a native build or grant access.

## Troubleshooting

- `PSP SDK not found`: `psp-config` is not in `PATH`/`$PSPDEV/bin`. Run `pocketpsp doctor`.
- `native build failed`: read `build/logs/build.log` (full compiler output).
- `sprite ...: file not found`: sprite paths are relative to the project root.
- Game starts but sprites are missing: assets must sit next to `EBOOT.PBP` (`build/psp/assets`).
