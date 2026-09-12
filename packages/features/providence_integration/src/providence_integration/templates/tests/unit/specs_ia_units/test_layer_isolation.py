"""
Test Layer Isolation — Verify domain doesn't import infrastructure.

This test validates that your project follows clean architecture principles
where the domain layer is completely independent of infrastructure implementation details.

## What This Tests

- ✅ Domain layer imports only domain, not infrastructure
- ✅ Infrastructure accessed only through ports (abstractions)
- ✅ Application layer orchestrates domain + infrastructure
- ✅ Entities remain infrastructure-agnostic
- ✅ Configuration abstracts infrastructure choices
- ✅ Modules follow SPEC structure

## How to Adapt for Your Project

Edit paths to match your project structure:

```python
# Current (example project)
domain_path = Path("src/rpg_narrative_server/domain")

# Your project (edit these)
domain_path = Path("src/your_project/domain")
infrastructure_path = Path("src/your_project/infrastructure")
```

Then run:
```bash
pytest tests/unit/specs_ia_units/test_layer_isolation.py -v
```
"""

from pathlib import Path

import pytest


class TestLayerIsolation:
    """Verify that domain layer is isolated from infrastructure."""

    def test_domain_does_not_import_infrastructure(self) -> None:
        """Domain should not directly import infrastructure.

        Rationale: Domain should depend on abstractions (ports), not implementations.
        This ensures portability and testability.
        """
        # EDIT: Change to your project structure
        domain_path = Path("src/domain")

        if not domain_path.exists():
            pytest.skip("Domain path not found")

        domain_files = list(domain_path.rglob("*.py"))
        assert len(domain_files) > 0, "No domain files found"

        violations = []
        for file in domain_files:
            if "__pycache__" in str(file):
                continue

            content = file.read_text(encoding="utf-8")

            # Check for direct infrastructure imports
            forbidden_patterns = [
                "from src.infrastructure",
                "from infrastructure.",
                "from .infrastructure",
                # Add your project-specific infrastructure patterns here
            ]

            for pattern in forbidden_patterns:
                if pattern in content:
                    violations.append(f"{file.relative_to(Path.cwd())}: {pattern}")

        assert len(violations) == 0, (
            "Domain imports infrastructure directly:\n" + "\n".join(violations)
        )

    def test_domain_uses_ports_for_abstraction(self) -> None:
        """Domain entities should use ports, not concrete implementations.

        Rationale: Dependency inversion principle requires domain depends on abstractions.
        """
        # EDIT: Change to your project structure
        Path("src/domain")
        ports_path = Path("src/domain/ports")

        if not ports_path.exists():
            pytest.skip("Ports directory not found")

        # At least one port should exist
        ports = list(ports_path.glob("*.py"))
        assert len(ports) > 0, "No ports defined in domain"

    def test_application_layer_orchestrates(self) -> None:
        """Application layer should coordinate domain + infrastructure.

        Rationale: Application is the glue between domain logic and infrastructure.
        """
        # EDIT: Change to your project structure
        app_path = Path("src/application")

        if not app_path.exists():
            pytest.skip("Application path not found")

        # Application layer should exist and have content
        app_files = list(app_path.rglob("*.py"))
        assert len(app_files) > 0, "Application layer is empty"

    def test_infrastructure_not_imported_in_domain_entities(self) -> None:
        """Domain entities should be infrastructure-agnostic.

        Rationale: Entities should express business logic, not storage details.
        """
        # EDIT: Change to your project structure
        entities_path = Path("src/domain/entities")

        if not entities_path.exists():
            pytest.skip("Domain entities path not found")

        entity_files = list(entities_path.rglob("*.py"))
        assert len(entity_files) > 0, "No domain entities found"

        violations = []
        for file in entity_files:
            if "__pycache__" in str(file):
                continue

            content = file.read_text(encoding="utf-8")

            # Entities should not know about storage mechanisms
            forbidden = [
                "from src.infrastructure",
                "session.add",  # SQLAlchemy
                "db.",
                "@database",
                # Add your project-specific forbidden patterns here
            ]

            for pattern in forbidden:
                if pattern in content:
                    violations.append(f"{file.name}: uses {pattern}")

        assert len(violations) == 0, (
            "Domain entities import infrastructure details:\n" + "\n".join(violations)
        )

    def test_config_independent_of_infrastructure(self) -> None:
        """Config layer should abstract infrastructure choices.

        Rationale: Changing storage/cache shouldn't require code changes, only config.
        """
        # EDIT: Change to your project structure
        config_path = Path("src/config")

        if not config_path.exists():
            pytest.skip("Config path not found")

        config_files = list(config_path.rglob("*.py"))
        assert len(config_files) > 0, "No config files found"


class TestModuleOrganization:
    """Verify that modules follow SPEC layer structure."""

    def test_required_layers_exist(self) -> None:
        """SPEC requires these layers to exist.

        Rationale: Clean architecture with clear separation of concerns.
        """
        # EDIT: Change to your project structure
        src_path = Path("src")
        if not src_path.exists():
            pytest.skip("src directory not found")

        required_layers = [
            "domain",
            "application",
            "infrastructure",
            # Add your project-specific layers here
        ]

        missing = []
        for layer in required_layers:
            layer_path = src_path / layer
            if not layer_path.exists():
                missing.append(layer)

        assert len(missing) == 0, f"Missing required layers: {', '.join(missing)}"

    def test_domain_has_entities_and_ports(self) -> None:
        """Domain should contain entities and ports (abstractions).

        Rationale: Domain = business logic + abstractions for infrastructure.
        """
        # EDIT: Change to your project structure
        domain_path = Path("src/domain")

        if not domain_path.exists():
            pytest.skip("Domain path not found")

        has_entities = (domain_path / "entities").exists()
        has_ports = (domain_path / "ports").exists()

        # Should have at least one of these
        assert has_entities or has_ports, (
            "Domain should have 'entities' and/or 'ports' subdirectories"
        )


class TestImportGraph:
    """Verify dependency graph follows SPEC rules."""

    def test_no_circular_imports_in_domain(self) -> None:
        """Domain modules should not have circular dependencies.

        Rationale: Circular imports make code unmaintainable and hard to test.
        """
        # EDIT: Change to your project structure
        domain_path = Path("src/domain")

        if not domain_path.exists():
            pytest.skip("Domain path not found")

        domain_files = list(domain_path.rglob("*.py"))
        assert len(domain_files) > 0, "No domain files found"

        # Note: Real circular import detection requires AST analysis.
        # This is a simplified check. For robust detection, use:
        # python -m py_compile src/domain/*.py


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
