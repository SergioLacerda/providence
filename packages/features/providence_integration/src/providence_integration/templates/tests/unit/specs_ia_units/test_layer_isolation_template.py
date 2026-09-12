"""
Template: Layer Isolation Compliance Tests

COPY THIS FILE TO: tests/unit/specs_ia_units/test_layer_isolation.py

Replace [project_name] with your project's actual package name.
"""

from pathlib import Path

import pytest


class TestLayerIsolation:
    """RULE 1: Domain layer never imports infrastructure or frameworks."""

    def test_domain_never_imports_infrastructure(self) -> None:
        """Domain layer cannot import infrastructure module."""
        domain_files = Path("src/[project_name]/domain").rglob("*.py")

        for file in domain_files:
            if file.name.startswith("__"):
                continue
            content = file.read_text(encoding="utf-8")

            # Check for infrastructure imports
            assert "from src.[project_name].infrastructure" not in content, (
                f"{file}: domain imports infrastructure (Rule 1 violation)"
            )
            assert "import src.[project_name].infrastructure" not in content, (
                f"{file}: domain imports infrastructure (Rule 1 violation)"
            )

    def test_domain_never_imports_frameworks(self) -> None:
        """Domain layer cannot import any web framework."""
        domain_files = Path("src/[project_name]/domain").rglob("*.py")
        forbidden_frameworks = [
            "from fastapi",
            "import fastapi",
            "from flask",
            "import flask",
            "from django",
            "import django",
            "from starlette",
            "import starlette",
        ]

        for file in domain_files:
            if file.name.startswith("__"):
                continue
            content = file.read_text(encoding="utf-8").lower()

            for framework in forbidden_frameworks:
                assert framework not in content, (
                    f"{file}: domain imports framework {framework.split()[-1]} (Rule 1 violation)"
                )

    def test_application_uses_ports_not_infrastructure(self) -> None:
        """Application layer must use ports (abstract), not direct infrastructure."""
        app_files = Path("src/[project_name]/application").rglob("*.py")

        for file in app_files:
            if file.name.startswith("__"):
                continue
            content = file.read_text(encoding="utf-8")

            # If file mentions "storage", it should use StoragePort, not direct implementation
            if "storage" in content.lower() and "Storage" in content:
                # Check it's using port, not concrete implementation
                has_port_reference = (
                    "StoragePort" in content
                    or "from src.[project_name].domain.ports" in content
                )
                has_direct_import = "from src.[project_name].infrastructure" in content

                assert not (has_direct_import and not has_port_reference), (
                    f"{file}: storage access should use StoragePort (abstract), not direct infrastructure"
                )

    def test_interfaces_layer_imports_domain_only(self) -> None:
        """Interfaces layer can import domain and usecases only."""
        if not Path("src/[project_name]/interfaces").exists():
            pytest.skip("Project doesn't have interfaces layer")

        interfaces_files = Path("src/[project_name]/interfaces").rglob("*.py")

        for file in interfaces_files:
            if file.name.startswith("__"):
                continue
            content = file.read_text(encoding="utf-8")

            # Interfaces should not directly import infrastructure
            assert "from src.[project_name].infrastructure" not in content, (
                f"{file}: interfaces imports infrastructure directly (should use application layer)"
            )

    def test_frameworks_only_wires_adapters(self) -> None:
        """Frameworks layer should only contain wiring, not business logic."""
        if not Path("src/[project_name]/frameworks").exists():
            return

        frameworks_files = Path("src/[project_name]/frameworks").rglob("*.py")

        for file in frameworks_files:
            if file.name.startswith("__"):
                continue
            # Frameworks layer is okay - it's expected to import everything for wiring
            # This is a placeholder for any framework-specific rules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
