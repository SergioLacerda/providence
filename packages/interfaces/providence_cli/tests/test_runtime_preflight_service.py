from __future__ import annotations

from unittest.mock import MagicMock, patch

from providence_cli.services.runtime_preflight import (
    PreflightResult,
    run_runtime_preflight,
)


def test_preflight_skips_non_compiled_path(tmp_path) -> None:
    result = run_runtime_preflight(str(tmp_path))
    assert result.passed is True
    assert result.details.get("skipped") is True


def test_preflight_result_dataclass_defaults() -> None:
    r = PreflightResult(passed=True)
    assert r.reason == ""
    assert r.details == {}


def test_preflight_runs_full_validation_when_core_json_present(tmp_path) -> None:
    core_json = tmp_path / "governance-core.json"
    core_json.write_text("{}", encoding="utf-8")

    fake_artifact = MagicMock(
        fingerprint="fp-test",
        schema_version="3.0",
        profile="client",
    )
    fake_policy_result = MagicMock(allowed=True, reason="preflight ok")
    fake_engine = MagicMock()
    fake_engine.validate_preflight.return_value = fake_policy_result

    import providence_runtime as _providence_runtime

    with (
        patch.object(
            _providence_runtime.CompiledArtifact,
            "from_sdd_compiled_dir",
            return_value=fake_artifact,
        ),
        patch("providence_runtime.PolicyEngine", return_value=fake_engine),
    ):
        result = run_runtime_preflight(str(tmp_path))

    assert result.passed is True
    assert result.details.get("artifact_fingerprint") == "fp-test"
    assert result.details.get("schema_version") == "3.0"


def test_preflight_returns_permissive_pass_on_exception(tmp_path) -> None:
    core_json = tmp_path / "governance-core.json"
    core_json.write_text("{}", encoding="utf-8")

    import providence_runtime as _providence_runtime

    with patch.object(
        _providence_runtime.CompiledArtifact,
        "from_sdd_compiled_dir",
        side_effect=RuntimeError("artifact load failed"),
    ):
        result = run_runtime_preflight(str(tmp_path))

    assert result.passed is True
    assert result.details.get("skipped") is True
    assert "artifact load failed" in result.details.get("error", "")
