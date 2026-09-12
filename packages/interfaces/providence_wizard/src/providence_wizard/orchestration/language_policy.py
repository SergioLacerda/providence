"""Shared language governance policy helpers."""

from __future__ import annotations

from typing import Any


def default_language_policy() -> dict[str, Any]:
    """Return the canonical default language policy."""
    return {
        "mandatory_surfaces": [
            "code",
            "technical_docs",
            "governance",
            "cli_help",
        ],
        "contextual_surfaces": [
            "chat",
            "ui",
            "workspace_local_docs",
            "analysis_docs",
        ],
        "workspace_local_docs_paths": [".analysis/"],
        "mandate_anchor": "M011",
        "guideline_anchors": ["G021", "G022"],
    }


def resolve_language_policy(config: dict[str, Any]) -> dict[str, Any]:
    """Merge optional config overrides onto the canonical policy."""
    policy = default_language_policy()
    raw_policy = config.get("language_policy", {})
    if not isinstance(raw_policy, dict):
        return policy
    for key, default in policy.items():
        value = raw_policy.get(key)
        if isinstance(default, list):
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                policy[key] = list(value)
            continue
        if isinstance(value, str) and value:
            policy[key] = value
    return policy


def evaluate_language_surface(
    *,
    surface: str,
    artifact_language: str,
    config: dict[str, Any],
) -> dict[str, str]:
    """Classify a language-policy evaluation as fail/warn/pass/info."""
    policy = resolve_language_policy(config)
    normalized_surface = surface.strip().lower()
    normalized_language = artifact_language.strip()

    if normalized_surface in policy["mandatory_surfaces"]:
        if normalized_language != "English":
            return {
                "severity": "fail",
                "reason": (
                    f"Mandatory surface '{surface}' must use English; "
                    f"got '{artifact_language}'."
                ),
            }
        return {
            "severity": "pass",
            "reason": f"Mandatory surface '{surface}' satisfies M011.",
        }

    preference_map = {
        "chat": "preferred_chat_language",
        "ui": "preferred_ui_language",
        "workspace_local_docs": "preferred_local_docs_language",
        "analysis_docs": "preferred_local_docs_language",
    }
    preference_key = preference_map.get(normalized_surface)
    language_context = config.get("language_context", {})
    if preference_key is None or not isinstance(language_context, dict):
        return {
            "severity": "info",
            "reason": f"No language preference rule is defined for surface '{surface}'.",
        }

    preferred_language = language_context.get(preference_key)
    if not isinstance(preferred_language, str) or not preferred_language:
        return {
            "severity": "info",
            "reason": f"Language context is missing for surface '{surface}'.",
        }
    if preferred_language != normalized_language:
        return {
            "severity": "warn",
            "reason": (
                f"Surface '{surface}' prefers '{preferred_language}' "
                f"but got '{artifact_language}'."
            ),
        }
    return {
        "severity": "pass",
        "reason": f"Surface '{surface}' matches preferred language '{preferred_language}'.",
    }
