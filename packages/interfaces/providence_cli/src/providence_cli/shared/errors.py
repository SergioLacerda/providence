"""Shared command errors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CliContractError(Exception):
    """Raised when command output violates canonical CLI contract."""

    reason_code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.reason_code}] {self.message}"
