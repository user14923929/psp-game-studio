"""Optional tests that need the real PSP SDK. Skipped when it is not installed."""

import pytest

from pocketpsp.build.builder import build_project
from pocketpsp.build.toolchain import ToolchainError, find_toolchain
from pocketpsp.project import create_project, load_project

pytestmark = pytest.mark.integration


def test_real_psp_build(tmp_path):
    try:
        tc = find_toolchain()
    except ToolchainError:
        pytest.skip("PSP SDK not installed")
    res = build_project(load_project(create_project("real", tmp_path)), tc)
    assert res.eboot.stat().st_size > 0
