"""Read game source and turn it into a Python AST (never executes it)."""

from __future__ import annotations

import ast
from pathlib import Path

from pocketpsp.frontend.diagnostics import Diagnostic, DiagnosticError


def read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise DiagnosticError([Diagnostic(f"entry file not found: {path}", str(path))]) from None
    except UnicodeDecodeError as exc:
        raise DiagnosticError([Diagnostic(f"file is not valid UTF-8: {exc.reason}", str(path))]) from None
    except OSError as exc:
        raise DiagnosticError([Diagnostic(f"cannot read file: {exc.strerror}", str(path))]) from None


def parse_source(source: str, filename: str) -> ast.Module:
    """Parse ``source`` with :mod:`ast`; syntax errors become diagnostics."""
    try:
        return ast.parse(source, filename=filename, mode="exec")
    except SyntaxError as exc:
        col = exc.offset if exc.offset else None
        raise DiagnosticError(
            [Diagnostic(exc.msg, filename, exc.lineno, col)]
        ) from None
    except (ValueError, RecursionError) as exc:
        raise DiagnosticError([Diagnostic(f"cannot parse source: {exc}", filename)]) from None
