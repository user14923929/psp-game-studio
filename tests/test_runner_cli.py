import pytest

from conftest import make_script
from pocketpsp.cli import main
from pocketpsp.runner.ppsspp import RunnerError, find_ppsspp, launch_command


def test_ppsspp_not_found(clean_env):
    with pytest.raises(RunnerError, match="PPSSPP was not found"):
        find_ppsspp(env=clean_env)


def test_ppsspp_found_in_path(tmp_path, clean_env):
    exe = make_script(tmp_path / "emptybin" / "PPSSPPSDL", "exit 0")
    assert find_ppsspp(env=clean_env) == [str(exe)]


def test_ppsspp_explicit_and_env_override(tmp_path, clean_env):
    exe = make_script(tmp_path / "custom-ppsspp", "exit 0")
    assert find_ppsspp(str(exe), env=clean_env) == [str(exe)]
    assert find_ppsspp(env={**clean_env, "POCKETPSP_PPSSPP": str(exe)}) == [str(exe)]
    with pytest.raises(RunnerError, match="not an executable"):
        find_ppsspp(str(tmp_path / "missing"), env=clean_env)


def test_launch_command_has_only_the_eboot(tmp_path):
    assert launch_command(["/usr/bin/PPSSPPSDL"], tmp_path / "EBOOT.PBP") == [
        "/usr/bin/PPSSPPSDL", str(tmp_path / "EBOOT.PBP")]


def test_cli_new_check_clean(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "g1"]) == 0
    monkeypatch.chdir(tmp_path / "g1")
    assert main(["check"]) == 0
    (tmp_path / "g1" / "build").mkdir()
    assert main(["clean"]) == 0
    assert not (tmp_path / "g1" / "build").exists()
    assert (tmp_path / "g1" / "game.py").exists() and (tmp_path / "g1" / "assets").exists()


def test_cli_check_reports_file_and_line(project_dir, capsys):
    (project_dir / "game.py").write_text("import os\n")
    assert main(["-C", str(project_dir), "check"]) == 1
    assert "game.py:1:1: error:" in capsys.readouterr().err


def test_cli_check_json(project_dir, capsys):
    import json
    (project_dir / "game.py").write_text("import os\n")
    assert main(["-C", str(project_dir), "check", "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data[0]["line"] == 1 and data[0]["severity"] == "error"


def test_cli_outside_project(tmp_path, capsys):
    assert main(["-C", str(tmp_path), "build"]) == 1
    assert "project.toml not found" in capsys.readouterr().err


def test_cli_build_without_sdk_returns_error(project_dir, clean_env, capsys):
    assert main(["-C", str(project_dir), "build"]) == 1
    err = capsys.readouterr()
    assert "build succeeded" not in err.out and "PSP SDK not found" in err.err


def test_cli_run_without_ppsspp_fails_before_building(project_dir, clean_env, capsys):
    assert main(["-C", str(project_dir), "run"]) == 1
    assert "PPSSPP was not found" in capsys.readouterr().err
    assert not (project_dir / "build").exists()


def test_cli_run_launches_built_eboot(project_dir, fake_toolchain, tmp_path, monkeypatch, capsys):
    tc = fake_toolchain("echo x > EBOOT.PBP")
    log = tmp_path / "args.txt"
    emu = make_script(tmp_path / "emu", f'echo "$@" > {log}')
    monkeypatch.setattr("pocketpsp.build.builder.find_toolchain", lambda: tc)
    assert main(["-C", str(project_dir), "run", "--ppsspp", str(emu)]) == 0
    assert log.read_text().strip() == str(project_dir / "build" / "psp" / "EBOOT.PBP")


def test_cli_run_failed_build_never_launches(project_dir, fake_toolchain, tmp_path, monkeypatch):
    tc = fake_toolchain("exit 1")
    marker = tmp_path / "launched"
    emu = make_script(tmp_path / "emu", f"touch {marker}")
    monkeypatch.setattr("pocketpsp.build.builder.find_toolchain", lambda: tc)
    assert main(["-C", str(project_dir), "run", "--ppsspp", str(emu)]) == 1
    assert not marker.exists()
