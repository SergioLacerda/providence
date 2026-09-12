"""Tests for the providence_core package public API boundary."""

from __future__ import annotations

import importlib

import pytest

import providence_core

pytestmark = pytest.mark.unit


def test_public_api_lazy_exports_resolve() -> None:
    assert (
        providence_core.DeploymentManager
        is importlib.import_module(
            "providence_core.deployment_manager"
        ).DeploymentManager
    )
    assert (
        providence_core.GovernanceOrchestrator
        is importlib.import_module(
            "providence_core.governance_orchestrator"
        ).GovernanceOrchestrator
    )


def test_public_api_missing_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="has no attribute 'missing'"):
        providence_core.__getattr__("missing")
