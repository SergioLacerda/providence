from __future__ import annotations

import json
from pathlib import Path

import pytest
from providence_runtime._skill_registry import SkillRegistry
from providence_runtime.skills import _REGISTRY

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(tmp_path: Path) -> SkillRegistry:
    return SkillRegistry(_REGISTRY, tmp_path)


def _write_skill_yaml(skills_dir: Path, name: str, content: str) -> None:
    (skills_dir / name).mkdir(parents=True, exist_ok=True)
    (skills_dir / name / "skill.yaml").write_text(content, encoding="utf-8")


_MINIMAL_YAML = """name: sdd-diagnose
version: "1.0.0"
category: analysis
description: Canonical diagnose
when_to_use:
  - failing checks
outcomes:
  - policy_result
allowed_tools:
  - providence doctor run
cli_fallback:
  - providence doctor run
required_permissions:
  - workspace-read
"""


# ---------------------------------------------------------------------------
# Disk loading
# ---------------------------------------------------------------------------


def test_falls_back_to_hardcoded_when_no_sdd_dir(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    assert registry._registry_source == "hardcoded"
    assert registry.get_skill("sdd-diagnose") is not None


def test_loads_canonical_skill_from_disk(tmp_path: Path) -> None:
    try:
        import yaml  # noqa: F401
    except ImportError:
        pytest.skip("PyYAML required")

    skills_dir = tmp_path / ".providence" / "skills"
    _write_skill_yaml(skills_dir, "sdd-diagnose", _MINIMAL_YAML)
    (skills_dir / "registry.json").write_text(
        json.dumps({"skills": [{"name": "sdd-diagnose"}]}), encoding="utf-8"
    )
    registry = SkillRegistry(_REGISTRY, tmp_path)
    assert registry._registry_source == "file"
    assert registry.get_skill("sdd-diagnose") is not None


def test_ignores_non_canonical_names_on_disk(tmp_path: Path) -> None:
    try:
        import yaml  # noqa: F401
    except ImportError:
        pytest.skip("PyYAML required")

    skills_dir = tmp_path / ".providence" / "skills"
    _write_skill_yaml(skills_dir, "diagnose", _MINIMAL_YAML)
    _write_skill_yaml(skills_dir, "sdd-diagnose", _MINIMAL_YAML)
    (skills_dir / "registry.json").write_text(
        json.dumps({"skills": [{"name": "diagnose"}, {"name": "sdd-diagnose"}]}),
        encoding="utf-8",
    )
    registry = SkillRegistry(_REGISTRY, tmp_path)
    names = {s.name for s in registry.list_skills()}
    assert "sdd-diagnose" in names
    assert "diagnose" not in names


def test_skips_malformed_yaml_gracefully(tmp_path: Path) -> None:
    try:
        import yaml  # noqa: F401
    except ImportError:
        pytest.skip("PyYAML required")

    skills_dir = tmp_path / ".providence" / "skills"
    (skills_dir / "sdd-diagnose").mkdir(parents=True)
    (skills_dir / "sdd-diagnose" / "skill.yaml").write_text(
        ": bad: yaml: [[[", encoding="utf-8"
    )
    (skills_dir / "registry.json").write_text(
        json.dumps({"skills": [{"name": "sdd-diagnose"}]}), encoding="utf-8"
    )
    registry = SkillRegistry(_REGISTRY, tmp_path)
    assert registry.get_skill("sdd-diagnose") is not None


# ---------------------------------------------------------------------------
# list_skills
# ---------------------------------------------------------------------------


def test_list_skills_returns_sorted_canonical_names(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    names = [s.name for s in registry.list_skills()]
    assert names == sorted(names)
    assert all(n.startswith("sdd-") for n in names)


def test_list_skills_deduplicates(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    names = [s.name for s in registry.list_skills()]
    assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# get_skill
# ---------------------------------------------------------------------------


def test_get_skill_by_canonical_name(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    assert registry.get_skill("sdd-diagnose") is not None


def test_get_skill_by_short_alias(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    skill = registry.get_skill("diagnose")
    assert skill is not None
    assert skill.name == "sdd-diagnose"


def test_get_skill_returns_none_for_unknown(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    assert registry.get_skill("does-not-exist") is None


def test_get_skill_reflects_live_fallback_mutations(tmp_path: Path) -> None:
    from providence_runtime.skills import _REGISTRY as live_registry

    registry = SkillRegistry(live_registry, tmp_path)
    original = live_registry["sdd-diagnose"]
    try:
        from providence_runtime._skill_contracts import SkillDefinition

        modified = SkillDefinition(
            name=original.name,
            version="9.9.9",
            category=original.category,
            description="mutated",
            when_to_use=list(original.when_to_use),
            outcomes=list(original.outcomes),
            allowed_tools=list(original.allowed_tools),
            cli_fallback=list(original.cli_fallback),
            required_permissions=list(original.required_permissions),
        )
        live_registry["sdd-diagnose"] = modified
        assert registry.get_skill("sdd-diagnose").version == "9.9.9"  # type: ignore[union-attr]
    finally:
        live_registry["sdd-diagnose"] = original


def test_sdd_ask_registry_remains_query_only_without_runtime_delegation(
    tmp_path: Path,
) -> None:
    """Runtime registry metadata must not imply executed provider delegation."""

    registry = _make_registry(tmp_path)
    skill = registry.get_skill("sdd-ask")

    assert skill is not None
    assert skill.delegation_policy is not None
    assert skill.delegation_policy["enabled"] is False
    assert skill.delegation_policy["runtime_status"] == "not_implemented"
    assert skill.delegation_policy["current_contract"] == "query_only"
    assert "declarative_only" in skill.delegation_policy["metadata_status"]
    assert "delegation_executed=false" in skill.delegation_policy["metadata_status"]
    assert "provider_bound=false" in skill.delegation_policy["metadata_status"]


# ---------------------------------------------------------------------------
# export_skills_payload
# ---------------------------------------------------------------------------


def test_export_json_format(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    payload = registry.export_skills_payload("json")
    assert payload["schema_version"] == "1.1.0"
    assert isinstance(payload["skills"], list)
    names = {s["name"] for s in payload["skills"]}
    assert "sdd-diagnose" in names
    assert "diagnose" not in names


def test_export_openai_format(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    payload = registry.export_skills_payload("openai")
    assert payload["format"] == "openai"
    assert all(t["type"] == "function" for t in payload["tools"])


def test_export_langchain_format(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    payload = registry.export_skills_payload("langchain")
    assert payload["format"] == "langchain"
    assert all("args" in t for t in payload["tools"])


def test_export_crewai_format(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    payload = registry.export_skills_payload("crewai")
    assert payload["format"] == "crewai"


def test_export_autogen_format(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    payload = registry.export_skills_payload("autogen")
    assert payload["format"] == "autogen"
    assert "functions" in payload


def test_export_unknown_format_fallback(tmp_path: Path) -> None:
    registry = _make_registry(tmp_path)
    payload = registry.export_skills_payload("custom-format")
    assert payload["format"] == "custom-format"
    assert "note" in payload
