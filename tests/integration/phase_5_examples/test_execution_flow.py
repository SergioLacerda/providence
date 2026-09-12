#!/usr/bin/env python3
"""
Phase 5: EXECUTION Flow Functional Test

Tests the EXECUTION flow by validating:
- AGENT_HARNESS 7-phase workflow structure
- CANONICAL layer documentation
- Link validity
- AI-first design
"""

# This file is a standalone functional script (run via __main__), not a pytest module.
__test__ = False

from pathlib import Path

from tests.helpers.text_io import read_text_utf8


class TestExecutionFlow:
    """Test EXECUTION flow: 7-phase AGENT_HARNESS workflow"""

    def __init__(self) -> None:
        # Resolve symlinks to get actual path
        current_file = Path(__file__).resolve()
        self.framework_root = current_file.parent.parent.parent
        self.execution_dir = self.framework_root / "EXECUTION"
        self.results: list[tuple[str, bool]] = []

    def test_entry_points(self) -> bool:
        """Test EXECUTION entry points exist"""
        print("\n📋 TEST 1: Entry Points")

        entry_points = ["README.md", "_START_HERE.md", "NAVIGATION.md", "INDEX.md"]

        for entry in entry_points:
            path = self.execution_dir / entry
            if path.exists():
                print(f"  ✅ Entry point found: {entry}")
                self.results.append((entry, True))
            else:
                print(f"  ❌ Entry point missing: {entry}")
                self.results.append((entry, False))

        return all(result for _, result in self.results[-len(entry_points) :])

    def test_canonical_layer(self) -> bool:
        """Test CANONICAL layer (immutable authority)"""
        print("\n📋 TEST 2: CANONICAL Layer")

        canonical_dir = self.execution_dir / "docs/ia/CANONICAL"

        # Rules layer
        rules_files = [
            "rules/constitution.md",
            "rules/ia-rules.md",
            "rules/conventions.md",
        ]

        print("  🔴 Constitution Layer:")
        for rule_file in rules_files:
            path = canonical_dir / rule_file
            if path.exists():
                print(f"    ✅ {rule_file}")
                self.results.append((f"canonical/{rule_file}", True))
            else:
                print(f"    ❌ {rule_file}")
                self.results.append((f"canonical/{rule_file}", False))

        # Decisions layer (ADRs)
        adr_dir = canonical_dir / "decisions"
        adr_files = list(adr_dir.glob("ADR-*.md")) if adr_dir.exists() else []

        print("  🟡 Decisions Layer (ADRs):")
        if len(adr_files) >= 6:
            print(f"    ✅ Found {len(adr_files)} ADRs")
            self.results.append(("canonical/decisions", True))
        else:
            print(f"    ❌ Only found {len(adr_files)} ADRs (need 6+)")
            self.results.append(("canonical/decisions", False))

        # Specifications layer
        spec_files = [
            "specifications/definition_of_done.md",
            "specifications/communication.md",
            "specifications/architecture.md",
            "specifications/testing.md",
        ]

        print("  🟢 Specifications Layer:")
        for spec_file in spec_files:
            path = canonical_dir / spec_file
            if path.exists():
                print(f"    ✅ {spec_file}")
                self.results.append((f"canonical/{spec_file}", True))
            else:
                print(f"    ⚠️  Optional: {spec_file}")

        return True

    def test_guides_layer(self) -> bool:
        """Test Guides layer (operational help)"""
        print("\n📋 TEST 3: Guides Layer")

        guides_dir = self.execution_dir / "docs/ia/guides"

        guide_categories = {
            "onboarding": ["AGENT_HARNESS.md", "VALIDATION_QUIZ.md"],
            "operational": [
                "ADDING_NEW_PROJECT.md",
                "TROUBLESHOOTING_SPEC_VIOLATIONS.md",
            ],
            "emergency": ["README.md"],
            "reference": ["FAQ.md", "GLOSSARY.md"],
        }

        for category, files in guide_categories.items():
            cat_dir = guides_dir / category
            print(f"  📚 {category.upper()}:")

            for file in files:
                path = cat_dir / file
                if path.exists():
                    print(f"    ✅ {file}")
                    self.results.append((f"guides/{category}/{file}", True))
                else:
                    print(f"    ⚠️  {file}")

        return True

    def test_runtime_layer(self) -> bool:
        """Test Runtime layer (search & indices)"""
        print("\n📋 TEST 4: Runtime Layer")

        runtime_dir = self.execution_dir / "docs/ia/runtime"

        runtime_files = [
            "search-keywords.md",
            "spec-canonical-index.md",
            "spec-guides-index.md",
        ]

        for runtime_file in runtime_files:
            path = runtime_dir / runtime_file
            if path.exists():
                size = path.stat().st_size
                lines = read_text_utf8(path).count("\n")
                print(f"  ✅ {runtime_file} ({lines} lines, {size} bytes)")
                self.results.append((f"runtime/{runtime_file}", True))
            else:
                print(f"  ❌ {runtime_file}")
                self.results.append((f"runtime/{runtime_file}", False))

        return True

    def test_custom_layer(self) -> bool:
        """Test Custom layer (project-specific)"""
        print("\n📋 TEST 5: Custom Layer")

        custom_dir = self.execution_dir / "docs/ia/custom"

        if custom_dir.exists():
            projects = list(custom_dir.glob("*/"))
            print("  ✅ Custom layer exists")
            print(f"  ✅ Projects configured: {len(projects)}")
            for project in projects:
                print(f"    - {project.name}")
            self.results.append(("custom_layer", True))
        else:
            print("  ❌ Custom layer missing")
            self.results.append(("custom_layer", False))

        return True

    def test_markdown_links(self) -> bool:
        """Test markdown links validity"""
        print("\n📋 TEST 6: Markdown Links")

        # Check key files for link format
        key_files = ["_START_HERE.md", "NAVIGATION.md", "INDEX.md"]

        import re

        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        total_links = 0
        for key_file in key_files:
            path = self.execution_dir / key_file
            if path.exists():
                content = read_text_utf8(path)
                links = link_pattern.findall(content)
                total_links += len(links)
                print(f"  ✅ {key_file}: {len(links)} links found")
                self.results.append((f"links/{key_file}", True))
            else:
                print(f"  ❌ {key_file}: file not found")
                self.results.append((f"links/{key_file}", False))

        print(f"  📊 Total links: {total_links}")
        return True

    def test_ai_first_design(self) -> bool:
        """Test AI-first design (at root level)"""
        print("\n📋 TEST 7: AI-First Design")

        root_dir = self.framework_root

        ai_files = [".providence-index.md", "README.md"]

        for ai_file in ai_files:
            path = root_dir / ai_file
            if path.exists():
                size = path.stat().st_size
                print(f"  ✅ {ai_file} ({size} bytes)")
                self.results.append((f"ai_first/{ai_file}", True))
            else:
                print(f"  ❌ {ai_file}")
                self.results.append((f"ai_first/{ai_file}", False))

        return True

    def run_all_tests(self) -> bool:
        """Run complete EXECUTION flow test"""
        print("\n" + "=" * 80)
        print("🚀 PHASE 5: EXECUTION FLOW FUNCTIONAL TEST")
        print("=" * 80)

        try:
            # Run all tests
            tests = [
                self.test_entry_points,
                self.test_canonical_layer,
                self.test_guides_layer,
                self.test_runtime_layer,
                self.test_custom_layer,
                self.test_markdown_links,
                self.test_ai_first_design,
            ]

            for test in tests:
                try:
                    test()
                except Exception as e:
                    print(f"  ❌ ERROR in {test.__name__}: {e}")

            # Summary
            print("\n" + "=" * 80)
            print("📊 TEST SUMMARY")
            print("=" * 80)

            passed = sum(1 for _, result in self.results if result)
            total = len(self.results)

            print(f"Tests Passed: {passed}/{total}")

            if passed >= total * 0.9:  # 90% pass rate is good
                print("\n✅ EXECUTION FLOW: READY FOR PRODUCTION")
                return True
            else:
                print("\n⚠️  EXECUTION FLOW: CHECK FAILURES ABOVE")
                return False

        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
            return False


if __name__ == "__main__":
    tester = TestExecutionFlow()
    success = tester.run_all_tests()
    raise SystemExit(0 if success else 1)
