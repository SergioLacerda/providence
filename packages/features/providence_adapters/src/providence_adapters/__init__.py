"""Multi-agent adapter generation from SDD skills and commands."""

from .adapter_generator import AdapterGenerator, AdapterResult
from .claude import ClaudeStandaloneGenerator, ClaudeStandaloneResult
from .copilot import CopilotStandaloneGenerator, CopilotStandaloneResult
from .devin import DevinPluginGenerator, DevinPluginResult

__all__ = [
    "AdapterGenerator",
    "AdapterResult",
    "ClaudeStandaloneGenerator",
    "ClaudeStandaloneResult",
    "CopilotStandaloneGenerator",
    "CopilotStandaloneResult",
    "DevinPluginGenerator",
    "DevinPluginResult",
]
