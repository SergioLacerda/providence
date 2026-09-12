"""Template directory resolution for Phase 3."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

_LANGUAGE_DIRS: dict[str, str] = {
    "Python": "python",
    "Java": "java",
    "TypeScript": "js",
    "Go": "go",
}

_TEMPLATE_CANDIDATES = (
    (
        "packages",
        "interfaces",
        "providence_wizard",
        "src",
        "providence_wizard",
        "templates",
    ),
    ("packages", "wizard", "templates"),
)


def _find_templates_dir(repo_root: Path) -> Path | None:
    return next(
        (
            repo_root.joinpath(*parts)
            for parts in _TEMPLATE_CANDIDATES
            if repo_root.joinpath(*parts).exists()
        ),
        None,
    )


class TemplateLocator:
    """Resolve wizard template directories relative to a repo root."""

    def __init__(
        self,
        repo_root: Path,
        emitter: Callable[[str], None] | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._emit = emitter or print
        self.last_error: str | None = None

    def validate_template_root(self) -> bool:
        """Return True if the wizard templates directory exists under repo_root."""
        if _find_templates_dir(self._repo_root) is not None:
            return True
        candidates = [str(self._repo_root.joinpath(*p)) for p in _TEMPLATE_CANDIDATES]
        self.last_error = f"Template root not found. Tried: {', '.join(candidates)}"
        self._emit(f"   {self.last_error}")
        return False

    def resolve_language_dir(self, language: str) -> Path | None:
        """Return the language-specific template directory, or None if not found."""
        if not self.validate_template_root():
            return None
        language_dirname = _LANGUAGE_DIRS.get(language)
        if language_dirname is None:
            self.last_error = f"Unsupported language template mapping: {language}"
            self._emit(f"   {self.last_error}")
            return None
        templates_root = _find_templates_dir(self._repo_root)
        if templates_root is None:
            return None
        template_dir = templates_root / "languages" / language_dirname
        if template_dir.exists():
            return template_dir
        self.last_error = (
            f"Language template directory missing for {language}: {template_dir}"
        )
        self._emit(f"   {self.last_error}")
        return None
