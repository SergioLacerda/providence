"""Non-blocking language governance advisory checks (M011)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from providence_cli.services.governance_config_reader import (
    _workspace_root_from_governance_path,
)

_PORTUGUESE_MARKER_RE = re.compile(
    r"\b(no|para|como|uma|idioma|portugus|governana|artefatos|deve|pode|documentao|estruturada)\b",
    re.IGNORECASE,
)


def _detect_non_english_markers(root: Path, *, limit: int = 5) -> list[str]:
    """Return a small sample of files containing obvious Portuguese markers."""
    matches: list[str] = []
    if not root.exists():
        return matches
    for file_path in sorted(root.rglob("*.md")):
        if len(matches) >= limit:
            break
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _PORTUGUESE_MARKER_RE.search(content):
            matches.append(str(file_path))
    return matches


def _build_language_governance_advisories(
    *, path: str, config: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Build non-blocking language governance advisories from mandates/guidelines/context."""
    advisories: list[dict[str, Any]] = []
    config = config or {}
    items = config.get("items", [])
    language_context = config.get("language_context", {})
    workspace_root = _workspace_root_from_governance_path(path)
    docs_root = workspace_root / "docs"
    analysis_root = workspace_root / ".analysis"

    m011_active = any(
        isinstance(item, dict)
        and item.get("id") == "M011"
        and item.get("type") == "MANDATE"
        for item in items
    )
    advisories.append(
        {
            "check": "Language mandate core (M011)",
            "severity": "info" if m011_active else "warn",
            "status": "pass" if m011_active else "warn",
            "message": "M011 is active for mandatory language surfaces."
            if m011_active
            else "M011 was not found in compiled mandate metadata.",
        }
    )

    source_dir = Path(path).resolve().parent / "source"
    source_guidelines_candidates = [source_dir / "guidelines.dsl"]
    guidelines_dir = source_dir / "guidelines"
    if guidelines_dir.is_dir():
        source_guidelines_candidates.extend(sorted(guidelines_dir.glob("*.md")))
    has_language_guidelines = any(
        all(gid in candidate.read_text(encoding="utf-8") for gid in ("G021", "G022"))
        for candidate in source_guidelines_candidates
        if candidate.exists()
    )
    advisories.append(
        {
            "check": "Language preference guidelines",
            "severity": "info" if has_language_guidelines else "warn",
            "status": "pass" if has_language_guidelines else "warn",
            "message": "Universal language preference guidelines are present."
            if has_language_guidelines
            else "Language preference guidelines were not found in .providence/source/guidelines.dsl or .providence/source/guidelines/*.md.",
        }
    )

    analysis_classified = (analysis_root / "README.md").exists()
    advisories.append(
        {
            "check": "Analysis workspace classification",
            "severity": "info" if analysis_classified else "warn",
            "status": "pass" if analysis_classified else "warn",
            "message": ".analysis/ is documented as workspace-local documentation under contextual language guidance."
            if analysis_classified
            else ".analysis/ classification is not explicitly documented; local language handling may be ambiguous.",
            "surface": "workspace_local_docs",
        }
    )

    mandatory_docs_samples = _detect_non_english_markers(docs_root)
    if m011_active and mandatory_docs_samples:
        advisories.append(
            {
                "check": "Mandatory docs surface language drift",
                "severity": "warn",
                "status": "warn",
                "message": "Possible non-English markers were found under docs/. Review canonical technical documentation for M011 alignment.",
                "surface": "technical_docs",
                "samples": mandatory_docs_samples,
            }
        )
    else:
        advisories.append(
            {
                "check": "Mandatory docs surface language drift",
                "severity": "info",
                "status": "pass" if m011_active else "info",
                "message": "No obvious non-English markers were sampled under docs/."
                if m011_active
                else "Docs surface sampling skipped because M011 is not active.",
                "surface": "technical_docs",
            }
        )

    local_analysis_samples = _detect_non_english_markers(analysis_root)
    if local_analysis_samples:
        advisories.append(
            {
                "check": "Local analysis language context",
                "severity": "info",
                "status": "info",
                "message": "Non-English content exists under .analysis/ and is treated as contextual workspace-local documentation unless promoted to canonical docs.",
                "surface": "workspace_local_docs",
                "samples": local_analysis_samples,
            }
        )

    if isinstance(language_context, dict) and language_context:
        advisories.append(
            {
                "check": "Wizard language context captured",
                "severity": "info",
                "status": "pass",
                "message": "Wizard language preference context is available to governed tooling.",
            }
        )
        local_docs_language = language_context.get("preferred_local_docs_language")
        if m011_active and local_docs_language and local_docs_language != "English":
            advisories.append(
                {
                    "check": "Local docs preference under M011",
                    "severity": "warn",
                    "status": "warn",
                    "message": "Local documentation preference is non-English; this may guide local-only notes but does not override M011 for technical documentation or governance artifacts.",
                }
            )
    else:
        advisories.append(
            {
                "check": "Wizard language context captured",
                "severity": "info",
                "status": "info",
                "message": "No wizard language preference context was found; contextual language guidance may be unavailable.",
            }
        )

    return advisories


def _render_advisory_status(status: str) -> str:
    """Render advisory status with Rich markup."""
    normalized = status.lower()
    if normalized == "pass":
        return "[green]PASS[/green]"
    if normalized == "warn":
        return "[yellow]WARN[/yellow]"
    if normalized == "info":
        return "[blue]INFO[/blue]"
    return status.upper()
