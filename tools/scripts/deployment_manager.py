#!/usr/bin/env python3
"""
Providence Deployment Orchestrator (Wrapper)
Thin wrapper around providence_core.deployment_manager.
"""

import sys

try:
    from providence_core.utils.environment import get_sdd_paths
except ImportError:
    print("ERROR: Could not load providence environment utility.")
    sys.exit(1)


def main() -> int:
    paths = get_sdd_paths()

    # Bootstrap sys.path to find providence_core if not installed
    core_src = paths["core_pkg"] / "src"
    if core_src.exists() and str(core_src) not in sys.path:
        sys.path.insert(0, str(core_src))

    try:
        from providence_core.deployment_manager import DeploymentManager
    except ImportError as e:
        print(f"ERROR: Could not import DeploymentManager from providence_core: {e}")
        return 1

    # Initialize with repo root and execute
    manager = DeploymentManager(repo_root=str(paths["root"]))
    result = manager.deploy()

    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
