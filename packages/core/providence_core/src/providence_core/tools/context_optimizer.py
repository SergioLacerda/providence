"""Context Optimizer."""

from pathlib import Path
from typing import Any

import yaml

from providence_core.utils.text_io import read_text_utf8


class ContextOptimizer:
    """ContextOptimizer."""

    def __init__(self, rules_path: str) -> None:
        self.rules: dict[str, Any] = yaml.safe_load(read_text_utf8(Path(rules_path)))

    def classify_task(self, task: str) -> str:
        """Classify task complexity into PATH A, B, or C (O2).

        PATH A: Simple, low-risk (help, docs, single-file fix).
        PATH B: Feature development, refactoring (multi-file).
        PATH C: Architectural changes, high complexity (decomposition required).
        """
        task = task.lower().strip()

        # PATH C: High complexity keywords or length
        complex_keywords = {
            "architect",
            "migration",
            "refactor core",
            "paradigm",
            "decouple",
        }
        if any(kw in task for kw in complex_keywords) or len(task) > 300:
            return "PATH C"

        # PATH B: Moderate complexity
        medium_keywords = {
            "implement",
            "add feature",
            "create module",
            "test suite",
            "refactor",
        }
        if any(kw in task for kw in medium_keywords) or len(task) > 100:
            return "PATH B"

        # PATH A: Simple
        return "PATH A"

    def select_specs(self, task_type: str) -> list[str]:
        """Select Specs."""
        mapping = {
            "PATH A": ["architecture.md"],
            "PATH B": ["feature-template.md", "conventions.md", "architecture.md"],
            "PATH C": ["architecture.md", "contracts.md", "decision-log.md"],
        }
        return mapping.get(task_type, ["architecture.md"])

    def load_specs(self, selected_files: list[str]) -> list[str]:
        """Load Specs."""
        base = Path("docs/ia")
        content: list[str] = []

        for file in base.rglob("*.md"):
            if file.name in selected_files:
                content.append(read_text_utf8(file))

        return content

    def prune(self, contents: list[str]) -> list[str]:
        """Prune."""
        pruned: list[str] = []
        for c in contents:
            lines = c.splitlines()

            # remove verbose sections (heurística simples)
            filtered = [
                line
                for line in lines
                if len(line.strip()) < 200 and not line.lower().startswith("example")
            ]

            pruned.append("\n".join(filtered[:200]))  # limite por doc

        return pruned

    def assemble(self, pruned_contents: list[str]) -> str:
        """Assemble."""
        return "\n\n".join(pruned_contents)

    def optimize(self, task: str) -> str:
        """Optimize."""
        task_type = self.classify_task(task)
        selected = self.select_specs(task_type)
        raw = self.load_specs(selected)
        pruned = self.prune(raw)
        return self.assemble(pruned)


if __name__ == "__main__":
    optimizer = ContextOptimizer("docs/ia/governance/canonical_rules.yaml")

    task = "analyze retrieval implementation vs spec"
    context = optimizer.optimize(task)

    print("=== OPTIMIZED CONTEXT ===")  # noqa: T201
    print(context[:2000])  # noqa: T201
