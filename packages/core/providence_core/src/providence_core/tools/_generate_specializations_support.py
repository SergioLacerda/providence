from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from _generate_constitution_template import generate_constitution_specialization
from _generate_constitution_template_tail import (
    generate_constitution_specialization_tail,
)
from _generate_ia_rules_template import generate_ia_rules_specialization


def load_config(project_name: str) -> dict[str, Any] | None:
    config_path = Path(f"docs/ia/custom/{project_name}/SPECIALIZATIONS_CONFIG.md")
    if not config_path.exists():
        print(f"❌ ERROR: Config not found at {config_path}")  # noqa: T201
        return None
    config = {"PROJECT_NAME": project_name, "GENERATED_AT": datetime.now().isoformat()}
    with open(config_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if "=" in line and not line.startswith("#") and not line.startswith("```"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip('"')
    return config


def validate_config(config: dict[str, Any]) -> bool:
    required = [
        "PROJECT_NAME",
        "MAX_CONCURRENT_ENTITIES",
        "LANGUAGE",
        "ASYNC_FRAMEWORK",
    ]
    missing = [key for key in required if key not in config]
    if missing:
        print(f"❌ ERROR: Missing required config fields: {missing}")  # noqa: T201
        return False
    return True


def create_specializations_dir(project: str) -> Path:
    spec_dir = Path(f"docs/ia/custom/{project}/SPECIALIZATIONS")
    spec_dir.mkdir(parents=True, exist_ok=True)
    return spec_dir


def _write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"⚠️  File exists: {path} (use --force to overwrite)")  # noqa: T201
        return
    path.write_text(content, encoding="utf-8")
    print(f"✅ Generated: {path}")  # noqa: T201


def write_specialization_files(
    project: str, config: dict[str, Any], force: bool = False
) -> bool:
    spec_dir = create_specializations_dir(project)
    _write_file(
        spec_dir / f"constitution-{project}-specific.md",
        generate_constitution_specialization(config)
        + generate_constitution_specialization_tail(config),
        force,
    )
    _write_file(
        spec_dir / f"ia-rules-{project}-specific.md",
        generate_ia_rules_specialization(config),
        force,
    )
    return True
