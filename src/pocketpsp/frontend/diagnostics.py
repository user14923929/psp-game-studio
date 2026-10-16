"""Structured diagnostics shared by every compiler stage."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Diagnostic:
    """One problem found in a source file or configuration."""

    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None  # 1-based
    severity: str = "error"

    def format(self) -> str:
        loc = self.file or "<input>"
        if self.line is not None:
            loc += f":{self.line}"
            if self.column is not None:
                loc += f":{self.column}"
        return f"{loc}: {self.severity}: {self.message}"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class DiagnosticError(Exception):
    """Raised when a stage fails; carries every diagnostic collected so far."""

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        super().__init__("; ".join(d.format() for d in diagnostics))
        self.diagnostics = diagnostics
