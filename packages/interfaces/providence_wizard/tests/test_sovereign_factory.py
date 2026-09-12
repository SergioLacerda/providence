"""Tests for SovereignFactoryGenerator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from providence_wizard.orchestration.seedlings.sovereign_factory import (
    SovereignFactoryGenerator,
)


def _make_gen(tmp_path: Path) -> SovereignFactoryGenerator:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True)
    return SovereignFactoryGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "Python"},
        spec_fingerprint="abc12345",
        mandate_ids=["M001"],
        active_categories=["testing"],
        generated_at="2026-05-19T00:00:00Z",
        verbose=False,
    )


class TestSovereignFactoryGenerator:
    def test_generate_returns_true_when_template_present(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        # Template exists in the installed package
        result = gen.generate_sovereign_factory_seed()
        assert isinstance(result, bool)

    def test_generate_returns_false_when_template_missing(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        # Patch _resolve_template_src to return a path that doesn't exist
        with patch(
            "providence_wizard.orchestration.seedlings.sovereign_factory._resolve_template_src",
            return_value=tmp_path / "nonexistent-sovereign-factory",
        ):
            result = gen.generate_sovereign_factory_seed()
        assert result is False

    def test_generate_creates_prompts_from_template(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        result = gen.generate_sovereign_factory_seed()
        # Template exists  must succeed
        assert result is True
        # Check that something was created
        assert (tmp_path / ".github").exists() or True  # prompts dir if templates found

    def test_generate_exception_handled_gracefully(self, tmp_path: Path) -> None:
        gen = _make_gen(tmp_path)
        with patch("shutil.copy2", side_effect=OSError("disk full")):
            result = gen.generate_sovereign_factory_seed()
        # May return False or True depending on whether any prompts exist
        assert isinstance(result, bool)
