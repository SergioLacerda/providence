"""Contract tests for the `providence doctor compiler` report (stable JSON shape)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from providence_cli.services import doctor_compiler
from providence_cli.services.doctor_compiler import (
    REPORT_SCHEMA_VERSION,
    _current_packaged_digest,
    build_compiler_report,
    prune_cache,
    run_prune,
)

pytestmark = pytest.mark.unit

STABLE_TOP_LEVEL_KEYS = {
    "schema_version",
    "cli_version",
    "binary",
    "handshake",
    "cache",
    "packaged_native",
    "validate",
}


def _mock_runner(tmp_path: Path) -> MagicMock:
    runner = MagicMock()
    runner._binary = tmp_path / "sdd-compile"
    runner.resolution_rule = "download"
    runner.version.return_value = "sdd-compile 1.0.3"
    runner.verify_version_handshake.return_value = {
        "status": "ok",
        "binary_version": "1.0.3",
        "cli_version": "1.0.3",
    }
    return runner


def test_report_has_stable_top_level_keys(tmp_path: Path) -> None:
    with patch(
        "providence_core.utils.compiler_runner.CompilerRunner",
        return_value=_mock_runner(tmp_path),
    ):
        report = build_compiler_report(workspace_root=tmp_path)

    assert STABLE_TOP_LEVEL_KEYS.issubset(report.keys())
    assert report["schema_version"] == REPORT_SCHEMA_VERSION
    assert report["binary"]["resolved"] is True
    assert report["binary"]["resolution_rule"] == "download"
    assert report["handshake"]["status"] == "ok"
    assert report["validate"] == {
        "ran": False,
        "compiled_dir": str(tmp_path / ".providence" / "compiled"),
    }
    json.dumps(report)


def test_report_survives_unresolvable_binary(tmp_path: Path) -> None:
    with patch(
        "providence_core.utils.compiler_runner.CompilerRunner",
        side_effect=RuntimeError("binary not found"),
    ):
        report = build_compiler_report(workspace_root=tmp_path)

    assert STABLE_TOP_LEVEL_KEYS.issubset(report.keys())
    assert report["binary"] == {"resolved": False, "error": "binary not found"}
    assert report["handshake"] == {"status": "unavailable"}
    json.dumps(report)


def test_report_captures_skew_without_raising(tmp_path: Path) -> None:
    runner = _mock_runner(tmp_path)
    runner.verify_version_handshake.side_effect = RuntimeError(
        "compiler_version_skew: mismatch"
    )
    with patch(
        "providence_core.utils.compiler_runner.CompilerRunner", return_value=runner
    ):
        report = build_compiler_report(workspace_root=tmp_path)

    assert report["handshake"]["status"] == "skew"
    assert "compiler_version_skew" in report["handshake"]["error"]


def _make_cache(tmp_path: Path) -> Path:
    cache = tmp_path / "bin"
    for version in ("1.0.0", "1.0.3", "1.0.3.dev5+gabc"):
        (cache / version).mkdir(parents=True)
        (cache / version / "sdd-compile-linux-amd64").write_bytes(b"x")
    for digest in ("digest-current", "digest-stale"):
        (cache / "packaged" / digest).mkdir(parents=True)
        (cache / "packaged" / digest / "sdd-compile-linux-amd64").write_bytes(b"x")
    return cache


def test_prune_cache_keeps_current_versions_and_packaged_digest(
    tmp_path: Path,
) -> None:
    cache = _make_cache(tmp_path)

    result = prune_cache(
        cache,
        keep_versions=["1.0.3.dev5+gabc", "1.0.3"],
        keep_packaged_digest="digest-current",
    )

    assert sorted(result["removed"]) == ["1.0.0", "packaged/digest-stale"]
    assert not (cache / "1.0.0").exists()
    assert (cache / "1.0.3").exists()
    assert (cache / "1.0.3.dev5+gabc").exists()
    assert (cache / "packaged" / "digest-current").exists()
    assert not (cache / "packaged" / "digest-stale").exists()


def test_prune_cache_leaves_packaged_when_digest_unknown(tmp_path: Path) -> None:
    cache = _make_cache(tmp_path)

    result = prune_cache(cache, keep_versions=["1.0.3"], keep_packaged_digest=None)

    assert (cache / "packaged" / "digest-stale").exists()
    assert "packaged/digest-stale" in result["kept"]


def test_prune_cache_handles_missing_cache_dir(tmp_path: Path) -> None:
    result = prune_cache(
        tmp_path / "nope", keep_versions=["1.0.3"], keep_packaged_digest=None
    )

    assert result == {"removed": [], "kept": []}


def test_run_prune_refuses_when_env_override_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDD_COMPILE_BIN", "/somewhere/sdd-compile")

    result = run_prune()

    assert "SDD_COMPILE_BIN" in result["skipped"]


def test_run_prune_refuses_when_cli_version_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SDD_COMPILE_BIN", raising=False)
    monkeypatch.setattr(
        "providence_cli.services.doctor_compiler._probe_cli_version",
        lambda: (None, "not installed"),
    )

    result = run_prune()

    assert "cannot determine" in result["skipped"]


def test_report_runs_dry_validate_when_compiled_dir_exists(tmp_path: Path) -> None:
    (tmp_path / ".providence" / "compiled").mkdir(parents=True)
    runner = _mock_runner(tmp_path)
    runner.validate_compilation_detailed.return_value = {
        "ok": False,
        "errors": ["file not found: x.msgpack"],
        "checks": [],
    }
    with patch(
        "providence_core.utils.compiler_runner.CompilerRunner", return_value=runner
    ):
        report = build_compiler_report(workspace_root=tmp_path)

    assert report["validate"]["ran"] is True
    assert report["validate"]["ok"] is False
    assert report["validate"]["errors"] == ["file not found: x.msgpack"]


def test_report_lists_existing_cache_entries(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    (cache / "1.0.3").mkdir(parents=True)
    (cache / "1.0.3" / "sdd-compile-linux-amd64").write_bytes(b"x")
    (cache / "packaged" / "digest").mkdir(parents=True)
    (cache / "packaged" / "digest" / "sdd-compile-linux-amd64").write_bytes(b"y")

    with (
        patch("providence_core.utils.compiler_runner._cache_dir", return_value=cache),
        patch(
            "providence_core.utils.compiler_runner.CompilerRunner",
            return_value=_mock_runner(tmp_path),
        ),
    ):
        report = build_compiler_report(workspace_root=tmp_path)

    assert report["cache"] == {
        "dir": str(cache),
        "entries": [
            "1.0.3/sdd-compile-linux-amd64",
            "packaged/digest/sdd-compile-linux-amd64",
        ],
    }


def test_report_captures_cli_version_error(tmp_path: Path) -> None:
    with (
        patch(
            "providence_cli.services.doctor_compiler._probe_cli_version",
            return_value=(None, "package metadata missing"),
        ),
        patch(
            "providence_core.utils.compiler_runner.CompilerRunner",
            return_value=_mock_runner(tmp_path),
        ),
    ):
        report = build_compiler_report(workspace_root=tmp_path)

    assert report["cli_version"] is None
    assert report["cli_version_error"] == "package metadata missing"


def test_report_captures_binary_version_error(tmp_path: Path) -> None:
    runner = _mock_runner(tmp_path)
    runner.version.side_effect = RuntimeError("version failed")

    with patch(
        "providence_core.utils.compiler_runner.CompilerRunner", return_value=runner
    ):
        report = build_compiler_report(workspace_root=tmp_path)

    assert report["binary"]["version_error"] == "version failed"


def test_report_captures_validate_error(tmp_path: Path) -> None:
    (tmp_path / ".providence" / "compiled").mkdir(parents=True)
    runner = _mock_runner(tmp_path)
    runner.validate_compilation_detailed.side_effect = RuntimeError("bad compiled")

    with patch(
        "providence_core.utils.compiler_runner.CompilerRunner", return_value=runner
    ):
        report = build_compiler_report(workspace_root=tmp_path)

    assert report["validate"]["ran"] is True
    assert report["validate"]["error"] == "bad compiled"


def test_packaged_native_probe_reports_assets(tmp_path: Path) -> None:
    native = tmp_path / "_native"
    native.mkdir()
    (native / "sdd-compile-linux-amd64").write_bytes(b"x")
    (native / "README.txt").write_text("doc", encoding="utf-8")

    with patch(
        "providence_cli.services.doctor_compiler.resources.files", return_value=tmp_path
    ):
        report = doctor_compiler._probe_packaged_native()

    assert report == {
        "present": True,
        "assets": ["README.txt", "sdd-compile-linux-amd64"],
    }


def test_packaged_native_probe_reports_resource_errors() -> None:
    with patch(
        "providence_cli.services.doctor_compiler.resources.files",
        side_effect=RuntimeError("resource failure"),
    ):
        report = doctor_compiler._probe_packaged_native()

    assert report == {
        "present": False,
        "assets": [],
        "error": "resource failure",
    }


def test_current_packaged_digest_hashes_platform_asset(tmp_path: Path) -> None:
    native = tmp_path / "_native"
    native.mkdir()
    asset = native / "sdd-compile-linux-amd64"
    asset.write_bytes(b"native-binary")

    with (
        patch(
            "providence_core.utils.compiler_runner._asset_platform",
            return_value=("linux", "amd64", ""),
        ),
        patch(
            "providence_cli.services.doctor_compiler.resources.files",
            return_value=tmp_path,
        ),
    ):
        digest = _current_packaged_digest()

    assert digest == hashlib.sha256(b"native-binary").hexdigest()


def test_current_packaged_digest_returns_none_when_asset_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / "_native").mkdir()

    with (
        patch(
            "providence_core.utils.compiler_runner._asset_platform",
            return_value=("linux", "amd64", ""),
        ),
        patch(
            "providence_cli.services.doctor_compiler.resources.files",
            return_value=tmp_path,
        ),
    ):
        assert _current_packaged_digest() is None


def test_prune_cache_keeps_regular_files(tmp_path: Path) -> None:
    cache = _make_cache(tmp_path)
    (cache / "README.txt").write_text("manual entry", encoding="utf-8")

    result = prune_cache(
        cache,
        keep_versions=["1.0.3"],
        keep_packaged_digest="digest-current",
    )

    assert "README.txt" in result["kept"]
    assert (cache / "README.txt").exists()


def test_run_prune_uses_resolved_keep_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_COMPILE_BIN", raising=False)
    cache_dir = Path("/tmp/providence-cache")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "providence_cli.services.doctor_compiler._probe_cli_version",
        lambda: ("1.0.3", None),
    )
    monkeypatch.setattr(
        "providence_core.utils.compiler_runner._cache_dir",
        lambda: cache_dir,
    )
    monkeypatch.setattr(
        "providence_core.utils.compiler_runner._release_version_candidates",
        lambda version: [version, f"{version}.dev1+gabc"],
    )
    monkeypatch.setattr(
        "providence_cli.services.doctor_compiler._current_packaged_digest",
        lambda: "digest-current",
    )

    def fake_prune_cache(
        cache_dir_arg: Path,
        *,
        keep_versions: list[str],
        keep_packaged_digest: str | None,
    ) -> dict[str, object]:
        captured["cache_dir"] = cache_dir_arg
        captured["keep_versions"] = keep_versions
        captured["keep_packaged_digest"] = keep_packaged_digest
        return {"removed": ["old"], "kept": ["1.0.3"]}

    monkeypatch.setattr(
        "providence_cli.services.doctor_compiler.prune_cache",
        fake_prune_cache,
    )

    result = run_prune()

    assert result == {"removed": ["old"], "kept": ["1.0.3"]}
    assert captured == {
        "cache_dir": cache_dir,
        "keep_versions": ["1.0.3", "1.0.3.dev1+gabc"],
        "keep_packaged_digest": "digest-current",
    }
