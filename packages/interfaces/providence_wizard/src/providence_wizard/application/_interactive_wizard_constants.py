"""Static configuration values for the interactive wizard flow."""

from __future__ import annotations

from providence_wizard.constants import PHASE2_INPUT_DIRNAME, RUNTIME_DIRNAME

__all__ = [
    "_ENFORCEMENT_CHOICES",
    "_ENFORCEMENT_MAP",
    "_FINAL_TEMPLATE_AUDIT_FILES",
    "_FINAL_TEMPLATE_COMPILED_FILES",
    "_FINAL_TEMPLATE_CONTEXT_CACHE_FILE",
    "_FINAL_TEMPLATE_DIRNAME",
    "_FINAL_TEMPLATE_MANIFEST_FILE",
    "_HANDSHAKE_CHOICES",
    "_HANDSHAKE_MAP",
    "_INTERACTION_LANGUAGE_CHOICES",
    "_LOCAL_DOCS_LANGUAGE_CHOICES",
    "_LOCALE_BY_LANGUAGE",
    "_ONBOARDING_BASELINE_GUIDELINES",
    "_ONBOARDING_BASELINE_MANDATE",
    "_TEMP_BUILD_DIRS",
    "_TEMP_COMPILED_DIRS",
]

_PHASE2_INPUT_DIRNAME = PHASE2_INPUT_DIRNAME
_PHASE1_CHOICES_DIRNAME = "phase-1-choices"
_FINAL_TEMPLATE_DIRNAME = "final-template"
_FINAL_TEMPLATE_COMPILED_FILES = (
    "governance-core.compiled.msgpack",
    "governance-client-template.compiled.msgpack",
)
_FINAL_TEMPLATE_AUDIT_FILES = (
    "metadata-core.json",
    "metadata-client-template.json",
)
_FINAL_TEMPLATE_MANIFEST_FILE = "DEPLOYMENT_MANIFEST.json"
_FINAL_TEMPLATE_CONTEXT_CACHE_FILE = f"{RUNTIME_DIRNAME}/runtime/.providence-cache.md"
_TEMP_BUILD_DIRS = ("docs-meta", _PHASE1_CHOICES_DIRNAME, _PHASE2_INPUT_DIRNAME)
_TEMP_COMPILED_DIRS = (
    RUNTIME_DIRNAME,
    ".github",
    ".vscode",
    ".cursor",
    ".claude",
    ".gemini",
    ".ai",
    ".ia",
)
_ONBOARDING_BASELINE_MANDATE = """# M001: Bootstrap Governance Baseline

Initial mandate placeholder generated during first onboarding.
Customize this file in Phase 2.
"""
_ONBOARDING_BASELINE_GUIDELINES = """guideline G001 {
    title: "Bootstrap guideline"
    description: "Initial guideline placeholder generated during first onboarding."
    type: "GUIDELINE"
    category: "core"
}
"""
_ENFORCEMENT_CHOICES = ["Sem Alertas", "Alertas", "Bloquear"]
_ENFORCEMENT_MAP = {
    "Sem Alertas": "silent_mode",
    "Alertas": "warn_mode",
    "Bloquear": "strict_mode",
}
_INTERACTION_LANGUAGE_CHOICES = ["English", "Portugus (Brasil)"]
_LOCAL_DOCS_LANGUAGE_CHOICES = [
    "English",
    "Portugus (Brasil)",
    "Same as interaction",
]
_LOCALE_BY_LANGUAGE = {
    "English": "en",
    "Portugus (Brasil)": "pt-BR",
}
_HANDSHAKE_CHOICES = [
    "Todo prompt filtrado pela governana (hook)",
    "Governana seletiva (slash commands, CLI)",
]
_HANDSHAKE_MAP = {
    "Todo prompt filtrado pela governana (hook)": "hook",
    "Governana seletiva (slash commands, CLI)": "standard",
}
