"""Project discovery and creation from templates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from string import Template

from pocketpsp.build.assets import make_png
from pocketpsp.config import CONFIG_NAME, Config, load_config
from pocketpsp.frontend.diagnostics import Diagnostic, DiagnosticError

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")


@dataclass(frozen=True)
class Project:
    root: Path
    config: Config

    @property
    def entry_path(self) -> Path:
        return self.root / self.config.entry

    @property
    def build_dir(self) -> Path:
        return self.root / "build"


def load_project(root: Path) -> Project:
    root = root.resolve()
    return Project(root, load_config(root / CONFIG_NAME))


def create_project(name: str, parent: Path) -> Path:
    """Create ``parent/name`` from the bundled template and return its path."""
    if not _NAME_RE.match(name) or name.endswith("."):
        raise DiagnosticError([Diagnostic(
            "project name must start with a letter or digit and contain only letters, "
            "digits, spaces, '.', '_' or '-' (max 64 characters)")])
    root = parent / name
    if root.exists():
        raise DiagnosticError([Diagnostic(f"'{root}' already exists", str(root))])
    tpl = resources.files("pocketpsp").joinpath("templates/project")
    mapping = {"name": name}
    (root / "assets").mkdir(parents=True)
    for tmpl_name, out_name in (("project.toml.tmpl", CONFIG_NAME), ("game.py.tmpl", "game.py"),
                                ("gitignore.tmpl", ".gitignore")):
        text = Template(tpl.joinpath(tmpl_name).read_text(encoding="utf-8")).substitute(mapping)
        (root / out_name).write_text(text, encoding="utf-8")
    (root / "assets" / "player.png").write_bytes(make_png(32, 32, (240, 200, 40, 255)))
    return root
