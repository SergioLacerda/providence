"""Golden-output test for build_verification_script.

Guards the structure-refactor split of _verification_script_template.py into
_verification_script_checks.py / _verification_script_runner.py (see
.analysis/pending/wizard-structure-refactor-20260708/)  output must stay
byte-identical across the split, and the generated verify.py source must
remain syntactically valid Python.
"""

from __future__ import annotations

import pytest

from providence_wizard.templates._verification_script_template import (
    build_verification_script,
)

pytestmark = pytest.mark.unit

_MANDATE_IDS_STR = "M001', 'M002', 'M003"


def test_build_verification_script_is_valid_python() -> None:
    output = build_verification_script(mandate_ids_str=_MANDATE_IDS_STR)
    compile(output, "<generated-verify.py>", "exec")


def test_build_verification_script_includes_all_methods() -> None:
    output = build_verification_script(mandate_ids_str=_MANDATE_IDS_STR)

    assert output.startswith("#!/usr/bin/env python3")
    assert output.rstrip().endswith("sys.exit(main())")
    for symbol in (
        "class GovernanceVerifier:",
        "def check_directory(self",
        "def check_file(self",
        "def check_seedling_loader(self",
        "def verify_mandates(self",
        "def run(self",
        "def main():",
        'if __name__ == "__main__":',
    ):
        assert symbol in output, f"missing: {symbol}"


def test_build_verification_script_interpolates_mandate_ids() -> None:
    output = build_verification_script(mandate_ids_str=_MANDATE_IDS_STR)
    assert f"expected = {{'{_MANDATE_IDS_STR}'}}" in output


def test_build_verification_script_preserves_literal_braces_in_fstrings() -> None:
    """The generated script's own f-strings (e.g. f"  {message}") must render
    with single literal braces, not the double-brace escaping used internally
    by this template's own f-string sections.
    """
    output = build_verification_script(mandate_ids_str=_MANDATE_IDS_STR)
    assert 'logger.info(f"  {message}")' in output
    assert "self.checks = {}" in output
    assert 'logger.info(f" Passed: {self.passed}")' in output
