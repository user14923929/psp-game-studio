"""Find PPSSPP on Linux and launch a built EBOOT.PBP.

PPSSPP is started as ``<ppsspp> <path-to-EBOOT.PBP>``, which is its documented
way of loading a game. No other arguments are passed, and this is a plain
launch: there is no debugger or hot-reload integration.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

CANDIDATES = ("PPSSPPSDL", "ppsspp", "PPSSPPQt", "PPSSPP")
FLATPAK_ID = "org.ppsspp.PPSSPP"


class RunnerError(Exception):
    """PPSSPP is missing or failed to start."""


def find_ppsspp(explicit: str | None = None,
                env: Mapping[str, str] | None = None) -> list[str]:
    """Return the argv prefix that starts PPSSPP, or raise RunnerError."""
    env = os.environ if env is None else env
    for label, value in (("--ppsspp", explicit), ("$POCKETPSP_PPSSPP", env.get("POCKETPSP_PPSSPP"))):
        if value:
            path = shutil.which(value, path=env.get("PATH"))
            if path is None:
                raise RunnerError(f"{label} points to '{value}', which is not an executable file")
            return [path]
    for name in CANDIDATES:
        path = shutil.which(name, path=env.get("PATH"))
        if path:
            return [path]
    flatpak = shutil.which("flatpak", path=env.get("PATH"))
    if flatpak:
        try:
            ok = subprocess.run([flatpak, "info", FLATPAK_ID], capture_output=True,
                                timeout=30, check=False).returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
        if ok:
            return [flatpak, "run", FLATPAK_ID]
    raise RunnerError(
        "PPSSPP was not found. Install it (see docs/installation.md), put it in PATH, "
        "or set $POCKETPSP_PPSSPP / pass --ppsspp PATH.")


def launch_command(prefix: list[str], eboot: Path) -> list[str]:
    return [*prefix, str(eboot)]


def run_game(prefix: list[str], eboot: Path) -> int:
    """Run PPSSPP and wait for it; returns its exit code."""
    if not eboot.is_file():
        raise RunnerError(f"{eboot} does not exist; build the project first")
    try:
        return subprocess.run(launch_command(prefix, eboot), check=False).returncode
    except OSError as exc:
        raise RunnerError(f"could not start PPSSPP: {exc}") from None
    except KeyboardInterrupt:
        return 130
