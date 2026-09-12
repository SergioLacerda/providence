"""Template for the seedlings verify.py script."""

from __future__ import annotations

from ._verification_script_checks import (
    _check_seedling_loader_method,
    _verify_mandates_method,
)
from ._verification_script_runner import _main_and_entry_section, _run_method


def _header_and_basic_checks_section() -> str:
    return '''#!/usr/bin/env python3
"""Governance Activation Verification Script

This script verifies that governance seedlings are properly activated.

Usage:
    python3 verify.py
    python3 verify.py --verbose
"""

import json
import sys
from pathlib import Path


class GovernanceVerifier:
    """Verify governance activation status"""

    def __init__(self, project_root: Path = None, verbose: bool = False):
        self.project_root = project_root or Path.cwd()
        self.verbose = verbose
        self.checks = {}
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, message: str):
        if self.verbose:
            logger.info(f"  {message}")

    def check_directory(self, path: str, description: str) -> bool:
        full_path = self.project_root / path
        passed = full_path.exists() and full_path.is_dir()
        status = "" if passed else ""
        logger.info(f"  {status} {description}: {path}")
        self.checks[description] = "pass" if passed else "fail"
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        return passed

    def check_file(self, path: str, description: str, must_be_json: bool = False) -> bool:
        full_path = self.project_root / path
        exists = full_path.exists() and full_path.is_file()

        if not exists:
            logger.warning(f"   {description}: {path}")
            self.checks[description] = "fail"
            self.failed += 1
            return False

        if must_be_json:
            try:
                with open(full_path, "r") as f:
                    json.load(f)
                status = ""
                result = True
            except json.JSONDecodeError as e:
                status = ""
                result = False
                logger.info(f"  {status} {description} (Invalid JSON): {path}")
                self.failed += 1
                return False
        else:
            status = ""
            result = True

        logger.info(f"  {status} {description}: {path}")
        self.checks[description] = "pass"
        if result:
            self.passed += 1
        return result

'''


def build_verification_script(mandate_ids_str: str) -> str:
    """Render verify.py content."""
    return (
        _header_and_basic_checks_section()
        + _check_seedling_loader_method()
        + _verify_mandates_method(mandate_ids_str)
        + _run_method()
        + _main_and_entry_section()
    )
