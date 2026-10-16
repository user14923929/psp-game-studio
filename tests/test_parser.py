import pytest

from pocketpsp.frontend.diagnostics import DiagnosticError
from pocketpsp.frontend.parser import parse_source, read_source


def test_parses_valid_source():
    assert parse_source("x = 1\n", "g.py").body


def test_syntax_error_has_file_and_line():
    with pytest.raises(DiagnosticError) as exc:
        parse_source("x = (1\n", "g.py")
    d = exc.value.diagnostics[0]
    assert d.file == "g.py" and d.line is not None
    assert d.format().startswith("g.py:")


def test_null_bytes_are_reported():
    with pytest.raises(DiagnosticError):
        parse_source("x = 1\0", "g.py")


def test_missing_file(tmp_path):
    with pytest.raises(DiagnosticError, match="not found"):
        read_source(tmp_path / "nope.py")


def test_non_utf8_file(tmp_path):
    p = tmp_path / "g.py"
    p.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(DiagnosticError, match="UTF-8"):
        read_source(p)
