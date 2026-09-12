from pathlib import Path


def get_repo_root() -> Path:
    """Dynamically finds the repository root based on the location of this file."""
    # This file is located in tests/path_config.py
    # Repo root is 1 level up from tests/
    return Path(__file__).resolve().parents[1]


REPO_ROOT = get_repo_root()
CORE_DIR = REPO_ROOT / "packages"
SPEC_DIR = REPO_ROOT / "docs" / "spec"
DOCS_DIR = REPO_ROOT / "docs"
GENERATED_DIR = REPO_ROOT / "generated"
MASTER_GENERATED = GENERATED_DIR / "master"
CLIENT_GENERATED = GENERATED_DIR / "client"

# Internal Framework Paths
CORE = CORE_DIR / "core"
WIZARD = CORE_DIR / "interfaces" / "providence_wizard"

# Decision and Spec Paths
CANONICAL_SPEC = SPEC_DIR / "canonical"
ADR_CANONICAL = CANONICAL_SPEC / "decisions"
ADR_ARCH = SPEC_DIR / "decisions"
ADR_DIR = ADR_ARCH  # Default to new architecture path
QUIZ_TRACKING = REPO_ROOT / "docs" / "project-status" / "_quiz_tracking.json"
