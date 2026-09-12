"""DevinPluginGenerator: builds a self-contained SDD governance plugin bundle for Devin (Soft/Standalone profile)."""

from __future__ import annotations

import hashlib
import json
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..skill_loader import SkillLoader
from ._content_sources import (
    _coding_practices_digest,
    _governance_summary_digest,
    _load_coding_practices,
    _load_governance_summary,
)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "devin_plugin"
_STANDALONE_TEMPLATES_DIR = _TEMPLATES_DIR / "standalone"
_PLUGIN_VERSION = "0.1.0"
_SOFT_GOVERNANCE_RULESET_VERSION = "1.0.0"
_STANDALONE_RULESET_VERSION = "1.0.0"
_STANDALONE_LAST_VERIFIED = "2026-08-18"
_STANDALONE_RULE_NAMES = (
    "architecture",
    "git-safety",
    "testing",
    "generated-artifacts",
    "go",
    "documentation",
    "token-economy",
)


def _policy_digest(skills: list[dict[str, Any]]) -> str:
    """Deterministic sha256 over a canonical JSON serialization of skill data."""
    canonical = json.dumps(skills, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _compiler_version() -> str:
    try:
        from importlib.metadata import version

        return version("providence-adapters")
    except Exception:
        return "0.0.0+unknown"


@dataclass
class DevinStandaloneResult:
    """Result of standalone (zero-SDD-mention) Devin config generation."""

    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


@dataclass
class DevinPluginResult:
    """Result of Devin plugin bundle generation."""

    files_written: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True
    policy_digest: str = ""
    governance_summary_digest: str = ""
    coding_practices_digest: str = ""


class DevinPluginGenerator:
    """Generates a Soft/Standalone SDD governance plugin bundle for Devin."""

    def __init__(
        self,
        templates_dir: Path | None = None,
        standalone_templates_dir: Path | None = None,
    ):
        self.templates_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm")),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.standalone_templates_dir = (
            Path(standalone_templates_dir)
            if standalone_templates_dir
            else _STANDALONE_TEMPLATES_DIR
        )
        self.standalone_env = Environment(
            loader=FileSystemLoader(str(self.standalone_templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm")),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.skill_loader = SkillLoader()

    def generate(
        self,
        output_dir: Path,
        dest: Path | None = None,
        *,
        source_revision: str = "unknown",
        built_at: str | None = None,
        include_skills: bool = True,
    ) -> DevinPluginResult:
        """
        Generate the Devin plugin bundle.

        Args:
            output_dir: project root where .providence/ (and optionally LICENSE) live.
            dest: bundle output directory. Defaults to {output_dir}/dist/devin-plugin.
            source_revision: caller-supplied revision identifier (e.g. a git SHA
                obtained by the caller â€” this method never shells out to git).
            built_at: ISO-8601 timestamp. Defaults to current UTC time; pass a
                fixed value in tests for reproducible output.
            include_skills: when False, skip the Providence skill catalog entirely
                (no skills/ directory, no "skills" key in plugin.json). Each
                skill's "Allowed CLI" commands assume the providence CLI is installed
                in the Devin environment â€” a real dependency the base
                AGENTS.md/rules/ governance summary does not have. Default True
                preserves existing behavior.
        """
        result = DevinPluginResult()
        sdd_dir = Path(output_dir) / ".providence"
        skills_sorted: list[dict[str, Any]] = []

        if include_skills:
            skills = self.skill_loader.load_skills(sdd_dir)
            if not skills:
                result.success = False
                result.errors.append(
                    f"No skills found under {sdd_dir / 'skills' / 'registry.json'}"
                )
                return result
            skills_sorted = sorted(skills, key=lambda s: s.get("name", ""))

        digest = _policy_digest(skills_sorted)
        result.policy_digest = digest

        governance_summary = _load_governance_summary(output_dir)
        governance_summary_digest = _governance_summary_digest(governance_summary)
        result.governance_summary_digest = governance_summary_digest

        try:
            coding_practices = _load_coding_practices(output_dir)
        except ValueError as e:
            result.success = False
            result.errors.append(str(e))
            return result
        coding_practices_digest = (
            _coding_practices_digest(coding_practices) if coding_practices else ""
        )
        result.coding_practices_digest = coding_practices_digest

        context = {
            "plugin_version": _PLUGIN_VERSION,
            "compiler_version": _compiler_version(),
            "schema_version": "1.0.0",
            "source_revision": source_revision,
            "built_at": built_at or datetime.now(timezone.utc).isoformat(),
            "policy_digest": digest,
            "governance_summary_digest": governance_summary_digest,
            "governance_fingerprint": governance_summary["governance_fingerprint"],
            "workspace_version": governance_summary["workspace_version"],
            "mandate_count": governance_summary["mandate_count"],
            "mandate_described_count": governance_summary["mandate_described_count"],
            "mandates": governance_summary["mandates"],
            "guideline_categories": governance_summary["guideline_categories"],
            "guidelines": governance_summary["guidelines"],
            "include_skills": include_skills,
            "soft_governance_ruleset_version": _SOFT_GOVERNANCE_RULESET_VERSION,
            "has_coding_practices": coding_practices is not None,
            "anti_patterns": coding_practices["anti_patterns"]
            if coding_practices
            else [],
            "go_resolution_bypass": (
                coding_practices["go_resolution_bypass"] if coding_practices else None
            ),
            "coding_practices_digest": coding_practices_digest,
        }

        bundle_root = Path(dest) if dest else Path(output_dir) / "dist" / "devin-plugin"
        bundle_root.mkdir(parents=True, exist_ok=True)

        try:
            self._write(
                bundle_root / ".devin-plugin" / "plugin.json",
                "plugin.json",
                context,
                result,
            )
            self._write(bundle_root / "AGENTS.md", "AGENTS.md", context, result)
            self._write(
                bundle_root / "rules" / "providence-summary.md",
                "providence-summary.md",
                context,
                result,
            )
            self._write(
                bundle_root / "rules" / "sdd-soft-governance-behavior.md",
                "sdd-soft-governance-behavior.md",
                context,
                result,
            )
            if coding_practices is not None:
                self._write(
                    bundle_root / "rules" / "sdd-coding-practices.md",
                    "sdd-coding-practices.md",
                    context,
                    result,
                )
            self._write(bundle_root / "hooks.json", "hooks.json", context, result)
            self._write(
                bundle_root / "metadata" / "provenance.json",
                "provenance.json",
                context,
                result,
            )
            hook_script = self._write(
                bundle_root / "hooks" / "session-start-assurance.sh",
                "session-start-assurance.sh",
                context,
                result,
            )
            hook_script.chmod(
                hook_script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH
            )

            for skill in skills_sorted:
                skill_dir = bundle_root / "skills" / skill.get("name", "unknown")
                skill_dir.mkdir(parents=True, exist_ok=True)
                self._write(
                    skill_dir / "SKILL.md",
                    "SKILL.md",
                    {**context, "skill": skill},
                    result,
                )

            license_source = Path(output_dir) / "LICENSE"
            if license_source.exists():
                license_dest = bundle_root / "LICENSE"
                shutil.copyfile(license_source, license_dest)
                result.files_written.append(str(license_dest))
        except Exception as e:  # defensive: partial bundle is still reported
            result.success = False
            result.errors.append(str(e))

        return result

    def _write(
        self,
        path: Path,
        template_name: str,
        context: dict[str, Any],
        result: DevinPluginResult,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        template = self.env.get_template(f"{template_name}.tpl")
        content = template.render(**context)
        path.write_text(content, encoding="utf-8")
        result.files_written.append(str(path))
        return path

    def generate_standalone(
        self, output_dir: Path, dest: Path | None = None
    ) -> DevinStandaloneResult:
        """
        Generate a zero-SDD-mention Devin project configuration: AGENTS.md,
        .devin/config.json, .devin/hooks.v1.json, .devin/rules/*.md (7 files).

        Args:
            output_dir: project root (used only to resolve the default dest).
            dest: output directory. Defaults to {output_dir}/dist/devin-standalone
                â€” a build artifact, same convention as generate()'s
                dist/devin-plugin default, never the project's real root files.
        """
        result = DevinStandaloneResult()
        context = {
            "standalone_ruleset_version": _STANDALONE_RULESET_VERSION,
            "last_verified": _STANDALONE_LAST_VERIFIED,
        }
        root = Path(dest) if dest else Path(output_dir) / "dist" / "devin-standalone"

        try:
            self._write_standalone(root / "AGENTS.md", "AGENTS.md", context, result)
            self._write_standalone(
                root / ".devin" / "config.json", "config.json", context, result
            )
            self._write_standalone(
                root / ".devin" / "hooks.v1.json", "hooks.v1.json", context, result
            )
            for rule_name in _STANDALONE_RULE_NAMES:
                self._write_standalone(
                    root / ".devin" / "rules" / f"{rule_name}.md",
                    f"rules/{rule_name}.md",
                    context,
                    result,
                )
        except Exception as e:  # defensive: partial output is still reported
            result.success = False
            result.errors.append(str(e))

        return result

    def _write_standalone(
        self,
        path: Path,
        template_name: str,
        context: dict[str, Any],
        result: DevinStandaloneResult,
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        template = self.standalone_env.get_template(f"{template_name}.tpl")
        content = template.render(**context)
        path.write_text(content, encoding="utf-8")
        result.files_written.append(str(path))
        return path
