"""ReadmeWriter  generates .providence/source/README.md and .providence/runtime/README.md."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from providence_core.utils.log import get_logger

from ._readme_templates import build_runtime_readme, build_source_readme

logger = get_logger(__name__)


class ReadmeWriter:
    """Write source and runtime README files."""

    def __init__(
        self,
        source_dir: Path,
        runtime_dir: Path,
        mandates: list[dict[str, Any]],
        guidelines: dict[str, Any],
        guidelines_by_category: dict[str, list[dict[str, Any]]],
        config: dict[str, Any],
        verbose: bool = False,
    ) -> None:
        self._source_dir = source_dir
        self._runtime_dir = runtime_dir
        self._mandates = mandates
        self._guidelines = guidelines
        self._guidelines_by_category = guidelines_by_category
        self._config = config
        self._verbose = verbose

    def _log(self, message: str) -> None:
        if self._verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    def _language_context_lines(self) -> str:
        """Build the language-context bullet list for README sections."""
        language_context = self._config.get("language_context", {})
        locale = self._config.get("locale")
        docs_language = self._config.get("docs_language")
        docs_locale = self._config.get("docs_locale")
        lines = []
        if locale:
            lines.append(f"- Interaction locale: {locale}")
        if docs_language:
            lines.append(f"- Docs language: {docs_language}")
        if docs_locale:
            lines.append(f"- Docs locale: {docs_locale}")
        if not isinstance(language_context, dict) or not language_context:
            return (
                "\n".join(lines)
                + ("\n" if lines else "")
                + "- No wizard language preference context was captured.\n"
            )
        labels = {
            "preferred_human_language": "Human",
            "preferred_chat_language": "Chat",
            "preferred_ui_language": "UI",
            "preferred_local_docs_language": "Local docs",
        }
        for key, label in labels.items():
            value = language_context.get(key)
            if value:
                lines.append(f"- {label}: {value}")
        return "\n".join(lines) + ("\n" if lines else "")

    def _guideline_category_block(self) -> str:
        """Return directory-tree lines for guideline categories."""
        if not self._guidelines_by_category:
            return "    (rendered by category when generated)\n"
        lines = []
        for category in sorted(self._guidelines_by_category.keys()):
            lines.append(f"    {category}.md")
        lines[-1] = lines[-1].replace("", "", 1)
        return "\n".join(lines) + "\n"

    def _guideline_read_examples(self) -> str:
        """Return example `cat` commands for the first few guideline categories."""
        if not self._guidelines_by_category:
            return "# No rendered category files available yet\ncat .providence/source/guidelines.dsl\n"
        return (
            "\n".join(
                f"cat .providence/source/guidelines/{category}.md"
                for category in sorted(self._guidelines_by_category.keys())[:3]
            )
            + "\n"
        )

    def _runtime_guideline_load_snippet(self) -> str:
        """Return the Python snippet that loads guidelines by category."""
        if not self._guidelines_by_category:
            return "    guidelines = {'dsl': read_file('.providence/source/guidelines.dsl')}\n"
        categories = ", ".join(
            repr(category) for category in sorted(self._guidelines_by_category.keys())
        )
        return (
            "    guidelines = {}\n"
            f"    for category in [{categories}]:\n"
            "        guidelines[category] = read_file(f'.providence/source/guidelines/{category}.md')\n"
        )

    def generate_source_readme(self) -> bool:
        """Write .providence/source/README.md; return True on success."""
        self._log("Generating .providence/source/README.md")
        try:
            categories_list = "\n".join(
                f"- {cat.title()}"
                for cat in sorted(self._guidelines_by_category.keys())
            )
            content = build_source_readme(
                generated_at=datetime.now().isoformat(),
                language=self._config.get("language", "Python"),
                adoption_level=self._config.get("adoption_level", "FULL"),
                guideline_category_block=self._guideline_category_block(),
                guideline_read_examples=self._guideline_read_examples(),
                language_context_lines=self._language_context_lines(),
                categories_list=categories_list,
                mandate_count=len(self._mandates),
                guideline_count=len(self._guidelines),
            )
            with open(self._source_dir / "README.md", "w", encoding="utf-8") as f:
                f.write(content)
            self._log("Generated .providence/source/README.md")
            return True
        except Exception as e:
            print(f"   Failed to generate source README: {e}")  # noqa: T201
            return False

    def generate_runtime_readme(self) -> bool:
        """Write .providence/runtime/README.md; return True on success."""
        self._log("Generating .providence/runtime/README.md")
        try:
            content = build_runtime_readme(
                generated_at=datetime.now().isoformat(),
                language_context_lines=self._language_context_lines(),
                runtime_guideline_load_snippet=self._runtime_guideline_load_snippet(),
            )
            with open(self._runtime_dir / "README.md", "w", encoding="utf-8") as f:
                f.write(content)
            self._log("Generated .providence/runtime/README.md")
            return True
        except Exception as e:
            print(f"   Failed to generate runtime README: {e}")  # noqa: T201
            return False
