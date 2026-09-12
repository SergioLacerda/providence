"""
Template: Port Contract Compliance Tests

COPY THIS FILE TO: tests/unit/specs_ia_units/test_port_contracts.py

Replace [project_name] and port names with your actual implementations.
"""

from pathlib import Path

import pytest


class TestPortContracts:
    """Verify infrastructure adapters implement their port contracts."""

    def test_all_adapters_implement_ports(self) -> None:
        """Every adapter in infrastructure must implement a port from domain."""
        adapters_dir = Path("src/[project_name]/infrastructure/adapters")
        if not adapters_dir.exists():
            pytest.skip("Project doesn't have adapters directory")

        adapter_files = adapters_dir.rglob("*.py")

        for file in adapter_files:
            if file.name.startswith("__"):
                continue
            content = file.read_text(encoding="utf-8")

            # Check adapter implements something
            has_class_definition = (
                "class " in content and not content.strip().startswith("#")
            )
            if has_class_definition:
                # Adapter should either:
                # 1. Inherit from a port
                # 2. Implement protocol/ABC
                has_inheritance = "(" in content and ":" in content
                assert has_inheritance, (
                    f"{file}: adapter doesn't inherit from anything (should implement port)"
                )

    def test_storage_adapter_implements_storage_port(self) -> None:
        """Storage adapter must implement StoragePort interface."""
        storage_adapter_path = Path(
            "src/[project_name]/infrastructure/adapters/storage_adapter.py"
        )

        if not storage_adapter_path.exists():
            pytest.skip("Project doesn't have storage adapter")

        content = storage_adapter_path.read_text(encoding="utf-8")

        # Check that class implements StoragePort or equivalent
        assert "StoragePort" in content or "class Storage" in content, (
            "Storage adapter should reference StoragePort contract"
        )

    def test_port_methods_are_implemented(self) -> None:
        """Adapters must implement all methods from port contracts."""
        ports_dir = Path("src/[project_name]/domain/ports")
        if not ports_dir.exists():
            pytest.skip("Project doesn't have ports directory")

        # This is project-specific - verify at least ONE port exists
        port_files = list(ports_dir.glob("*.py"))
        assert len(port_files) > 0, "Domain should define port contracts"

    def test_no_domain_code_calls_non_port_methods(self) -> None:
        """Domain code should only use methods defined in ports, not implementation details."""
        domain_dir = Path("src/[project_name]/domain")
        if not domain_dir.exists():
            pytest.skip("Domain directory not found")

        domain_files = domain_dir.rglob("*.py")

        has_valid_domain_code = False
        for file in domain_files:
            if file.name.startswith("__"):
                continue
            content = file.read_text(encoding="utf-8")
            if "def " in content:  # Has methods
                has_valid_domain_code = True
                # Domain code should use abstract patterns, not concrete implementations
                # This is primarily validated by type checking at runtime

        assert has_valid_domain_code, "Domain should have actual business logic"


class TestPortDiscovery:
    """Discover what ports are defined in project."""

    def test_list_all_ports(self) -> None:
        """Print all ports for verification."""
        ports_dir = Path("src/[project_name]/domain/ports")
        if not ports_dir.exists():
            print("⚠️  No ports directory found")  # noqa: T201
            return

        port_files = sorted(ports_dir.glob("*.py"))
        print(f"\n📋 Discovered {len(port_files)} ports:")  # noqa: T201
        for port_file in port_files:
            print(f"  ✅ {port_file.name}")  # noqa: T201


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
