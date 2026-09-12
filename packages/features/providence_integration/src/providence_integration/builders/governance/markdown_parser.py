"""Markdown content parsing for v3.0 governance specifications."""

from __future__ import annotations

import re


class MarkdownParser:
    """Extracts governance item metadata from Markdown content."""

    @staticmethod
    def _strip_trailing_section_separators(text: str) -> str:
        """Remove trailing horizontal-rule separators from extracted section text."""
        lines = text.splitlines()
        while lines and not lines[-1].strip():
            lines.pop()
        while lines and lines[-1].strip() == "---":
            lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()
        return "\n".join(lines).strip()

    @staticmethod
    def extract_summary_minimal(content: str, item_id: str) -> str | None:
        """Extract one-line minimal summary for an item from Markdown.

        Looks for pattern: `# ITEM_ID: One-line summary`
        or returns first non-empty line after heading if no colon.

        Args:
            content: Markdown content
            item_id: Item ID to extract summary for (e.g., M001, G002)

        Returns:
            Minimal summary or None if not found
        """
        # Try to extract title from heading
        pattern = rf"^#{{1,3}}\s+{item_id}[:\s]+(.+?)$"
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Validate: reject malformed titles (e.g., "- Status: Accepted")
            if title.startswith("-"):
                return None
            # Reject single-word status keywords
            if title.lower() in ("accepted", "rejected", "pending", "status"):
                return None
            return title
        return None

    @staticmethod
    def extract_summary_runtime(content: str, item_id: str) -> str | None:
        """Extract runtime summary (enforcement rules) for an item from Markdown.

        Looks for content between the item's heading and the next item heading.
        Returns first paragraph or up to 200 chars of description.

        Args:
            content: Markdown content
            item_id: Item ID to extract summary for (e.g., M001, G002)

        Returns:
            Runtime summary or None if not found
        """
        # Find the section for this item (from its heading to next item heading)
        pattern = rf"^#{{1,3}}\s+{item_id}[:\s]+.+?$\n(.*?)(?=^#{{1,3}}\s+[MG]\d+|$)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            section_content = match.group(1).strip()
            # Extract first non-empty line after heading
            lines = [
                line.strip() for line in section_content.split("\n") if line.strip()
            ]
            if lines:
                # Return first line, limited to 200 chars for runtime summary
                first_line = lines[0]
                return first_line[:197] + "..." if len(first_line) > 200 else first_line
        return None

    # ------------------------------------------------------------------
    # Individual canonical file extraction (for .providence/spec generation)
    # These methods operate on single-mandate files (# Mandate: Title format)
    # ------------------------------------------------------------------

    @staticmethod
    def extract_canonical_title(content: str) -> str | None:
        """Extract title from an individual canonical mandate/guideline file.

        Reads the top-level heading and strips the 'Mandate:' / 'Guideline:' prefix.
        """
        match = re.search(
            r"^#\s+(?:Mandate:|Guideline:)?\s*(.+)$", content, re.MULTILINE
        )
        return match.group(1).strip() if match else None

    @staticmethod
    def extract_section_text(content: str, section_heading: str) -> str | None:
        """Extract the full text body of a named section from a canonical file.

        Matches headings like '## Goal', '## 🎯 Goal', '## Enforcement Steps', etc.
        Returns None if the section is absent or empty.
        """
        # Strip leading emoji/symbols for flexible matching
        escaped = re.escape(section_heading)
        pattern = rf"^#{{1,3}}\s+(?:[^\w\s]*\s*)?{escaped}\s*$\n(.*?)(?=^#{{1,3}}\s|\Z)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if not match:
            return None
        section = MarkdownParser._strip_trailing_section_separators(match.group(1))
        return section or None

    @staticmethod
    def extract_bullet_list(content: str, section_heading: str) -> list[str] | None:
        """Extract bullet items from a named section.

        Handles '-', '*', '•', and checkbox '- [ ]' / '- [x]' prefixes.
        """
        section = MarkdownParser.extract_section_text(content, section_heading)
        if not section:
            return None
        items = []
        for line in section.splitlines():
            if re.match(r"^\s*[-*•]\s+", line):
                # Strip checkbox markers and bullet prefix
                cleaned = re.sub(r"^\s*[-*•]\s+\[.\]\s*", "", line)
                cleaned = re.sub(r"^\s*[-*•]\s+", "", cleaned).strip()
                if cleaned:
                    items.append(cleaned)
        return items if items else None

    @staticmethod
    def extract_numbered_list(content: str, section_heading: str) -> list[str] | None:
        """Extract numbered items from a named section."""
        section = MarkdownParser.extract_section_text(content, section_heading)
        if not section:
            return None
        items = []
        for line in section.splitlines():
            m = re.match(r"^\s*\d+\.\s+\*{0,2}(.+?)\*{0,2}:\s*(.*)", line)
            if m:
                # "1. **Label**: description" → "Label: description"
                label, desc = m.group(1).strip(), m.group(2).strip()
                items.append(f"{label}: {desc}" if desc else label)
                continue
            m2 = re.match(r"^\s*\d+\.\s+(.+)", line)
            if m2:
                items.append(m2.group(1).strip())
        return items if items else None

    @staticmethod
    def extract_canonical_category(content: str) -> str | None:
        """Extract category from **Category:** field in canonical file."""
        match = re.search(r"^\*\*Category:\*\*\s*(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else None

    @staticmethod
    def extract_canonical_summary_runtime(content: str) -> str | None:
        """Extract a runtime summary from a canonical individual file.

        Uses the Goal section's first non-empty line (≤200 chars).
        Falls back to Objective section for mandates that use that heading.
        """
        for heading in ("Goal", "Objective"):
            section = MarkdownParser.extract_section_text(content, heading)
            if section:
                paragraphs = [
                    part.strip()
                    for part in re.split(r"\n\s*\n", section)
                    if part.strip()
                ]
                if paragraphs:
                    first_paragraph = " ".join(paragraphs[0].split())
                    return (
                        first_paragraph[:197] + "..."
                        if len(first_paragraph) > 200
                        else first_paragraph
                    )
        return None
