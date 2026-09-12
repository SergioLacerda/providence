"""Patterns for error, warning, and info log message fields."""

from providence_telemetry.types import PatternDef

MESSAGE_PATTERNS: dict[str, PatternDef] = {
    "MSG001": {
        "name": "Exception Stack Trace",
        "regex": r"^(Traceback|Error:|Exception:|\s+at\s+).*",
        "fields": ["error", "exception", "traceback"],
        "compression_ratio": 0.40,
        "frequency": 0.10,
    },
    "MSG002": {
        "name": "Database Connection Error",
        "regex": r"^(Connection|Database|SQL|Query).*",
        "fields": ["error_message", "error"],
        "compression_ratio": 0.25,
        "frequency": 0.08,
    },
    "MSG003": {
        "name": "Timeout Error",
        "regex": r"(timeout|timed out|deadline exceeded)",
        "fields": ["error_message", "error"],
        "compression_ratio": 0.20,
        "frequency": 0.15,
    },
    "MSG004": {
        "name": "Authorization Error",
        "regex": r"(unauthorized|forbidden|permission denied|access denied)",
        "fields": ["error_message", "error"],
        "compression_ratio": 0.22,
        "frequency": 0.12,
    },
    "MSG005": {
        "name": "Success Message",
        "regex": r"^(Success|OK|Created|Accepted|Completed).*",
        "fields": ["message", "status_message"],
        "compression_ratio": 0.12,
        "frequency": 0.40,
    },
    "MSG006": {
        "name": "Warning Message",
        "regex": r"^(Warning|Deprecated|Experimental).*",
        "fields": ["message", "warning"],
        "compression_ratio": 0.15,
        "frequency": 0.20,
    },
    "MSG007": {
        "name": "Info Message",
        "regex": r"^(Info|Initializing|Starting|Loading).*",
        "fields": ["message", "info"],
        "compression_ratio": 0.10,
        "frequency": 0.55,
    },
    "MSG008": {
        "name": "Debug Message",
        "regex": r"^(Debug|Trace|Step).*",
        "fields": ["message", "debug"],
        "compression_ratio": 0.12,
        "frequency": 0.25,
    },
}
