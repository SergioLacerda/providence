"""Integration tests for providence skills full-bootstrap / --regenerate-seeds CLI commands."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()

# Same workspace src dirs as [tool.pytest.ini_options].pythonpath in
# pyproject.toml. pytest's own `pythonpath` setting only affects sys.path of
# THIS process  a subprocess spawned via subprocess.run does not inherit
# it, so `python -m providence_cli ...` below would fail to import providence_cli in any
# venv without a full `uv sync --all-packages` editable install unless we
# forward it explicitly via PYTHONPATH.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_WORKSPACE_PYTHONPATH = os.pathsep.join(
    str(_REPO_ROOT / rel)
    for rel in (
        "packages/core/providence_core/src",
        "packages/core/providence_runtime/src",
        "packages/core/providence_telemetry/src",
        "packages/features/providence_integration/src",
        "packages/features/providence_adapters/src",
        "packages/features/providence_skills/src",
        "packages/features/providence_pages/src",
        "packages/interfaces/providence_wizard/src",
        "packages/interfaces/providence_cli/src",
    )
)


def _load_json_output(raw: str) -> dict:
    # Some environments emit a governance soft preface line before JSON output.
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _payload_data(payload: dict) -> dict:
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def test_skills_full_bootstrap_json_missing_governance_uses_canonical_error(
    tmp_path,
) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "providence_cli.commands.skills.resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.services.skills_bootstrap_validation.validate_governance_path",
            return_value=False,
        ),
    ):
        result = runner.invoke(app, ["--json", "skills", "--full-bootstrap"])

    assert result.exit_code == 1, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "error"
    assert payload["command"] == "skills full-bootstrap"
    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "missing_governance_artifacts"


def test_skills_regenerate_seeds_invokes_full_bootstrap_mode() -> None:
    with patch("providence_cli.commands.skills._run_full_bootstrap") as bootstrap:
        result = runner.invoke(app, ["skills", "--regenerate-seeds"])
    assert result.exit_code == 0, result.output
    bootstrap.assert_called_once_with(regenerate_seeds=True, dry_run=False)


def test_skills_regenerate_seeds_dry_run_invokes_full_bootstrap_mode() -> None:
    with patch("providence_cli.commands.skills._run_full_bootstrap") as bootstrap:
        result = runner.invoke(app, ["skills", "--regenerate-seeds", "--dry-run"])
    assert result.exit_code == 0, result.output
    bootstrap.assert_called_once_with(regenerate_seeds=True, dry_run=True)


def test_skills_dry_run_requires_regenerate_seeds() -> None:
    result = runner.invoke(app, ["skills", "--dry-run"])
    assert result.exit_code == 2, result.output
    assert "--dry-run requires --regenerate-seeds" in result.output


def test_skills_dry_run_module_entrypoint_preserves_exit_code() -> None:
    env = {**os.environ, "PYTHONPATH": _WORKSPACE_PYTHONPATH}
    result = subprocess.run(
        [sys.executable, "-m", "providence_cli", "skills", "--dry-run"],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2, result.stderr
    assert "--dry-run requires --regenerate-seeds" in result.stderr


def test_skills_full_bootstrap_json_uses_canonical_envelope(tmp_path) -> None:
    class _Summary:
        commands = {"added": 0, "removed": 0, "unchanged": 1}
        skills = {"added": 0, "removed": 0, "unchanged": 1}

        def as_json(self):
            return {
                "commands": self.commands,
                "skills": self.skills,
                "drift_detected": False,
            }

    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "providence_cli.commands.skills.resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "providence_cli.services.skills_bootstrap_validation.validate_governance_path",
            return_value=True,
        ),
        patch(
            "providence_cli.services.skills_bootstrap_validation.load_governance_config",
            return_value={"items": [{"id": "M001"}]},
        ),
        patch(
            "providence_cli.services.skills_bootstrap.generate_agent_seeds",
            return_value=[("copilot", tmp_path / "seed.md", "ok")],
        ),
        patch(
            "providence_cli.services.skills_bootstrap.generate_agent_instruction_files",
            return_value=[],
        ),
        patch(
            "providence_cli.services.skills_bootstrap.generate_agent_prompt_commands",
            return_value=[],
        ),
        patch(
            "providence_cli.services.skills_bootstrap.generate_skills_registry",
            return_value={"skill_count": 1},
        ),
        patch(
            "providence_cli.services.skills_bootstrap.generate_commands_registry",
            return_value={"command_count": 1},
        ),
        patch(
            "providence_cli.services.skills_bootstrap.reconcile_registries",
            return_value=_Summary(),
        ),
        patch(
            "providence_cli.services.skills_bootstrap.generate_skill_index",
            return_value={"skill_count": 1},
        ),
        patch(
            "providence_cli.services.skills_bootstrap.generate_cli_commands_index",
            return_value={"command_count": 1},
        ),
        patch(
            "providence_cli.services.skills_bootstrap._generate_adapters",
            return_value=(2, None),
        ),
    ):
        result = runner.invoke(app, ["--json", "skills", "--full-bootstrap"])

    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "skills full-bootstrap"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "skills_full_bootstrap_completed"
