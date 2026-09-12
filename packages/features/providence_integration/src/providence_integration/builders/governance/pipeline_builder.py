"""
Pipeline builder for governance artifacts.

Orchestrates parsing and fingerprinting of governance specifications
from multiple formats (v3.0 Markdown, legacy DSL).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from providence_integration.builders.governance.fingerprinter import (
    GovernanceFingerprinter,
)
from providence_integration.builders.governance.legacy_parser import LegacySpecParser
from providence_integration.builders.governance.markdown_parser import MarkdownParser


class PipelineBuilder:
    """Builds governance artifacts from source specifications with deterministic hashing."""

    # Architectural constants for data schema
    SCHEMA_VERSION = "3.0"
    CORE_KEY = "governance_core"
    CLIENT_KEY = "governance_client"
    HASH_ALGORITHM = "sha256"

    def __init__(
        self,
        spec_path: str,
        parsed_items: dict[str, list[dict[str, Any]]] | None = None,
        spec_mandates_path: Path | None = None,
    ):
        self.spec_path = Path(spec_path)
        self.parsed_items = parsed_items or {"mandates": [], "guidelines": []}
        self.spec_mandates_path = spec_mandates_path
        self.core_items: list[dict[str, Any]] = []
        self.client_items: list[dict[str, Any]] = []
        self.result: dict[str, Any] = {}

    def build(self) -> dict[str, Any]:
        """Parses source files and generates deterministic fingerprints.

        Supports both v3.0 Markdown format (mandate.md / guidelines.md)
        and legacy DSL format (mandate.spec / guidelines.dsl).
        """
        # Priority path: when wizard provides parsed items from phase-2-input,
        # compile from those items directly to respect user selections.
        parsed_mandates = self.parsed_items.get("mandates", [])
        parsed_guidelines = self.parsed_items.get("guidelines", [])
        if parsed_mandates or parsed_guidelines:
            self.core_items = [
                {
                    "id": item.get("id", ""),
                    "type": "MANDATE",
                    "title": item.get("title", ""),
                    "status": item.get("status", "required"),
                    "criticality": item.get(
                        "criticality", "high"
                    ),  # Default: mandates are high criticality
                }
                for item in sorted(parsed_mandates, key=lambda i: i.get("id", ""))
                if item.get("id")
            ]
            self.client_items = [
                {
                    "id": item.get("id", ""),
                    "type": "GUIDELINE",
                    "title": item.get("title", ""),
                    "status": item.get("status", "required"),
                    "criticality": item.get(
                        "criticality", "medium"
                    ),  # Default: guidelines are medium criticality
                }
                for item in sorted(parsed_guidelines, key=lambda i: i.get("id", ""))
                if item.get("id")
            ]

            core_fingerprint = GovernanceFingerprinter.generate(self.core_items)
            client_fingerprint = GovernanceFingerprinter.generate(
                self.client_items, salt=core_fingerprint
            )

            self.result = {
                self.CORE_KEY: {
                    "fingerprint": core_fingerprint,
                    "version": self.SCHEMA_VERSION,
                },
                self.CLIENT_KEY: {
                    "fingerprint": client_fingerprint,
                    "fingerprint_core_salt": core_fingerprint,
                    "version": self.SCHEMA_VERSION,
                },
                "core_items": self.core_items,
                "client_items": self.client_items,
            }
            return self.result

        # Resolve path resilience: check for meta/ or mandates/ subdirectory
        spec_root = self.spec_path
        if (
            not (spec_root / "mandate.md").exists()
            and not (spec_root / "mandate.spec").exists()
        ) and (spec_root / "meta").exists():
            spec_root = spec_root / "meta"

        # Prefer mandates/mandates.md (v3.0 structure) over the legacy
        # top-level mandate.md so stale generated compatibility files cannot
        # shadow the canonical readable source.
        if (spec_root / "mandates" / "mandates.md").exists():
            md_mandate = spec_root / "mandates" / "mandates.md"
        else:
            md_mandate = spec_root / "mandate.md"

        legacy_mandate = spec_root / "mandate.spec"

        if md_mandate.exists():
            mandate_content = md_mandate.read_text(encoding="utf-8")
            # Parse Markdown headings: `# M001: Title` or `## M001 Title`
            md_ids = re.findall(r"^#{1,3}\s+(M\d+)[:\s]", mandate_content, re.MULTILINE)
            self.core_items = [
                {
                    "id": mid,
                    "type": "MANDATE",
                    "title": MarkdownParser.extract_summary_minimal(
                        mandate_content, mid
                    )
                    or mid,
                    "status": "active",
                    "criticality": "high",
                    "summary_minimal": MarkdownParser.extract_summary_minimal(
                        mandate_content, mid
                    ),
                    "summary_runtime": MarkdownParser.extract_summary_runtime(
                        mandate_content, mid
                    ),
                }
                for mid in md_ids
            ]
            mandate_source = md_mandate
        elif legacy_mandate.exists():
            mandate_content = legacy_mandate.read_text(encoding="utf-8")
            self.core_items = LegacySpecParser.parse_mandates(mandate_content)
            mandate_source = legacy_mandate
        else:
            abs_path = (spec_root / "mandate.md").resolve()
            raise FileNotFoundError(
                f"mandate.spec not found at {abs_path}. "
                "Run 'providence governance compile' to regenerate governance artifacts."
            )

        self._require_parsed_mandates(mandate_source)

        # Guidelines: prefer guidelines.md, fall back to guidelines.dsl
        md_guidelines = spec_root / "guidelines.md"
        legacy_guidelines = spec_root / "guidelines.dsl"

        if md_guidelines.exists():
            gl_content = md_guidelines.read_text(encoding="utf-8")
            gl_ids = re.findall(r"^#{1,3}\s+(G\d+)[:\s]", gl_content, re.MULTILINE)
            self.client_items = [
                {
                    "id": g_id,
                    "type": "GUIDELINE",
                    "title": MarkdownParser.extract_summary_minimal(gl_content, g_id)
                    or g_id,
                    "status": "active",
                    "criticality": "medium",
                    "summary_minimal": MarkdownParser.extract_summary_minimal(
                        gl_content, g_id
                    ),
                    "summary_runtime": MarkdownParser.extract_summary_runtime(
                        gl_content, g_id
                    ),
                }
                for g_id in gl_ids
            ]
        elif legacy_guidelines.exists():
            gl_content = legacy_guidelines.read_text(encoding="utf-8")
            # Legacy block format: `guideline G001 { ... }`
            block_items = LegacySpecParser.parse_guidelines_blocks(gl_content)
            if block_items:
                self.client_items = block_items
            else:
                # Compact key-value format: `G01: Title` (one entry per block)
                gl_matches = re.findall(
                    r"^\s*(G\d+)\s*:\s+(.+)$", gl_content, re.MULTILINE
                )
                if gl_matches:
                    compact_map = {
                        gid: title.strip() for gid, title in gl_matches if gid.strip()
                    }
                    self.client_items = [
                        {
                            "id": g_id,
                            "type": "GUIDELINE",
                            "title": compact_map[g_id] or g_id,
                            "status": "active",
                            "criticality": "medium",
                        }
                        for g_id in sorted(compact_map)
                    ]
                else:
                    # Bullet/label fallback: `- [G01] ...`
                    bullet_ids = sorted(set(re.findall(r"\[(G\d+)\]", gl_content)))
                    self.client_items = [
                        {
                            "id": g_id,
                            "type": "GUIDELINE",
                            "title": g_id,
                            "status": "active",
                            "criticality": "medium",
                        }
                        for g_id in bullet_ids
                    ]
        else:
            self.client_items = []

        # Enrich core_items with rich spec content from .providence/spec/mandates.json
        self._merge_spec_content()

        # Phase 2: Deterministic Fingerprinting
        core_fingerprint = GovernanceFingerprinter.generate(self.core_items)
        # Client fingerprint uses core hash as salt to maintain referential integrity
        client_fingerprint = GovernanceFingerprinter.generate(
            self.client_items, salt=core_fingerprint
        )

        self.result = {
            self.CORE_KEY: {
                "fingerprint": core_fingerprint,
                "version": self.SCHEMA_VERSION,
            },
            self.CLIENT_KEY: {
                "fingerprint": client_fingerprint,
                "fingerprint_core_salt": core_fingerprint,
                "version": self.SCHEMA_VERSION,
            },
            "core_items": self.core_items,
            "client_items": self.client_items,
        }
        return self.result

    def _require_parsed_mandates(self, mandate_source: Path) -> None:
        """Fail fast when a mandate source file parses to zero items."""
        if self.core_items:
            return
        raise ValueError(
            f"Parsed 0 mandates from {mandate_source.resolve()}. The file "
            "exists but contains no recognizable mandate entries — it may be "
            "corrupt, empty, or a git symlink checked out as a plain text stub "
            "(common on Windows clones without symlink support). Reinstall "
            "from the release wheels or restore the canonical mandate source, "
            "then re-run 'providence governance generate'."
        )

    def _merge_spec_content(self) -> None:
        """Merge rich spec fields from .providence/spec/mandates.json into core_items."""
        if not self.spec_mandates_path or not self.spec_mandates_path.exists():
            return
        try:
            spec_data = json.loads(self.spec_mandates_path.read_text(encoding="utf-8"))
        except Exception:
            return
        spec_by_id: dict[str, dict[str, Any]] = {
            m["id"]: m for m in spec_data.get("mandates", []) if m.get("id")
        }
        for item in self.core_items:
            spec = spec_by_id.get(item.get("id", ""), {})
            if not spec:
                continue
            item.setdefault("enforcement_steps", spec.get("enforcement_steps"))
            item.setdefault("requirements", spec.get("requirements"))
            item.setdefault("rationale", spec.get("rationale"))
            if not item.get("summary_runtime"):
                item["summary_runtime"] = spec.get("summary_runtime")

    @classmethod
    def generate_spec_file(
        cls,
        canonical_mandates_dir: Path,
        output_path: Path,
        generated_by: str = "providence-wizard",
    ) -> dict[str, Any]:
        """Extract rich content from individual canonical M*.md files and write mandates.json.

        This is called by the wizard when generating a client template. The output is
        written to .providence/spec/mandates.json in the template and later consumed by
        _merge_spec_content() during providence governance compile on the client.

        Returns a summary dict with counts.
        """
        from datetime import datetime, timezone

        mandate_files = sorted(canonical_mandates_dir.glob("M*.md"))
        mandates = []
        for mf in mandate_files:
            content = mf.read_text(encoding="utf-8")
            item_id = mf.stem.split("_")[0]
            if not item_id.startswith("M"):
                continue

            title = MarkdownParser.extract_canonical_title(content) or item_id
            category = MarkdownParser.extract_canonical_category(content)
            summary_runtime = MarkdownParser.extract_canonical_summary_runtime(content)

            # Requirements: numbered list from Requirement section, fallback to Requirements
            requirements = (
                MarkdownParser.extract_numbered_list(content, "Requirement")
                or MarkdownParser.extract_numbered_list(content, "Requirements")
                or MarkdownParser.extract_bullet_list(content, "Requirements (MUST)")
            )

            # Rationale: full text of Rationale section
            rationale = MarkdownParser.extract_section_text(content, "Rationale")
            if rationale:
                rationale = " ".join(rationale.split())

            # Implementation pattern: first paragraph of Implementation section
            impl = MarkdownParser.extract_section_text(
                content, "Implementation Pattern"
            ) or MarkdownParser.extract_section_text(content, "Implementation")

            # Enforcement steps: bullets from Enforcement Steps section
            enforcement_steps = MarkdownParser.extract_bullet_list(
                content, "Enforcement Steps"
            )

            # Validation: checklist items from Validation section
            validation = MarkdownParser.extract_bullet_list(
                content, "Validation"
            ) or MarkdownParser.extract_bullet_list(content, "Validation Checklist")

            mandates.append(
                {
                    "id": item_id,
                    "title": title,
                    "category": category,
                    "summary_runtime": summary_runtime,
                    "requirements": requirements,
                    "rationale": rationale,
                    "implementation_pattern": impl,
                    "enforcement_steps": enforcement_steps,
                    "validation": validation,
                }
            )

        payload = {
            "schema": "1.0",
            "generated_by": generated_by,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "mandates": mandates,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        return {"mandates_written": len(mandates), "output": str(output_path)}

    def save_outputs(self, output_dir: str) -> dict[str, Any]:
        """Saves the built JSON artifacts for Phase 2 (Compiler)."""
        if not self.result:
            self.build()

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        core_output = {
            "category": "CORE",
            "version": self.result["governance_core"]["version"],
            "fingerprint": self.result["governance_core"]["fingerprint"],
            "items": self.result["core_items"],
        }

        client_output = {
            "category": "CLIENT",
            "version": self.result["governance_client"]["version"],
            "fingerprint": self.result["governance_client"]["fingerprint"],
            "fingerprint_core_salt": self.result["governance_client"][
                "fingerprint_core_salt"
            ],
            "items": self.result["client_items"],
        }

        core_path = out_path / "governance-core.json"
        client_path = out_path / "governance-client.json"

        with open(core_path, "w", encoding="utf-8") as f:
            json.dump(core_output, f, indent=2, ensure_ascii=False)

        with open(client_path, "w", encoding="utf-8") as f:
            json.dump(client_output, f, indent=2, ensure_ascii=False)

        return {
            "governance_core": str(core_path),
            "governance_client": str(client_path),
            "core_fingerprint": core_output["fingerprint"],
            "client_fingerprint": client_output["fingerprint"],
        }
