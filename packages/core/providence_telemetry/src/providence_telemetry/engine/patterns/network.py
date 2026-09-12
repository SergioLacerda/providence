"""Patterns for network fields: IPs, URLs, ports, emails, domains, and MAC addresses."""

from providence_telemetry.types import PatternDef

NETWORK_PATTERNS: dict[str, PatternDef] = {
    "NET001": {
        "name": "IPv4 Address",
        "regex": r"^(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$",
        "fields": ["ip", "ip_address", "client_ip", "server_ip", "source_ip"],
        "compression_ratio": 0.20,
        "frequency": 0.70,
    },
    "NET002": {
        "name": "IPv6 Address",
        "regex": r"^([0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}$",
        "fields": ["ipv6", "ipv6_address"],
        "compression_ratio": 0.35,
        "frequency": 0.15,
    },
    "NET003": {
        "name": "Port Number",
        "regex": r"^\d{1,5}$",
        "fields": ["port", "server_port"],
        "compression_ratio": 0.05,
        "frequency": 0.50,
    },
    "NET004": {
        "name": "HTTP URL",
        "regex": r"^https?://[^\s]+$",
        "fields": ["url", "endpoint", "path"],
        "compression_ratio": 0.25,
        "frequency": 0.60,
    },
    "NET005": {
        "name": "Email Address",
        "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "fields": ["email", "user_email", "contact"],
        "compression_ratio": 0.30,
        "frequency": 0.20,
    },
    "NET006": {
        "name": "Domain Name",
        "regex": r"^([a-z0-9]+-?)*[a-z0-9]+(\.[a-z]{2,})+$",
        "fields": ["domain", "hostname"],
        "compression_ratio": 0.18,
        "frequency": 0.45,
    },
    "NET007": {
        "name": "MAC Address",
        "regex": r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
        "fields": ["mac_address", "hardware_address"],
        "compression_ratio": 0.22,
        "frequency": 0.05,
    },
    "NET008": {
        "name": "CIDR Notation",
        "regex": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$",
        "fields": ["cidr", "network", "subnet"],
        "compression_ratio": 0.20,
        "frequency": 0.10,
    },
}
