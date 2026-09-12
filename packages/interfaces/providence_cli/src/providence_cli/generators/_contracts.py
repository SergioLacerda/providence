"""Contracts generator  creates .providence/contracts/ with the three plugin interface schemas."""

from pathlib import Path
from typing import Any

_ANALYSIS_PROVIDER_SCHEMA = """\
# analysis-provider.schema.yaml
# Contract schema for SDD analysis provider plugin declarations.
schema_version: "1.0.0"

required_fields:
  - id
  - type
  - version
  - status
  - entrypoint
  - contract
  - sdd_injection

known_types:
  - analysis_orchestrator
  - analysis_provider
  - execution_provider

sdd_injection:
  required:
    - base_path
    - execution_provider
    - approval_gate
  optional:
    - knowledge_paths    # array of SDD-compiled knowledge paths; may be empty
    - governance_context # workspace_version + active_mandates metadata

compliance:
  m017: enforced
  artifact_scope: sdd_injection.base_path only
  execution_provider: sdd_injection.execution_provider only
  approval_gate: required when sdd_injection.approval_gate == "required"
"""

_MISSION_CONTRACT_SCHEMA = """\
# mission-contract.schema.yaml
# Contract schema for what SDD passes to a plugin at mission invocation.
schema_version: "1.0.0"

required_fields:
  - mission_id        # format: mission-{YYYY-MM-DD}-{sequence}
  - prompt            # original user request string
  - constraints       # delivery_strategy, legacy_compatibility, execution_intent
  - sdd_injection     # authoritative SDD configuration  plugin MUST NOT override
  - artifacts         # dict of expected output artifact paths

mission_id_format: "mission-{YYYY-MM-DD}-{sequence}"

sdd_injection:
  required:
    - base_path           # plugin writes artifacts only under this path
    - execution_provider  # plugin uses this skill for execution slot
    - approval_gate       # "required"  plugin must not skip gate
    - knowledge_paths     # array (may be empty); plugin appends to its pool
    - governance_context  # workspace_version and active_mandates

constraints:
  optional_fields:
    - delivery_strategy
    - legacy_compatibility
    - execution_intent

artifacts:
  description: "Expected output paths keyed by phase (discovery, refined_plan, execution_report)"
"""

_MISSION_RESULT_SCHEMA = """\
# mission-result.schema.yaml
# Contract schema for what a plugin returns to SDD after a mission.
schema_version: "1.0.0"

required_fields:
  - mission_id  # must match the contract mission_id
  - status      # completed | plan_only | blocked
  - artifacts   # dict of phase -> path; at least one path required on success

optional_fields:
  - progress    # phase checklist: {phase: done|pending|blocked}
  - blockers    # required when status == "blocked"

status_values:
  completed: mission ran to completion, Sniper executed
  plan_only: mission stopped at gate (gate declined or tasks empty)
  blocked: mission could not proceed; blockers array required

blockers:
  required_when: "status == blocked"
  required_fields_per_blocker:
    - phase   # which phase was blocked
    - reason  # human-readable reason
    - action  # suggested corrective action

m017_validation:
  artifact_paths_must_be_under: sdd_injection.base_path
  violation_action: emit_governance_event + reject_result
"""


def generate_contracts(output_dir: str, _config: dict[str, Any]) -> dict[str, Any]:
    """Generate .providence/contracts/ with the three plugin interface schema files.

    Args:
        output_dir: Base output directory (workspace root)
        _config: Governance configuration dict (reserved for future use)

    Returns:
        Dict with contracts_dir and files_written.
    """
    output_path = Path(output_dir)
    contracts_dir = output_path / ".providence" / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "analysis-provider.schema.yaml": _ANALYSIS_PROVIDER_SCHEMA,
        "mission-contract.schema.yaml": _MISSION_CONTRACT_SCHEMA,
        "mission-result.schema.yaml": _MISSION_RESULT_SCHEMA,
    }

    written: list[str] = []
    for filename, content in files.items():
        path = contracts_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(str(path))

    return {
        "contracts_dir": str(contracts_dir),
        "files_written": len(written),
        "files": written,
    }
