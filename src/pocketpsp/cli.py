"""Command line interface: ``pocketpsp``."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

from pocketpsp import __version__
from pocketpsp.build.builder import BuildError, BuildResult, build_project, check_project
from pocketpsp.build.package import package_project
from pocketpsp.build.toolchain import ToolchainError, find_make, find_psp_config, find_toolchain
from pocketpsp.frontend.diagnostics import Diagnostic, DiagnosticError
from pocketpsp.project import Project, create_project, load_project
from pocketpsp.runner.ppsspp import RunnerError, find_ppsspp, run_game


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _report(diags: list[Diagnostic]) -> None:
    for d in diags:
        _err(d.format())


def _open(root: Path) -> Project | None:
    try:
        return load_project(root)
    except DiagnosticError as exc:
        _report(exc.diagnostics)
        return None


def _build(project: Project) -> BuildResult | None:
    try:
        return build_project(project, say=print)
    except DiagnosticError as exc:
        _report(exc.diagnostics)
        _err("build failed: source has errors")
    except BuildError as exc:
        _err(f"error: {exc}")
        if exc.log:
            _err(f"build output saved to {exc.log}")
    return None


def cmd_new(args: argparse.Namespace) -> int:
    try:
        root = create_project(args.name, Path.cwd())
    except DiagnosticError as exc:
        _report(exc.diagnostics)
        return 1
    print(f"created project in {root}")
    print(f"next: cd '{args.name}' && pocketpsp check")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    project = _open(args.dir)
    if project is None:
        return 1
    try:
        check_project(project)
    except DiagnosticError as exc:
        if args.format == "json":
            print(json.dumps([d.to_dict() for d in exc.diagnostics]))
        else:
            _report(exc.diagnostics)
            _err(f"check failed: {len(exc.diagnostics)} error(s)")
        return 1
    print("[]" if args.format == "json" else "check passed: no problems found")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    project = _open(args.dir)
    if project is None:
        return 1
    result = _build(project)
    if result is None:
        return 1
    print(f"build succeeded: {result.eboot}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    project = _open(args.dir)
    if project is None:
        return 1
    try:
        prefix = find_ppsspp(args.ppsspp)  # fail early, before a long build
    except RunnerError as exc:
        _err(f"error: {exc}")
        return 1
    result = _build(project)
    if result is None:
        return 1
    print(f"launching {' '.join(prefix)}")
    try:
        code = run_game(prefix, result.eboot)
    except RunnerError as exc:
        _err(f"error: {exc}")
        return 1
    if code != 0:
        _err(f"PPSSPP exited with code {code}")
    return code


def cmd_package(args: argparse.Namespace) -> int:
    project = _open(args.dir)
    if project is None:
        return 1
    result = _build(project)
    if result is None:
        return 1
    dest = package_project(project, result)
    print(f"packaged game: {dest}")
    print("copy this folder to ms0:/PSP/GAME/ on a memory stick (or PPSSPP's memstick directory)")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    project = _open(args.dir)
    if project is None:
        return 1
    removed = []
    for d in (project.build_dir, project.root / "dist"):
        if d.is_dir() and not d.is_symlink():
            shutil.rmtree(d)
            removed.append(d.name)
    print("removed: " + (", ".join(removed) if removed else "nothing to clean"))
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    ok = True
    py = sys.version_info
    py_ok = py >= (3, 11)
    print(f"[{'ok' if py_ok else 'FAIL'}] Python {platform.python_version()} (3.11+ required)")
    ok &= py_ok
    make = find_make()
    print(f"[{'ok' if make else 'FAIL'}] make: {make or 'not found'}")
    ok &= make is not None
    cfg = find_psp_config()
    if cfg is None:
        print("[FAIL] PSP SDK: psp-config not found (set PSPDEV or add it to PATH)")
        ok = False
    else:
        try:
            tc = find_toolchain()
            print(f"[ok] PSP SDK: {tc.sdk_path}")
            gcc = shutil.which("psp-gcc", path=tc.env()["PATH"])
            print(f"[{'ok' if gcc else 'FAIL'}] psp-gcc: {gcc or 'not found'}")
            ok &= gcc is not None
        except ToolchainError as exc:
            print(f"[FAIL] PSP SDK: {exc}")
            ok = False
    try:
        print(f"[ok] PPSSPP: {' '.join(find_ppsspp())}")
    except RunnerError:
        print("[warn] PPSSPP: not found (optional; needed only for 'pocketpsp run')")
    print("all required tools found" if ok else "some required tools are missing; "
          "see docs/installation.md")
    return 0 if ok else 1


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pocketpsp", description="Build PSP games from a Python DSL.")
    p.add_argument("--version", action="version", version=f"pocketpsp {__version__}")
    p.add_argument("-C", dest="dir", type=Path, default=Path.cwd(), metavar="DIR",
                   help="project directory (default: current directory)")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("new", help="create a project from the template")
    s.add_argument("name", metavar="PROJECT_NAME")
    s.set_defaults(func=cmd_new)
    sub.add_parser("doctor", help="check tools: make, PSP SDK, PPSSPP").set_defaults(func=cmd_doctor)
    s = sub.add_parser("check", help="validate the game source")
    s.add_argument("--format", choices=("text", "json"), default="text")
    s.set_defaults(func=cmd_check)
    sub.add_parser("build", help="check, generate C, compile, create EBOOT.PBP").set_defaults(func=cmd_build)
    s = sub.add_parser("run", help="build and launch in PPSSPP")
    s.add_argument("--ppsspp", metavar="PATH", help="PPSSPP executable")
    s.set_defaults(func=cmd_run)
    sub.add_parser("clean", help="remove build/ and dist/").set_defaults(func=cmd_clean)
    sub.add_parser("package", help="build and prepare dist/PSP/GAME/<name>").set_defaults(func=cmd_package)
    return p


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        _err("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
