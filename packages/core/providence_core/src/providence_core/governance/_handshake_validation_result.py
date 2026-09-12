"""Handshake validation result model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationResult:
    name: str
    passed: bool
    message: str
    layer: str


def result(name: str, passed: bool, message: str, layer: str) -> ValidationResult:
    return ValidationResult(name=name, passed=passed, message=message, layer=layer)
