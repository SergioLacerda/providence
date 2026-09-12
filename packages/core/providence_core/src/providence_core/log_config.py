"""Central structlog configuration for all sdd_* packages.

Call ``configure_logging()`` once at process startup (CLI entrypoint or
``__main__``).  All packages obtain a logger via::

    import structlog
    logger = structlog.get_logger(__name__)

No package configures structlog directly — they rely on this module.

Output format
-------------
- JSON when ``SDD_ENV=production`` or stdout is not a TTY.
- ConsoleRenderer (human-readable, coloured) otherwise.
"""

from __future__ import annotations

import os
import sys

import structlog

# Mutable container avoids the `global` keyword; CodeQL can verify the read/write.
_state: list[bool] = [False]


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog for the current process.

    Idempotent — safe to call multiple times; only the first call takes effect.
    """
    if _state[0]:
        return
    _state[0] = True

    _log_levels: dict[str, int] = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "WARN": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    is_production = os.environ.get("SDD_ENV", "").lower() == "production"
    is_tty = sys.stdout.isatty()
    use_json = is_production or not is_tty

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if use_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    numeric_level = _log_levels.get(level.upper(), 20)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
