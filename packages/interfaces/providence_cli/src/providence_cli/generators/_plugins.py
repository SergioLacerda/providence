"""Plugin registry generator  creates .providence/plugins/ with registry.yaml and Strategist entry."""

from pathlib import Path
from typing import Any

_STRATEGIST_ENTRY: dict[str, Any] = {
    "id": "strategist",
    "type": "analysis_orchestrator",
    "version": "1.0.0",
    "status": "active",
    "entrypoint": "/strategist",
    "contract": ".providence/contracts/analysis-provider.schema.yaml",
    "sdd_injection": {
        "base_path": ".providence/analysis",
        "execution_provider": "sdd-ask",
        "approval_gate": "required",
        "knowledge_paths": [
            ".providence/docs",
            ".providence/source/mandates",
        ],
        "governance_context": {
            "workspace_version": "3.0",
            "active_mandates": ["M001", "M005", "M010", "M017"],
        },
    },
    "forbidden": [
        "write artifacts outside sdd_injection.base_path",
        "invoke execution_provider other than sdd-ask",
        "skip approval_gate",
    ],
}


def generate_plugins_registry(
    output_dir: str, _config: dict[str, Any]
) -> dict[str, Any]:
    """Generate .providence/plugins/registry.yaml with schema and Strategist plugin entry.

    Args:
        output_dir: Base output directory (workspace root)
        config: Governance configuration dict

    Returns:
        Dict with registry_path and plugin_count.
    """
    try:
        import yaml
    except ImportError:
        return {
            "registry_path": None,
            "plugin_count": 0,
            "error": "PyYAML not available",
        }

    output_path = Path(output_dir)
    plugins_dir = output_path / ".providence" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    registry: dict[str, Any] = {
        "schema_version": "1.0.0",
        "policies": {
            "preferred_type": "analysis_orchestrator",
            "conflict_resolution": "first_active",
            "m017_enforcement": "block",
        },
        "plugins": [_STRATEGIST_ENTRY],
    }

    registry_path = plugins_dir / "registry.yaml"
    registry_path.write_text(
        yaml.dump(
            registry, default_flow_style=False, sort_keys=False, allow_unicode=True
        ),
        encoding="utf-8",
    )

    return {
        "registry_path": registry_path.as_posix(),
        "plugin_count": len(registry["plugins"]),
    }
