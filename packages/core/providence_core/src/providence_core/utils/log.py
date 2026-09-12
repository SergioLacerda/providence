"""Centralized logger factory for SDD packages.

Use this instead of calling logging.getLogger(__name__) directly so that
future changes to the logging backend (e.g., structlog) only require
updating this module.
"""

from __future__ import annotations

import logging as _stdlib_logging


def get_logger(name: str) -> _stdlib_logging.Logger:
    """Return a standard library logger for *name*.

    Usage::

        from providence_core.utils.log import get_logger
        logger = get_logger(__name__)
    """
    return _stdlib_logging.getLogger(name)
