from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from providence_cli.main import app

runner = CliRunner()


def _last_json(output: str) -> dict:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _payload_data(payload: dict) -> dict:
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_governance_reconcile_registries_json_success(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()

        _write(
            root / ".providence" / "commands" / "sdd-zeta" / "command.yaml",
            """id: \"sdd-zeta\"\nslash: \"/sdd-zeta\"\nroutes_to:\n  type: skill\n  id: sdd-zeta\nadapter_targets:\n  - codex\n""",
        )
        _write(
            root / ".providence" / "commands" / "sdd-alpha" / "command.yaml",
            """id: \"sdd-alpha\"\nslash: \"/sdd-alpha\"\nroutes_to:\n  type: cli\n  command: \"providence ask\"\ntargets:\n  - codex\n""",
        )
        _write(
            root / ".providence" / "skills" / "sdd-zeta" / "skill.yaml",
            """name: sdd-zeta\nversion: 1.0.0\ncategory: governance\ndescription: test\nstatus: active\nrisk_score: low\n""",
        )

        # Existing stale registries to prove added/removed counters.
        _write(
            root / ".providence" / "commands" / "registry.json",
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "commands": [
                        {
                            "id": "stale-cmd",
                            "slash": "/stale-cmd",
                            "routes_to": {"type": "skill", "id": "stale-cmd"},
                            "targets": ["codex"],
                        }
                    ],
                }
            ),
        )
        _write(
            root / ".providence" / "skills" / "registry.json",
            json.dumps(
                {
                    "schema_version": "1.1.0",
                    "skills": [
                        {
                            "name": "stale-skill",
                            "version": "1.0.0",
                            "category": "governance",
                            "description": "stale",
                            "risk_score": "low",
                            "status": "active",
                            "skill_yaml": ".providence/skills/stale-skill/skill.yaml",
                        }
                    ],
                }
            ),
        )

        result = runner.invoke(
            app,
            ["--json", "governance", "reconcile-registries"],
            env={"SDD_WORKSPACE_ROOT": str(root)},
        )
        assert result.exit_code == 0, result.output
        payload = _last_json(result.output)
        data = _payload_data(payload)
        assert payload["ok"] is True
        assert data["summary"]["commands"]["added"] == 2
        assert data["summary"]["commands"]["removed"] == 1
        assert data["summary"]["skills"]["added"] == 1
        assert data["summary"]["skills"]["removed"] == 1

        commands_registry = json.loads(
            (root / ".providence" / "commands" / "registry.json").read_text(
                encoding="utf-8"
            )
        )
        ids = [entry["id"] for entry in commands_registry["commands"]]
        assert ids == ["sdd-alpha", "sdd-zeta"]


def test_governance_reconcile_registries_duplicate_command_id_fails(
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()

        _write(
            root / ".providence" / "commands" / "cmd-1" / "command.yaml",
            """id: \"dup\"\nslash: \"/dup-a\"\nroutes_to:\n  type: skill\n  id: dup\nadapter_targets:\n  - codex\n""",
        )
        _write(
            root / ".providence" / "commands" / "cmd-2" / "command.yaml",
            """id: \"dup\"\nslash: \"/dup-b\"\nroutes_to:\n  type: skill\n  id: dup\nadapter_targets:\n  - codex\n""",
        )
        _write(
            root / ".providence" / "skills" / "sdd-one" / "skill.yaml",
            """name: sdd-one\nversion: 1.0.0\ncategory: governance\ndescription: test\nstatus: active\nrisk_score: low\n""",
        )

        result = runner.invoke(
            app,
            ["--json", "governance", "reconcile-registries"],
            env={"SDD_WORKSPACE_ROOT": str(root)},
        )
        assert result.exit_code == 1
        payload = _last_json(result.output)
        assert payload["ok"] is False
        assert "duplicate command id" in payload["error"]["message"]


def test_governance_reconcile_registries_check_mode_fails_on_drift(
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        _write(
            root / ".providence" / "commands" / "sdd-one" / "command.yaml",
            """id: "sdd-one"\nslash: "/sdd-one"\nroutes_to:\n  type: skill\n  id: sdd-one\nadapter_targets:\n  - codex\n""",
        )
        _write(
            root / ".providence" / "skills" / "sdd-one" / "skill.yaml",
            """name: sdd-one\nversion: 1.0.0\ncategory: governance\ndescription: test\nstatus: active\nrisk_score: low\n""",
        )
        _write(
            root / ".providence" / "commands" / "registry.json",
            json.dumps({"schema_version": "1.0.0", "commands": []}),
        )
        _write(
            root / ".providence" / "skills" / "registry.json",
            json.dumps({"schema_version": "1.1.0", "skills": []}),
        )

        result = runner.invoke(
            app,
            ["--json", "governance", "reconcile-registries", "--check"],
            env={"SDD_WORKSPACE_ROOT": str(root)},
        )
        assert result.exit_code == 1
        payload = _last_json(result.output)
        data = _payload_data(payload)
        assert payload["ok"] is False
        assert data["summary"]["drift_detected"] is True


def test_governance_reconcile_registries_check_mode_passes_when_in_sync(
    tmp_path: Path,
) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        _write(
            root / ".providence" / "commands" / "sdd-one" / "command.yaml",
            """id: "sdd-one"\nslash: "/sdd-one"\nroutes_to:\n  type: skill\n  id: sdd-one\nadapter_targets:\n  - codex\n""",
        )
        _write(
            root / ".providence" / "skills" / "sdd-one" / "skill.yaml",
            """name: sdd-one\nversion: 1.0.0\ncategory: governance\ndescription: test\nstatus: active\nrisk_score: low\n""",
        )

        # First apply to sync.
        applied = runner.invoke(
            app,
            ["governance", "reconcile-registries"],
            env={"SDD_WORKSPACE_ROOT": str(root)},
        )
        assert applied.exit_code == 0, applied.output

        result = runner.invoke(
            app,
            ["--json", "governance", "reconcile-registries", "--check"],
            env={"SDD_WORKSPACE_ROOT": str(root)},
        )
        assert result.exit_code == 0, result.output
        payload = _last_json(result.output)
        data = _payload_data(payload)
        assert payload["ok"] is True
        assert data["summary"]["drift_detected"] is False
