from __future__ import annotations

from providence_wizard.orchestration.language_policy import (
    evaluate_language_surface,
    resolve_language_policy,
)


def _config_with_context() -> dict[str, object]:
    return {
        "language_context": {
            "preferred_chat_language": "Portugus (Brasil)",
            "preferred_ui_language": "Portugus (Brasil)",
            "preferred_local_docs_language": "Portugus (Brasil)",
        }
    }


def test_resolve_language_policy_includes_analysis_docs() -> None:
    policy = resolve_language_policy({})
    assert "analysis_docs" in policy["contextual_surfaces"]
    assert policy["mandate_anchor"] == "M011"


def test_evaluate_language_surface_fails_for_mandatory_non_english() -> None:
    result = evaluate_language_surface(
        surface="technical_docs",
        artifact_language="Portugus (Brasil)",
        config=_config_with_context(),
    )
    assert result["severity"] == "fail"


def test_evaluate_language_surface_warns_on_context_divergence() -> None:
    result = evaluate_language_surface(
        surface="chat",
        artifact_language="English",
        config=_config_with_context(),
    )
    assert result["severity"] == "warn"


def test_evaluate_language_surface_passes_on_context_match() -> None:
    result = evaluate_language_surface(
        surface="ui",
        artifact_language="Portugus (Brasil)",
        config=_config_with_context(),
    )
    assert result["severity"] == "pass"


def test_evaluate_language_surface_info_when_context_missing() -> None:
    result = evaluate_language_surface(
        surface="workspace_local_docs",
        artifact_language="Portugus (Brasil)",
        config={"language_context": {}},
    )
    assert result["severity"] == "info"
