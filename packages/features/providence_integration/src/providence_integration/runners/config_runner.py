"""Config Runner."""

import configparser
from pathlib import Path

from providence_integration.engine.types import ConfigValidateInputs, RuntimeContext


def run_config_validate(
    inputs: ConfigValidateInputs, context: RuntimeContext, spec_dir: Path
) -> None:
    """Run Config Validate."""
    del spec_dir
    working_dir = context.get("working_dir", Path.cwd())
    # Default to .providence/profile (replaces legacy .spec.config)
    config_file = working_dir / (inputs.file or ".providence/profile")

    if not config_file.exists():
        context["config"] = {}
        return

    parser = configparser.ConfigParser()
    parser.read(config_file)

    # Flatten all sections into a single dict
    config: dict[str, str] = {}
    for section in parser.sections():
        for key, value in parser.items(section):
            config[key] = value

    context["config"] = config
