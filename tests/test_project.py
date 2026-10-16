import pytest

from pocketpsp.config import load_config, parse_config
from pocketpsp.frontend.diagnostics import DiagnosticError
from pocketpsp.project import create_project, load_project

OK = {"project": {"name": "X", "version": "1", "entry": "game.py"}, "build": {"target": "psp"}}


def test_valid_config():
    c = parse_config(OK)
    assert (c.name, c.entry, c.target) == ("X", "game.py", "psp")


@pytest.mark.parametrize("mutate,expected", [
    (lambda d: d["project"].update(name=""), "project.name"),
    (lambda d: d["project"].update(entry="game.txt"), "project.entry"),
    (lambda d: d["project"].update(entry="../evil.py"), "inside the project"),
    (lambda d: d["project"].update(entry="/abs.py"), "inside the project"),
    (lambda d: d["build"].update(target="vita"), "build.target"),
    (lambda d: d["project"].update(bogus=1), "unknown key 'bogus'"),
    (lambda d: d.update(extra={}), "unknown section"),
])
def test_invalid_config(mutate, expected):
    import copy
    d = copy.deepcopy(OK)
    mutate(d)
    with pytest.raises(DiagnosticError) as exc:
        parse_config(d)
    assert any(expected in x.message for x in exc.value.diagnostics)


def test_missing_config_is_clear(tmp_path):
    with pytest.raises(DiagnosticError, match="not found"):
        load_config(tmp_path / "project.toml")


def test_invalid_toml(tmp_path):
    (tmp_path / "project.toml").write_text("[project\n")
    with pytest.raises(DiagnosticError, match="invalid TOML"):
        load_config(tmp_path / "project.toml")


def test_create_project_from_template(tmp_path):
    root = create_project("My Game", tmp_path)
    assert (root / "game.py").is_file() and (root / "assets" / "player.png").is_file()
    assert (root / "assets" / "player.png").read_bytes().startswith(b"\x89PNG")
    assert load_project(root).config.name == "My Game"


def test_create_project_refuses_existing_and_bad_names(tmp_path):
    create_project("a", tmp_path)
    with pytest.raises(DiagnosticError, match="already exists"):
        create_project("a", tmp_path)
    for bad in ("../x", "a/b", "", '"q"', ".hidden"):
        with pytest.raises(DiagnosticError):
            create_project(bad, tmp_path)


def test_new_project_passes_check(tmp_path):
    from pocketpsp.build.builder import check_project
    check_project(load_project(create_project("ok", tmp_path)))


@pytest.mark.parametrize("name", ["hello-world", "pocket-jumper"])
def test_examples_pass_check(name):
    from pathlib import Path

    from pocketpsp.build.builder import check_project
    check_project(load_project(Path(__file__).resolve().parent.parent / "examples" / name))
