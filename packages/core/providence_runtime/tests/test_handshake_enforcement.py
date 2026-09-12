import json
from pathlib import Path

from providence_runtime.skills import SkillEngine

from providence_core.governance.handshake import AgentHandshakeProtocol


def test_skill_enforcement_blocks_unauthorized_skill(tmp_path: Path):
    # Setup temporary project root
    project_root = tmp_path
    ai_dir = project_root / ".providence" / "runtime"
    ai_dir.mkdir(parents=True)

    # Create a handshake response that DOES NOT include 'sdd-diagnose'
    handshake_file = ai_dir / "handshake-response.json"
    response_data = {
        "agent_id": "test-agent",
        "understood_mandates": ["M001"],
        "skills_to_use": ["sdd-review-architecture"],  # 'sdd-diagnose' is missing
        "plan": {},
        "compliance_declaration": "test",
        "acknowledged_signature": True,
    }
    handshake_file.write_text(json.dumps(response_data), encoding="utf-8")

    engine = SkillEngine()

    # Execution should be blocked
    result = engine.run_skill("sdd-diagnose", project_root=project_root)

    assert result.policy_result == "unauthorized"
    assert "was not declared in the initial handshake" in result.reason
    assert result.exit_code == 1


def test_skill_enforcement_allows_authorized_skill(tmp_path: Path):
    # Setup temporary project root
    project_root = tmp_path
    ai_dir = project_root / ".providence" / "runtime"
    ai_dir.mkdir(parents=True)

    # Create a handshake response that DOES include 'sdd-diagnose'
    handshake_file = ai_dir / "handshake-response.json"
    response_data = {
        "agent_id": "test-agent",
        "understood_mandates": ["M001"],
        "skills_to_use": ["sdd-diagnose"],
        "plan": {},
        "compliance_declaration": "test",
        "acknowledged_signature": True,
    }
    handshake_file.write_text(json.dumps(response_data), encoding="utf-8")

    engine = SkillEngine()

    # Execution should be allowed (policy_result will be 'executed' or 'fallback_cli' if tool missing)
    result = engine.run_skill("sdd-diagnose", project_root=project_root)

    assert result.policy_result != "unauthorized"


def test_handshake_challenge_generation(tmp_path: Path):
    # project_root must be explicit: AgentHandshakeProtocol() with no
    # argument resolves to the real repository root (via cwd), which
    # would persist a fresh challenge to the live .providence/runtime/
    # and invalidate any active session handshake (M015 runtime drift).
    ahp = AgentHandshakeProtocol(project_root=tmp_path)
    challenge = ahp.generate_challenge(task_description="Unit Test")

    assert challenge.session_id is not None
    assert isinstance(challenge.active_mandates, list)
    assert all(
        isinstance(mandate_id, str) and mandate_id.startswith("M")
        for mandate_id in challenge.active_mandates
    )
    assert isinstance(challenge.available_skills, list)
    assert challenge.task.get("description") == "Unit Test"

    # Signature status is environment-dependent: "unavailable" (signature
    # mode off), "unsigned" (no artifact/.sig), "verified", or a
    # validate_artifact_signature() failure code (e.g. "SIG_INVALID").
    status = challenge.signature_status
    assert status in {"unavailable", "unsigned", "verified"} or status.startswith(
        "SIG_"
    )
