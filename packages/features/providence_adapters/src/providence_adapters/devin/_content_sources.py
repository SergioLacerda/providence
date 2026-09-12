"""Governance-summary and coding-practices content sourcing for the Devin plugin.

Parses the repository's own governed markdown sources (mandates, guidelines,
anti-pattern docs) into the plain dicts `plugin_generator.py` renders into the
bundle. Split out of `plugin_generator.py` (ADR-019 module-size budget) â€”
this half is pure content parsing, independent of the Jinja2/bundle-writing
concerns that stay in `plugin_generator.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_PLACEHOLDER_DESCRIPTION = "no description available"
_SECTION_HEADING_RE = re.compile(r"^#{2,3} (\S+): (.+)$")

_ANTI_PATTERN_SOURCES = (
    "COGNITIVE_OVERLOAD",
    "PREMATURE_EXECUTION",
    "RESOLUTION_BYPASS",
    "SCOPE_CREEP",
    "SYMPTOM_FIXING",
)
_ANTI_PATTERNS_DIR = Path("docs") / "cognition" / "anti-patterns"
_GO_RESOLUTION_BYPASS_PATH = (
    Path("docs") / "cognition" / "anti-patterns" / "lang" / "GO_RESOLUTION_BYPASS.md"
)

# Matched by substring, not exact phrase â€” heading wording is not identical
# across the 5 source files (e.g. RESOLUTION_BYPASS.md uses "The Universal
# Cure" while the others use "The Cure"). Order matters only for readability;
# lookup below checks all keys regardless of order.
_ANTI_PATTERN_SECTION_KEYS = {
    "problem": "Problem",
    "cure": "Cure",
    "benchmark": "Benchmark",
    "symptoms": "Symptoms",
    "danger": "Dangerous",
}
_REQUIRED_ANTI_PATTERN_KEYS = ("problem", "cure", "benchmark")

_GO_RESOLUTION_BYPASS_SECTION_KEYS = {
    "hacks": "Go-Specific Hacks",
    "cures": "Go Cures",
    "detection": "Detection",
    "rule": "Rule",
}
_REQUIRED_GO_RESOLUTION_BYPASS_KEYS = ("hacks", "cures", "rule")


def _parse_governance_sections(text: str) -> list[dict[str, Any]]:
    """Parse '## <ID>: <Title>' or '### <ID>: <Title>' sections (mandates.md /
    guidelines/*.md shape â€” heading level is inconsistent across source files,
    e.g. general.md uses '##' and other.md uses '###').

    Each section is a heading, a metadata block of '**Field**: value' lines, and
    a trailing description paragraph. A description equal to the source's own
    "No description available" placeholder is reported as has_description=False
    rather than treated as real content â€” callers must not fabricate a summary
    for those sections.
    """
    sections: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    body_lines: list[str] = []

    def _finalize() -> None:
        if current is None:
            return
        description = " ".join(
            line.strip()
            for line in body_lines
            if line.strip() and not line.strip().startswith("**")
        ).strip()
        has_description = (
            bool(description) and description.lower() != _PLACEHOLDER_DESCRIPTION
        )
        sections.append(
            {
                "id": current["id"],
                "title": current["title"],
                "description": description if has_description else "",
                "has_description": has_description,
            }
        )

    for line in text.splitlines():
        match = _SECTION_HEADING_RE.match(line)
        if match:
            _finalize()
            current = {"id": match.group(1), "title": match.group(2).strip()}
            body_lines = []
            continue
        if current is not None:
            body_lines.append(line)
    _finalize()
    return sections


def _match_section_marker(
    heading_text: str, keys: dict[str, str]
) -> tuple[str | None, str]:
    """Find which key's marker appears in heading_text; return (key, trailing_content).

    trailing_content is whatever follows the marker on the same line. Some
    source files jam heading and content onto one line with no line break
    (e.g. GO_RESOLUTION_BYPASS.md's '## \U0001f4cf Rule> Your code should...') â€”
    without this, that content would be silently dropped rather than captured.
    """
    for key, marker in keys.items():
        idx = heading_text.find(marker)
        if idx != -1:
            return key, heading_text[idx + len(marker) :].strip()
    return None, ""


def _extract_title(lines: list[str], source_name: str) -> str:
    """Return the first '# <Title>' heading's text, or raise if none exists."""
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip()
    raise ValueError(f"{source_name}: missing title ('# <Title>' heading)")


def _split_marked_sections(
    lines: list[str], keys: dict[str, str], *, track_fences: bool
) -> dict[str, str]:
    """Split lines on '## ' headings matched against `keys` (via
    _match_section_marker), returning {key: joined_body_text}.

    When track_fences is True, a heading-shaped line *inside* a ``` code
    fence (e.g. SCOPE_CREEP.md's fenced "## Parking Lot" example) is treated
    as example content, not a real section boundary â€” see
    _parse_anti_pattern's docstring for why this matters.
    """
    sections: dict[str, str] = {}
    current_key: str | None = None
    body: list[str] = []
    in_code_fence = False

    def _flush() -> None:
        if current_key is not None:
            sections[current_key] = "\n".join(body).strip()

    for line in lines:
        if track_fences and line.startswith("```"):
            in_code_fence = not in_code_fence
            if current_key is not None:
                body.append(line)
            continue
        if line.startswith("## ") and not (track_fences and in_code_fence):
            _flush()
            heading_text = line[3:].strip()
            current_key, trailing = _match_section_marker(heading_text, keys)
            body = [trailing] if trailing else []
            continue
        if current_key is not None:
            body.append(line)
    _flush()
    return sections


def _require_sections(
    sections: dict[str, str],
    required_keys: tuple[str, ...],
    keys: dict[str, str],
    source_name: str,
) -> None:
    """Raise ValueError naming every required key missing from `sections`."""
    missing = [keys[key] for key in required_keys if not sections.get(key)]
    if missing:
        raise ValueError(
            f"{source_name}: missing required section(s): {', '.join(missing)}"
        )


def _parse_anti_pattern(text: str, source_name: str) -> dict[str, Any]:
    """Parse a docs/cognition/anti-patterns/*.md file.

    Unlike _parse_governance_sections, a missing required section is NOT a
    tolerable state here â€” these are fixed, hand-authored, first-party files
    with a confirmed-consistent shape, so a missing Problem/Cure/Benchmark
    section means the source itself is structurally broken. Raises ValueError
    rather than degrading silently (R-008 mitigation from
    .analysis/refined/20260817-devin-plugin-cognition-runtime-go-case/design.md).
    """
    lines = text.splitlines()
    title = _extract_title(lines, source_name)
    sections = _split_marked_sections(
        lines, _ANTI_PATTERN_SECTION_KEYS, track_fences=True
    )
    _require_sections(
        sections, _REQUIRED_ANTI_PATTERN_KEYS, _ANTI_PATTERN_SECTION_KEYS, source_name
    )

    return {
        "id": source_name,
        "title": title,
        "problem": sections.get("problem", ""),
        "cure": sections.get("cure", ""),
        "benchmark": sections.get("benchmark", ""),
        "symptoms": sections.get("symptoms", ""),
        "danger": sections.get("danger", ""),
        "has_symptoms": bool(sections.get("symptoms")),
        "has_danger": bool(sections.get("danger")),
    }


def _parse_go_resolution_bypass(text: str, source_name: str) -> dict[str, Any]:
    """Parse docs/cognition/anti-patterns/lang/GO_RESOLUTION_BYPASS.md.

    No fence tracking â€” unlike the anti-pattern files, this file's code
    fences are inconsistently glued to their surrounding text (open and close
    markers don't reliably start their own line), so naive fence-toggling
    would misfire; there is also no confirmed '## ' heading inside any of its
    fences today, so tracking isn't needed to parse it correctly. Same
    loud-failure contract as _parse_anti_pattern: a missing required section
    raises ValueError.
    """
    sections = _split_marked_sections(
        text.splitlines(), _GO_RESOLUTION_BYPASS_SECTION_KEYS, track_fences=False
    )
    _require_sections(
        sections,
        _REQUIRED_GO_RESOLUTION_BYPASS_KEYS,
        _GO_RESOLUTION_BYPASS_SECTION_KEYS,
        source_name,
    )

    return {
        "hacks": sections.get("hacks", ""),
        "cures": sections.get("cures", ""),
        "detection": sections.get("detection", ""),
        "rule": sections.get("rule", ""),
    }


def _load_coding_practices(output_dir: Path) -> dict[str, Any] | None:
    """Load the Go-pilot coding practices content.

    The whole docs/cognition/anti-patterns/ category is optional and degrades
    gracefully (returns None) when entirely absent â€” this content is specific
    to the Providence repository itself, not something every consuming
    project has (unlike .providence/, which the wizard scaffolds everywhere). But once
    the category is present, an individual missing file or malformed section
    within it is a hard failure (ValueError) â€” that indicates the source
    itself is broken, not that the feature is optional for this project.
    """
    anti_patterns_dir = Path(output_dir) / _ANTI_PATTERNS_DIR
    if not anti_patterns_dir.exists():
        return None

    anti_patterns = []
    for source_name in _ANTI_PATTERN_SOURCES:
        path = anti_patterns_dir / f"{source_name}.md"
        if not path.exists():
            raise ValueError(f"missing anti-pattern source: {path}")
        anti_patterns.append(
            _parse_anti_pattern(path.read_text(encoding="utf-8"), str(path))
        )

    go_path = Path(output_dir) / _GO_RESOLUTION_BYPASS_PATH
    if not go_path.exists():
        raise ValueError(f"missing anti-pattern source: {go_path}")
    go_resolution_bypass = _parse_go_resolution_bypass(
        go_path.read_text(encoding="utf-8"), str(go_path)
    )

    return {
        "anti_patterns": anti_patterns,
        "go_resolution_bypass": go_resolution_bypass,
    }


def _coding_practices_digest(coding_practices: dict[str, Any]) -> str:
    """Deterministic sha256 over coding-practices content, independent of the
    other three digest/version fields."""
    canonical_input = {
        "anti_patterns": [
            {
                "id": ap["id"],
                "title": ap["title"],
                "problem": ap["problem"],
                "cure": ap["cure"],
                "benchmark": ap["benchmark"],
            }
            for ap in coding_practices["anti_patterns"]
        ],
        "go_resolution_bypass": coding_practices["go_resolution_bypass"],
    }
    canonical = json.dumps(canonical_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_governance_summary(output_dir: Path) -> dict[str, Any]:
    """Load a best-effort Providence governance summary for embedding.

    Degrades gracefully (empty lists, "unknown" fields) when .providence/metadata.json
    or .providence/source/mandates/mandates.md are absent â€” this is additive content,
    never a reason to fail plugin generation.
    """
    sdd_dir = Path(output_dir) / ".providence"
    metadata_path = sdd_dir / "metadata.json"
    mandates_path = sdd_dir / "source" / "mandates" / "mandates.md"
    guidelines_dir = sdd_dir / "source" / "guidelines"

    governance_fingerprint = "unknown"
    workspace_version = "unknown"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            governance_fingerprint = str(
                metadata.get("governance_fingerprint", governance_fingerprint)
            )
            workspace_version = str(metadata.get("version", workspace_version))
        except (OSError, json.JSONDecodeError):
            # Best-effort only: fall back to the "unknown" defaults already
            # set above rather than fail plugin generation over a metadata
            # file that's missing, unreadable, or malformed.
            pass

    mandates: list[dict[str, Any]] = []
    if mandates_path.exists():
        mandates = _parse_governance_sections(mandates_path.read_text(encoding="utf-8"))

    guideline_categories: list[str] = []
    guidelines: list[dict[str, Any]] = []
    if guidelines_dir.exists():
        for guideline_file in sorted(guidelines_dir.glob("*.md")):
            guideline_categories.append(guideline_file.stem)
            items = _parse_governance_sections(
                guideline_file.read_text(encoding="utf-8")
            )
            described = [
                item["description"] for item in items if item["has_description"]
            ]
            guidelines.append(
                {
                    "category": guideline_file.stem,
                    "highlight": described[0] if described else "",
                    "has_highlight": bool(described),
                }
            )

    return {
        "governance_fingerprint": governance_fingerprint,
        "workspace_version": workspace_version,
        "mandate_count": len(mandates),
        "mandate_described_count": sum(1 for m in mandates if m["has_description"]),
        "mandates": mandates,
        "guideline_categories": guideline_categories,
        "guidelines": guidelines,
    }


def _governance_summary_digest(summary: dict[str, Any]) -> str:
    """Deterministic sha256 over the governance summary, independent of _policy_digest."""
    canonical_input = {
        "governance_fingerprint": summary["governance_fingerprint"],
        "workspace_version": summary["workspace_version"],
        "mandate_count": summary["mandate_count"],
        "mandates": [
            {
                "id": m["id"],
                "title": m["title"],
                "has_description": m["has_description"],
            }
            for m in summary["mandates"]
        ],
        "guideline_categories": summary["guideline_categories"],
    }
    canonical = json.dumps(canonical_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
