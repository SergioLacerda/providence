"""Patterns for time-related fields: ISO 8601, Unix timestamps, durations, and dates."""

from providence_telemetry.types import PatternDef

TEMPORAL_PATTERNS: dict[str, PatternDef] = {
    "TS001": {
        "name": "ISO 8601 Timestamp",
        "regex": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})?$",
        "fields": ["timestamp", "created_at", "updated_at", "time", "date"],
        "compression_ratio": 0.15,
        "frequency": 0.95,
    },
    "TS002": {
        "name": "Unix Timestamp",
        "regex": r"^\d{10}(?:\.\d+)?$",
        "fields": ["unix_time", "epoch", "timestamp_ms"],
        "compression_ratio": 0.12,
        "frequency": 0.60,
    },
    "TS003": {
        "name": "Duration (milliseconds)",
        "regex": r"^\d+ms$",
        "fields": ["duration", "latency", "response_time", "elapsed"],
        "compression_ratio": 0.10,
        "frequency": 0.80,
    },
    "TS004": {
        "name": "Date String (YYYY-MM-DD)",
        "regex": r"^\d{4}-\d{2}-\d{2}$",
        "fields": ["date", "birth_date", "effective_date"],
        "compression_ratio": 0.08,
        "frequency": 0.40,
    },
    "TS005": {
        "name": "Time String (HH:MM:SS)",
        "regex": r"^\d{2}:\d{2}:\d{2}$",
        "fields": ["time", "start_time", "end_time"],
        "compression_ratio": 0.08,
        "frequency": 0.35,
    },
}
