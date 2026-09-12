"""Tests for providence_core.log_config central configuration module."""

from __future__ import annotations

import io
import json
import sys

import pytest
import structlog

import providence_core.log_config as logging_mod


def _reset_structlog(monkeypatch) -> None:
    """Reset structlog and the _state flag between tests."""
    monkeypatch.setattr(logging_mod, "_state", [False])
    structlog.reset_defaults()


def test_configure_logging_json_when_production_env(monkeypatch) -> None:
    _reset_structlog(monkeypatch)
    monkeypatch.setenv("SDD_ENV", "production")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    logging_mod.configure_logging()

    buf = io.StringIO()
    logger = structlog.get_logger("test.json")
    with monkeypatch.context() as m:
        m.setattr("sys.stdout", buf)
        logger.info("hello", key="value")

    output = buf.getvalue().strip()
    assert output, "Expected log output"
    parsed = json.loads(output)
    assert parsed["key"] == "value"
    assert parsed["level"] == "info"


def test_configure_logging_non_tty_uses_json(monkeypatch) -> None:
    _reset_structlog(monkeypatch)
    monkeypatch.delenv("SDD_ENV", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    logging_mod.configure_logging()

    buf = io.StringIO()
    logger = structlog.get_logger("test.nontty")
    with monkeypatch.context() as m:
        m.setattr("sys.stdout", buf)
        logger.info("nontty_msg")

    output = buf.getvalue().strip()
    assert output
    parsed = json.loads(output)
    assert "level" in parsed


def test_configure_logging_idempotent(monkeypatch) -> None:
    _reset_structlog(monkeypatch)
    monkeypatch.setenv("SDD_ENV", "production")

    logging_mod.configure_logging()
    logging_mod.configure_logging()  # second call must not raise or reset config

    assert logging_mod._state[0] is True


def test_configure_logging_console_when_tty(monkeypatch) -> None:
    _reset_structlog(monkeypatch)
    monkeypatch.delenv("SDD_ENV", raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    logging_mod.configure_logging()

    buf = io.StringIO()
    logger = structlog.get_logger("test.tty")
    with monkeypatch.context() as m:
        m.setattr("sys.stdout", buf)
        logger.info("tty_msg")

    # ConsoleRenderer output is not valid JSON — just confirm no crash and output exists
    output = buf.getvalue()
    assert "tty_msg" in output
    with pytest.raises(json.JSONDecodeError):
        json.loads(output.strip())
