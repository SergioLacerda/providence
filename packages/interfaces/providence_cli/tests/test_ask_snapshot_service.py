"""Tests for ask_snapshot compatibility wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def test_build_governed_ask_snapshot_delegates_to_ask_backend() -> None:
    from providence_cli.services.ask_snapshot import build_governed_ask_snapshot

    expected = {"workspace_root": Path("/tmp"), "fingerprint": "fp-1"}
    with patch(
        "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
        return_value=expected,
    ) as mock_fn:
        result = build_governed_ask_snapshot(
            query="test query",
            skill=None,
            organize_used=False,
            workspace_root=None,
            require_handshake=True,
        )

    mock_fn.assert_called_once_with(
        query="test query",
        skill=None,
        organize_used=False,
        workspace_root=None,
        require_handshake=True,
    )
    assert result is expected


def test_build_governed_ask_snapshot_passes_workspace_root() -> None:
    from providence_cli.services.ask_snapshot import build_governed_ask_snapshot

    root = Path("/some/workspace")
    with patch(
        "providence_cli.commands._ask_backend.build_governed_ask_snapshot",
        return_value={"workspace_root": root},
    ) as mock_fn:
        build_governed_ask_snapshot(
            query="query",
            skill="sdd-diagnose",
            organize_used=True,
            workspace_root=root,
            require_handshake=False,
        )

    call_kwargs = mock_fn.call_args[1]
    assert call_kwargs["workspace_root"] == root
    assert call_kwargs["skill"] == "sdd-diagnose"
    assert call_kwargs["organize_used"] is True
    assert call_kwargs["require_handshake"] is False
