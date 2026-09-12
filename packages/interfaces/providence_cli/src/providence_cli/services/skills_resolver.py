"""Adapter generation and seed registry helpers for skills bootstrap."""

from __future__ import annotations

from pathlib import Path

from providence_cli.services.skills_seed_reconciler import (
    _read_registry_ids,
    _reconcile_root_seed_artifacts,
)

__all__ = ["_generate_adapters", "_read_registry_ids", "_reconcile_root_seed_artifacts"]


def _generate_adapters(output_base: Path) -> tuple[int, str | None]:
    try:
        from providence_adapters.adapter_generator import AdapterGenerator

        adapter_results = AdapterGenerator().generate(output_dir=output_base)
        return len(adapter_results), None
    except Exception as exc:
        return 0, str(exc)
