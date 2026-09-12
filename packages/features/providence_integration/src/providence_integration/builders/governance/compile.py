#!/usr/bin/env python3
"""
PHASE 2: Compile governance from source/ → governance-core.json + governance-client.json

Reads:
  - core/source/{mandates,guidelines,decisions,rules,guardrails}/*.md
  - user_selections.json (which items go to CORE vs CLIENT)

Outputs:
  - governance-core.json (immutable items)
  - governance-client.json (customizable items)
  - metadata-core.json (with fingerprint)
  - metadata-client.json (with fingerprint and core_salt)

Fingerprinting strategy:
  - fingerprintpackages = SHA256(governance-core.json)
  - fingerprint_client = SHA256(fingerprintpackages + governance-client.json)  ← SALT!
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class GovernanceCompiler:
    """GovernanceCompiler."""

    # World-class practice: Centralize architectural constants
    VERSION = "3.0"
    CORE_TYPE = "GOVERNANCE_CORE"
    CLIENT_TYPE = "GOVERNANCE_CLIENT"
    FINGERPRINT_KEY = "fingerprint"
    SALT_KEY = "fingerprint_core_salt"

    def __init__(self, core_path: str = "core"):
        self.core_path = Path(core_path)
        self.source_path = self.core_path / "source"
        self.selections: dict[str, Any] = {}
        self.all_items: list[dict[str, Any]] = []
        self.core_items: list[dict[str, Any]] = []
        self.client_items: list[dict[str, Any]] = []

    def load_selections(
        self, selections_file: str = "user_selections_sample.json"
    ) -> None:
        """Load user selections (CORE vs CLIENT)"""
        logger.info("Loading user selections...")

        selections_path = Path(selections_file)
        if not selections_path.exists():
            logger.warning(f"{selections_file} not found, using all as CORE")
            return

        data = json.loads(selections_path.read_text(encoding="utf-8"))
        self.selections = data.get("selections", {})

        core_count = sum(1 for s in self.selections.values() if s["choice"] == "CORE")
        client_count = sum(
            1 for s in self.selections.values() if s["choice"] == "CLIENT"
        )
        logger.info(f"Loaded {len(self.selections)} item selections")
        logger.debug(f"  CORE items: {core_count}")
        logger.debug(f"  CLIENT items: {client_count}")

    def extract_markdown_items(self) -> None:
        """Extract all markdown items from source/"""
        logger.info("Extracting markdown items from source/...")

        for item_type in ["mandates", "guidelines", "decisions", "rules", "guardrails"]:
            type_dir = self.source_path / item_type
            if not type_dir.exists():
                logger.debug(f"source/{item_type}/ not found")
                continue

            md_files = sorted(type_dir.glob("*.md"))
            logger.debug(f"Reading source/{item_type}/ ({len(md_files)} items)")

            for md_file in md_files:
                item = self._parse_markdown_item(md_file, item_type.rstrip("s").upper())
                if item:
                    self.all_items.append(item)

        logger.info(f"Extracted {len(self.all_items)} total items")

    def _parse_markdown_item(
        self, md_file: Path, item_type: str
    ) -> dict[str, Any] | None:
        """Parse YAML frontmatter from markdown file"""
        content = md_file.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        yaml_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not yaml_match:
            logger.debug(f"No YAML in {md_file.name}")
            return None

        try:
            frontmatter = yaml.safe_load(yaml_match.group(1))
        except yaml.YAMLError as e:
            logger.debug(f"YAML error in {md_file.name}: {e}")
            return None

        item = {
            "id": frontmatter.get("id", md_file.stem),
            "title": frontmatter.get("title", ""),
            "type": frontmatter.get("type", item_type),
            "criticality": frontmatter.get("criticality", "OPCIONAL"),
            "customizable": frontmatter.get("customizable", False),
            "optional": frontmatter.get("optional", True),
            "category": frontmatter.get("category", "general"),
            "source_file": str(md_file.relative_to(self.core_path)),
        }

        return item

    def separatepackages_client(self) -> None:
        """Separate items into CORE vs CLIENT based on user selections"""
        logger.info("Separating CORE vs CLIENT items...")

        for item in self.all_items:
            item_id = item["id"]

            # Check if in selections
            if item_id in self.selections:
                choice = self.selections[item_id]["choice"]
                if choice == "CORE":
                    self.core_items.append(item)
                else:
                    self.client_items.append(item)
            else:
                # Default: if not in selections, follow criticality
                if item["criticality"] == "OBRIGATÓRIO":
                    self.core_items.append(item)
                elif item["customizable"]:
                    self.client_items.append(item)
                else:
                    self.core_items.append(item)

        logger.info(f"CORE items:   {len(self.core_items)}")
        logger.info(f"CLIENT items: {len(self.client_items)}")

    def calculate_fingerprint(self, data: dict[str, Any]) -> str:
        """Calculate SHA256 fingerprint"""
        # Create copy without fingerprint fields
        data_copy = {
            k: v
            for k, v in data.items()
            if k not in [self.FINGERPRINT_KEY, self.SALT_KEY]
        }

        # Hash as sorted JSON
        hash_input = json.dumps(data_copy, sort_keys=True).encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()

    def generate_governance_files(self) -> None:
        """Generate governance-core.json and governance-client.json"""
        logger.info("Generating governance files...")

        # Create core structure
        governance_core = {
            "version": self.VERSION,
            "type": self.CORE_TYPE,
            "readonly": True,
            "compiled_at": datetime.now().isoformat(),
            "items": self.core_items,
            "metadata": {"total_items": len(self.core_items), "customizable": False},
        }

        # Create client structure
        governance_client = {
            "version": self.VERSION,
            "type": self.CLIENT_TYPE,
            "readonly": False,
            "compiled_at": datetime.now().isoformat(),
            "items": self.client_items,
            "metadata": {"total_items": len(self.client_items), "customizable": True},
        }

        # Calculate fingerprints
        fingerprint_core = self.calculate_fingerprint(governance_core)
        governance_core[self.FINGERPRINT_KEY] = fingerprint_core

        # Client fingerprint uses core fingerprint as salt
        combined_for_client = {
            **governance_client,
            "fingerprint_core_salt": fingerprint_core,
        }
        fingerprint_client = self.calculate_fingerprint(combined_for_client)
        governance_client["fingerprint"] = fingerprint_client
        governance_client["fingerprint_core_salt"] = fingerprint_core

        # Save files
        output_dir = self.core_path.parent / "compiler" / "compiled"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save core JSON
        core_path = output_dir / "governance-core.json"
        core_path.write_text(
            json.dumps(governance_core, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug(f"Saved {core_path.relative_to(self.core_path.parent)}")

        # Save client JSON
        client_path = output_dir / "governance-client.json"
        client_path.write_text(
            json.dumps(governance_client, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug(f"Saved {client_path.relative_to(self.core_path.parent)}")

        # Save metadata files
        metadata_core = {
            "version": self.VERSION,
            "type": self.CORE_TYPE,
            "readonly": True,
            "compiled_at": governance_core["compiled_at"],
            "fingerprint": fingerprint_core,
            "items_count": len(self.core_items),
        }

        metadata_core_path = output_dir / "metadata-core.json"
        metadata_core_path.write_text(
            json.dumps(metadata_core, indent=2), encoding="utf-8"
        )
        logger.debug(f"Saved {metadata_core_path.relative_to(self.core_path.parent)}")

        metadata_client = {
            "version": "3.0",
            "type": "GOVERNANCE_CLIENT",
            "readonly": False,
            "compiled_at": governance_client["compiled_at"],
            "fingerprint": fingerprint_client,
            "fingerprint_core_salt": fingerprint_core,
            "items_count": len(self.client_items),
        }

        metadata_client_path = output_dir / "metadata-client.json"
        metadata_client_path.write_text(
            json.dumps(metadata_client, indent=2), encoding="utf-8"
        )
        logger.debug(f"Saved {metadata_client_path.relative_to(self.core_path.parent)}")

        logger.info(f"Core fingerprint:   {fingerprint_core}")
        logger.info(f"Client fingerprint: {fingerprint_client}")

    def print_summary(self) -> None:
        """Log compilation summary"""
        logger.info("PHASE 2: GOVERNANCE COMPILATION COMPLETE")
        logger.info(f"Total items extracted: {len(self.all_items)}")
        logger.info(f"  CORE (immutable):    {len(self.core_items)} items")
        logger.info(f"  CLIENT (customizable): {len(self.client_items)} items")

        output_dir = self.core_path.parent / "compiler" / "compiled"
        logger.debug(f"Files generated in {output_dir}/")
        logger.debug("  ├── governance-core.json")
        logger.debug("  ├── governance-client.json")
        logger.debug("  ├── metadata-core.json")
        logger.debug("  └── metadata-client.json")

        # Show sample items
        for item in self.core_items[:3]:
            logger.debug(f"CORE: {item['id']}: {item['title'][:50]}")
        if len(self.core_items) > 3:
            logger.debug(f"... and {len(self.core_items) - 3} more CORE items")

        for item in self.client_items[:3]:
            logger.debug(f"CLIENT: {item['id']}: {item['title'][:50]}")
        if len(self.client_items) > 3:
            logger.debug(f"... and {len(self.client_items) - 3} more CLIENT items")

    def run(self, selections_file: str = "user_selections_sample.json") -> None:
        """Execute full compilation"""
        logger.info("PHASE 2: COMPILE GOVERNANCE (source → JSON)")

        self.load_selections(selections_file)
        self.extract_markdown_items()
        self.separatepackages_client()
        self.generate_governance_files()
        self.print_summary()


if __name__ == "__main__":
    import sys

    # Determine correct path
    from pathlib import Path

    current_dir = Path.cwd()
    core_path = current_dir if current_dir.name == "core" else current_dir / "core"

    compiler = GovernanceCompiler(str(core_path))

    # Allow custom selections file as argument
    selections_file = (
        sys.argv[1] if len(sys.argv) > 1 else "user_selections_sample.json"
    )
    compiler.run(selections_file)
