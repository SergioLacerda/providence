"""Tests for check_module_available."""

from __future__ import annotations

import sys

import pytest

from providence_core.utils.process import check_module_available

pytestmark = pytest.mark.unit


def test_check_module_available_for_installed_module() -> None:
    """A module that is importable returns True."""
    assert check_module_available(sys.executable, "sys") is True


def test_check_module_available_for_missing_module() -> None:
    """A module that cannot be imported returns False."""
    assert check_module_available(sys.executable, "this_module_does_not_exist") is False
