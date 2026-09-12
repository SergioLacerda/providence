"""Patterns for infrastructure metadata: versions, service names, and cloud resource IDs."""

from providence_telemetry.types import PatternDef

METADATA_PATTERNS: dict[str, PatternDef] = {
    "META001": {
        "name": "Semantic Version",
        "regex": r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$",
        "fields": ["version", "app_version", "release"],
        "compression_ratio": 0.15,
        "frequency": 0.90,
    },
    "META002": {
        "name": "Service Name",
        "regex": r"^[a-z][a-z0-9-]{1,62}$",
        "fields": ["service", "service_name"],
        "compression_ratio": 0.12,
        "frequency": 0.85,
    },
    "META003": {
        "name": "Kubernetes Resource",
        "regex": r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
        "fields": ["pod", "deployment", "namespace"],
        "compression_ratio": 0.10,
        "frequency": 0.30,
    },
    "META004": {
        "name": "Container ID",
        "regex": r"^[a-f0-9]{12}$",
        "fields": ["container_id", "docker_id"],
        "compression_ratio": 0.20,
        "frequency": 0.20,
    },
    "META005": {
        "name": "User Agent",
        "regex": r"^(Mozilla|Chrome|Safari|Firefox).*",
        "fields": ["user_agent", "agent"],
        "compression_ratio": 0.28,
        "frequency": 0.50,
    },
    "META006": {
        "name": "GCP Project ID",
        "regex": r"^[a-z][a-z0-9-]{5,29}$",
        "fields": ["project_id", "gcp_project"],
        "compression_ratio": 0.12,
        "frequency": 0.40,
    },
    "META007": {
        "name": "AWS Account ID",
        "regex": r"^\d{12}$",
        "fields": ["account_id", "aws_account"],
        "compression_ratio": 0.06,
        "frequency": 0.30,
    },
}
