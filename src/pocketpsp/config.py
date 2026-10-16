"""Load and validate ``project.toml``."""

from __future__ import annotations

import posixpath
import tomllib
from dataclasses import dataclass
from pathlib import Path

from pocketpsp.frontend.diagnostics import Diagnostic, DiagnosticError

CONFIG_NAME = "project.toml"
KNOWN_TARGETS = ("psp",)
_ALLOWED = {"project": {"name", "version", "entry"}, "build": {"target"}}


@dataclass(frozen=True)
class Config:
    name: str
    version: str
    entry: str
    target: str


def load_config(path: Path) -> Config:
    """Parse ``path`` and return a validated :class:`Config`."""
    f = str(path)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DiagnosticError([Diagnostic(
            f"{CONFIG_NAME} not found; run this command inside a pocketpsp project "
            "(create one with 'pocketpsp new NAME')", f)]) from None
    except tomllib.TOMLDecodeError as exc:
        raise DiagnosticError([Diagnostic(f"invalid TOML: {exc}", f)]) from None
    except (OSError, UnicodeDecodeError) as exc:
        raise DiagnosticError([Diagnostic(f"cannot read configuration: {exc}", f)]) from None
    return parse_config(data, f)


def parse_config(data: dict[str, object], filename: str = CONFIG_NAME) -> Config:
    errs: list[Diagnostic] = []

    def err(msg: str) -> None:
        errs.append(Diagnostic(msg, filename))

    for section, body in data.items():
        if section not in _ALLOWED:
            err(f"unknown section [{section}]")
        elif not isinstance(body, dict):
            err(f"[{section}] must be a table")
        else:
            for key in body:
                if key not in _ALLOWED[section]:
                    err(f"unknown key '{key}' in [{section}]")
    project = data.get("project")
    build = data.get("build", {})
    if not isinstance(project, dict):
        err("missing [project] section")
        project = {}
    if not isinstance(build, dict):
        build = {}

    name = project.get("name")
    if not isinstance(name, str) or not name.strip():
        err("project.name must be a non-empty string")
        name = ""
    elif len(name) > 64 or any(ord(c) < 32 for c in name):
        err("project.name must be at most 64 printable characters")
    version = project.get("version", "0.1.0")
    if not isinstance(version, str) or not version.strip():
        err("project.version must be a non-empty string")
        version = ""
    entry = project.get("entry", "game.py")
    if not isinstance(entry, str) or not entry.endswith(".py"):
        err("project.entry must be a relative path ending in .py")
        entry = ""
    elif entry.startswith("/") or "\\" in entry or posixpath.normpath(entry).startswith(".."):
        err("project.entry must stay inside the project directory")
        entry = ""
    target = build.get("target", "psp")
    if target not in KNOWN_TARGETS:
        err(f"build.target must be one of: {', '.join(KNOWN_TARGETS)} (got {target!r})")
        target = ""
    if errs:
        raise DiagnosticError(errs)
    return Config(name, version, entry, target)
