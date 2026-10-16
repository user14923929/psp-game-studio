import pytest

from pocketpsp.build.builder import BuildError, build_project, check_project
from pocketpsp.build.package import folder_name, package_project
from pocketpsp.build.toolchain import ToolchainError, find_toolchain
from pocketpsp.frontend.diagnostics import DiagnosticError
from pocketpsp.project import load_project


def test_find_toolchain_without_sdk(clean_env):
    with pytest.raises(ToolchainError, match="PSP SDK not found"):
        find_toolchain(clean_env)


def test_build_without_sdk_fails_cleanly(project_dir, monkeypatch, clean_env):
    with pytest.raises(BuildError, match="PSP SDK not found"):
        build_project(load_project(project_dir))
    assert not (project_dir / "build" / "psp").exists()


def test_missing_asset_is_reported(project_dir):
    (project_dir / "assets" / "player.png").unlink()
    with pytest.raises(DiagnosticError, match="file not found"):
        check_project(load_project(project_dir))


def test_source_errors_stop_before_native_build(project_dir):
    (project_dir / "game.py").write_text("import os\n")
    with pytest.raises(DiagnosticError):
        build_project(load_project(project_dir))
    assert not (project_dir / "build" / "native").exists()


def test_successful_build_with_fake_make(project_dir, fake_toolchain):
    tc = fake_toolchain('echo built; echo PBP > EBOOT.PBP')
    res = build_project(load_project(project_dir), tc)
    assert res.eboot.is_file()
    assert (res.output_dir / "assets" / "player.png").is_file()
    assert "built" in res.log.read_text()
    assert (project_dir / "build" / "native" / "game.c").is_file()
    assert "PSP_EBOOT_TITLE = demo" in (project_dir / "build" / "native" / "Makefile").read_text()


def test_failing_make_is_not_success(project_dir, fake_toolchain):
    tc = fake_toolchain('echo "game.c:1: error: boom"; exit 2')
    with pytest.raises(BuildError, match="exit code 2") as exc:
        build_project(load_project(project_dir), tc)
    assert "boom" in exc.value.log.read_text()
    assert not (project_dir / "build" / "psp").exists()


def test_make_without_eboot_is_failure(project_dir, fake_toolchain):
    with pytest.raises(BuildError, match="EBOOT.PBP was not produced"):
        build_project(load_project(project_dir), fake_toolchain("exit 0"))


def test_stale_eboot_does_not_mask_failure(project_dir, fake_toolchain):
    project = load_project(project_dir)
    build_project(project, fake_toolchain("echo x > EBOOT.PBP"))
    with pytest.raises(BuildError):
        build_project(project, fake_toolchain("exit 1"))
    assert not (project_dir / "build" / "psp" / "EBOOT.PBP").exists()


def test_package_layout(project_dir, fake_toolchain):
    project = load_project(project_dir)
    res = build_project(project, fake_toolchain("echo x > EBOOT.PBP"))
    dest = package_project(project, res)
    assert dest == project_dir / "dist" / "PSP" / "GAME" / "demo"
    assert (dest / "EBOOT.PBP").is_file() and (dest / "assets" / "player.png").is_file()


def test_folder_name():
    assert folder_name("My Game!") == "My_Game"
    assert folder_name("???") == "game"
