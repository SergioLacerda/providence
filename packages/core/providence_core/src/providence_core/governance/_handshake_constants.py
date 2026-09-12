from __future__ import annotations

STATES = {
    "NOT_CONNECTED": {"emoji": "X", "description": "No governance detected"},
    "MISCONFIGURED": {"emoji": "!", "description": "Governance broken/invalid"},
    "NOT_INITIALIZED": {
        "emoji": "!",
        "description": "Setup incomplete (PHASE 0 needed)",
    },
    "PARTIAL": {"emoji": "~", "description": "Runtime incomplete"},
    "HEALTHY": {"emoji": "+", "description": "Fully operational"},
}

ACTIONS = {
    "NOT_CONNECTED": ["proceed_normally"],
    "MISCONFIGURED": ["warn_user", "suggest_review"],
    "NOT_INITIALIZED": ["suggest_phase_0_setup"],
    "PARTIAL": ["suggest_fix"],
    "HEALTHY": ["proceed_silently"],
}
