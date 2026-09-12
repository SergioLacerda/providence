"""MandateSeeds  JSON seed generation for governance and compliance."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from providence_wizard.constants import RUNTIME_DIRNAME

if TYPE_CHECKING:
    from .base_generator import BaseSeedlingGenerator

TOKEN_BUDGET_MEDIUM = "medium"  # nosec B105


class MandateSeeds:
    """Generate governance.seed.json and compliance.seed.json."""

    def __init__(self, ctx: BaseSeedlingGenerator) -> None:
        self._ctx = ctx

    def _resolve_activation_profile(self) -> str:
        enforcement_mode = self._ctx.config.get("enforcement_mode", "warn_mode")
        return "critic" if enforcement_mode == "strict_mode" else "executor"

    def _resolve_skill_set(self) -> list[str]:
        base = [
            "sdd-diagnose",
            "sdd-correct",
            "sdd-converge",
            "sdd-validate-governance",
            "sdd-stabilize",
        ]
        if self._ctx.config.get("enforcement_mode", "warn_mode") == "strict_mode":
            base.append("sdd-review-architecture")
        return base

    def _resolve_escalation_mode(self) -> str:
        enforcement_mode = self._ctx.config.get("enforcement_mode", "warn_mode")
        return "block" if enforcement_mode == "strict_mode" else "warn"

    def _should_auto_activate(self) -> bool:
        adoption_level = str(self._ctx.config.get("adoption_level", "standard")).lower()
        return adoption_level != "lite"

    def generate_governance_seed(self) -> bool:
        """Generate governance.seed.json."""
        try:
            ctx = self._ctx
            seed_file = ctx.seedlings_dir / "governance.seed.json"
            seed_data = {
                "schema_version": "1.0.0",
                "auto_activate": self._should_auto_activate(),
                "load_compiled_from": RUNTIME_DIRNAME,
                "on_load": "activate_governance",
                "triggers": ["on_project_load"],
                "description": "Governance Activation Protocol (GAP) v1.0 - Auto-activates on project load",
                "required_context": [
                    f"{RUNTIME_DIRNAME}/metadata.json",
                    f"{RUNTIME_DIRNAME}/seedlings/agent-prep.seed.json",
                ],
                "project_metadata": {
                    "adoption_level": ctx.config.get("adoption_level", "standard"),
                    "language": ctx.config.get("language", "python"),
                    "language_context": ctx.config.get("language_context", {}),
                    "spec_fingerprint": ctx.spec_fingerprint,
                    "generated_at": ctx.generated_at,
                    "version": "1.0",
                    "mandates_selected": ctx.mandate_ids,
                    "guidelines_active": ctx.active_categories,
                },
                "awakening": {
                    "activation_profile": self._resolve_activation_profile(),
                    "skill_set": self._resolve_skill_set(),
                    "fallback_order": ["skills", "cli"],
                    "response_footer_policy": "always",
                    "budget_policy": {
                        "token_budget": TOKEN_BUDGET_MEDIUM,
                        "max_retries": 1,
                        "timeout_seconds": 120,
                    },
                    "escalation_policy": {
                        "mode": self._resolve_escalation_mode(),
                        "on_repeat_failure": "human_review",
                        "on_critical_violation": "block",
                    },
                    "validation_policy": {"preflight": True, "postcheck": True},
                    "telemetry_policy": {
                        "emit_runtime_event": True,
                        "emit_audit_event": True,
                        "otel_if_enabled": True,
                    },
                },
                "awakening_flow": [
                    "project_load",
                    "preflight",
                    "context_sync",
                    "skill_profile_resolve",
                    "policy_enforce",
                    "telemetry_emit",
                ],
            }
            with open(seed_file, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)
            ctx.log(
                f" Generated governance.seed.json (fingerprint: {ctx.spec_fingerprint})"
            )
            return True
        except Exception as e:
            self._ctx._emit(f"   Failed to generate governance.seed.json: {e}")
            return False

    def generate_compliance_seed(self) -> bool:
        """Generate compliance.seed.json."""
        try:
            ctx = self._ctx
            seed_file = ctx.seedlings_dir / "compliance.seed.json"
            enforcement_mode = ctx.config.get("enforcement_mode", "warn_mode")
            action_on_drift = {
                "silent_mode": "silent",
                "warn_mode": "warn",
                "strict_mode": "block",
            }.get(enforcement_mode, "warn")
            enforcement_level = {
                "silent_mode": "SILENT",
                "warn_mode": "WARN",
                "strict_mode": "STRICT",
            }.get(enforcement_mode, "WARN")
            seed_data: dict[str, Any] = {
                "auto_activate": True,
                "load_compiled_from": RUNTIME_DIRNAME,
                "on_load": "setup_compliance_pipeline",
                "triggers": ["on_ci_pipeline"],
                "description": "Compliance Validation - CI/CD policy and runtime checks",
                "required_context": [
                    f"{RUNTIME_DIRNAME}/metadata.json",
                    f"{RUNTIME_DIRNAME}/seedlings/governance.seed.json",
                ],
                "telemetry": {
                    "agent_observability": {
                        "enabled": True,
                        "track_agent_id": True,
                        "log_compliance_rate": True,
                    }
                },
                "compliance_rules": {
                    "signature_validation": {
                        "enabled": True,
                        "signature_mode": "warn",
                        "trusted_keyring": f"{RUNTIME_DIRNAME}/trust/trusted-keys.json",
                        "strict_in_ci": True,
                        "strict_requires_canonical_keyring": True,
                        "unsigned_policy": {
                            "dev": "allowed_warn",
                            "ci_release": "forbidden_block",
                        },
                        "legacy_trust_migration": {
                            "enabled": True,
                            "window_releases": 2,
                            "removal_timeline": "remove legacy keyring fallback after 2 releases",
                        },
                    },
                    "fingerprint_validation": {
                        "enabled": True,
                        "expected_fingerprint": ctx.spec_fingerprint,
                        "action_on_drift": action_on_drift,
                    },
                    "mandate_enforcement": {
                        "enabled": True,
                        "level": enforcement_level,
                    },
                    "guideline_checks": {
                        "enabled": True,
                        "categories": ctx.active_categories,
                    },
                },
                "hooks": {
                    "github_actions": {
                        "enabled": True,
                        "workflow": ".github/workflows/sdd-validation.yml",
                        "triggers": ["push", "pull_request"],
                    },
                },
                "generated_at": ctx.generated_at,
            }
            with open(seed_file, "w", encoding="utf-8") as f:
                json.dump(seed_data, f, indent=2)
            ctx.log(" Generated compliance.seed.json")
            return True
        except Exception as e:
            self._ctx._emit(f"   Failed to generate compliance.seed.json: {e}")
            return False
