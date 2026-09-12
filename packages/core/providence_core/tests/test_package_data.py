"""Package-data smoke tests for the built providence-core wheel."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_built_wheel_exposes_canonical_specs_via_importlib_resources(
    tmp_path: Path,
) -> None:
    """A non-editable wheel install must expose the bundled governance specs."""
    package_dir = Path(__file__).resolve().parents[1]
    source_copy = tmp_path / "providence_core_src"
    wheelhouse = tmp_path / "wheelhouse"
    target = tmp_path / "install"
    env = os.environ.copy()
    env["PIP_CACHE_DIR"] = str(tmp_path / "pip-cache")
    env["UV_CACHE_DIR"] = str(tmp_path / "uv-cache")
    uv = shutil.which("uv")
    assert uv is not None, "uv executable is required for package build smoke tests"

    def _ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name == "build"
            or name == "tests"
            or name == "__pycache__"
            or name == ".coverage"
            or name.endswith(".egg-info")
            or name.endswith(".link")
            or name.endswith(".pyc")
        }

    shutil.copytree(package_dir, source_copy, symlinks=False, ignore=_ignore)
    native_dir = source_copy / "src" / "providence_core" / "_native"
    native_dir.mkdir(parents=True)
    (native_dir / "sdd-compile-linux-amd64").write_text("fake-native", encoding="utf-8")
    (native_dir / "sdd-compile-windows-amd64.exe").write_text(
        "fake-native", encoding="utf-8"
    )

    build_result = subprocess.run(
        [
            uv,
            "build",
            "--wheel",
            "--no-build-isolation",
            "--out-dir",
            str(wheelhouse),
            str(source_copy),
        ],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )
    assert build_result.returncode == 0, build_result.stdout + build_result.stderr

    wheel = next(wheelhouse.glob("providence_core-*.whl"))
    install_result = subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--python",
            sys.executable,
            "--no-deps",
            "--target",
            str(target),
            str(wheel),
        ],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )
    assert install_result.returncode == 0, install_result.stdout + install_result.stderr

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib.resources as r, json, platform; "
                "root = r.files('providence_core'); "
                "system = platform.system().lower(); "
                "goos = {'linux': 'linux', 'windows': 'windows'}.get(system, system); "
                "asset = 'sdd-compile-' + goos + '-amd64' + "
                "('.exe' if goos == 'windows' else ''); "
                "print(json.dumps({"
                "'mandate.spec': (root / 'mandate.spec').read_text(encoding='utf-8'), "
                "'guidelines.dsl': (root / 'guidelines.dsl').read_text(encoding='utf-8'), "
                "'native_asset_exists': (root / '_native' / asset).is_file()"
                "}))"
            ),
        ],
        check=False,
        capture_output=True,
        env={**env, "PYTHONPATH": str(target)},
        text=True,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr

    resources = json.loads(probe.stdout)
    assert "mandate M001" in resources["mandate.spec"]
    assert "guideline G01" in resources["guidelines.dsl"]
    assert resources["native_asset_exists"] is True
