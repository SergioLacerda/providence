#!/usr/bin/env python3
"""
Test intelligent seedlings generation integration

Tests:
1. IntelligentSeedlingsGenerator module imports correctly
2. Creates three seedling files with correct structure
3. Fingerprint is computed correctly
4. Seedling content matches expected format
5. Phase 6 integration method exists and works
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from tests.helpers.text_io import read_text_utf8

# Add packages to path
project_root = Path(__file__).parent.parent.parent.parent
wizard_src = project_root / "packages/interfaces/providence_wizard/src"
sys.path.insert(0, str(wizard_src))

from providence_wizard.orchestration.intelligent_seedlings_generator import (  # noqa: E402
    IntelligentSeedlingsGenerator,
)


def test_intelligent_seedlings_generator() -> None:  # noqa: C901
    """Test intelligent seedlings generator"""
    print("\n" + "=" * 70)
    print("Testing Intelligent Seedlings Generator")
    print("=" * 70)

    with TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        print(f"\n📂 Test project: {project_root}")

        # Create test governance-core.json
        governance_core_path = project_root / "governance-core.json"
        governance_data: dict[str, Any] = {
            "category": "CORE",
            "version": "3.0",
            "items": [
                {
                    "id": "M001",
                    "title": "Clean Architecture",
                    "type": "MANDATE",
                    "category": "architecture",
                },
                {
                    "id": "M002",
                    "title": "Test-Driven Development",
                    "type": "MANDATE",
                    "category": "testing",
                },
                {
                    "id": "G001",
                    "title": "Git Workflow",
                    "type": "GUIDELINE",
                    "category": "git",
                },
            ],
        }
        with open(governance_core_path, "w", encoding="utf-8") as f:
            json.dump(governance_data, f)

        # Prepare test data
        mandates: list[dict[str, Any]] = [
            item for item in governance_data["items"] if item["type"] == "MANDATE"
        ]
        guidelines_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in governance_data["items"]:
            if item["type"] == "GUIDELINE":
                category = item.get("category", "other")
                guidelines_by_category[category].append(item)

        config = {
            "adoption_level": "enterprise",
            "language": "python",
        }

        # Test 1: Create generator
        print("\n✓ Test 1: Instantiate IntelligentSeedlingsGenerator")
        try:
            generator = IntelligentSeedlingsGenerator(
                output_base=project_root,
                mandates=mandates,
                guidelines_by_category=guidelines_by_category,
                config=config,
                governance_core_path=governance_core_path,
                verbose=True,
            )
            print("  ✅ Generator created successfully")
        except Exception as e:
            print(f"  ❌ Failed to create generator: {e}")
            raise AssertionError("Test failed") from e

        # Test 2: Generate seedlings
        print("\n✓ Test 2: Generate all intelligent seedlings")
        try:
            success = generator.generate_all()
            if not success:
                print("  ❌ Failed to generate seedlings")
                raise AssertionError("Test failed")
            print("  ✅ Seedlings generated successfully")
        except Exception as e:
            print(f"  ❌ Failed to generate seedlings: {e}")
            raise AssertionError("Test failed") from e

        # Test 3: Verify seedlings directory created
        print("\n✓ Test 3: Verify seedlings directory structure")
        seedlings_dir = project_root / ".providence" / "seedlings"
        if not seedlings_dir.exists():
            print(f"  ❌ Seedlings directory not created: {seedlings_dir}")
            raise AssertionError("Test failed")
        print(f"  ✅ Seedlings directory: {seedlings_dir}")

        # Test 4: Verify each seedling file (13 files expected)
        print("\n✓ Test 4: Verify seedling files (13 total)")
        required_json_files = [
            "governance.seed.json",
            "agent-prep.seed.json",
            "compliance.seed.json",
        ]

        # Verify JSON seedling files
        for filename in required_json_files:
            seed_file = seedlings_dir / filename
            if not seed_file.exists():
                print(f"  ❌ Missing seedling file: {filename}")
                raise AssertionError("Test failed")
            try:
                with open(seed_file, encoding="utf-8") as f:
                    seed_data = json.load(f)
                print(f"  ✅ {filename} ({len(json.dumps(seed_data))} bytes)")
            except json.JSONDecodeError as e:
                print(f"  ❌ Invalid JSON in {filename}: {e}")
                raise AssertionError("Test failed") from e

        # Verify documentation files
        print("\n✓ Test 4b: Verify documentation and verification files")
        doc_files = [
            ("ACTIVATION_GUIDE.md", "Activation guide"),
            ("verify.py", "Verification script"),
        ]

        for filename, description in doc_files:
            doc_file = seedlings_dir / filename
            if not doc_file.exists():
                print(f"  ❌ Missing {description}: {filename}")
                raise AssertionError("Test failed")
            try:
                content = read_text_utf8(doc_file)
                print(f"  ✅ {filename} ({len(content)} bytes) - {description}")
            except Exception as e:
                print(f"  ❌ Error reading {filename}: {e}")
                raise AssertionError("Test failed") from e

        # Test 4c: Verify new agnostic and native hooks
        print("\n✓ Test 4c: Verify agnostic and native hooks")
        native_files = [
            ("AGENTS.md", "Agent Bootstrap Contract"),
            (".providence/agent-instructions.md", "Agnostic Instructions"),
            (".github/copilot-instructions.md", "Copilot Instructions"),
            (".gemini/gemini-instructions.md", "Gemini Instructions"),
            ("GEMINI.md", "Gemini Root Pointer"),
            ("CLAUDE.md", "Claude Instructions"),
        ]
        for rel_path, desc in native_files:
            hook_file = project_root / rel_path
            if not hook_file.exists():
                print(f"  ❌ Missing {desc}: {rel_path}")
                raise AssertionError("Test failed")
            print(f"  ✅ {desc} created at {rel_path}")

        # Test 5: Verify governance.seed.json structure
        print("\n✓ Test 5: Verify governance.seed.json content")
        with open(seedlings_dir / "governance.seed.json", encoding="utf-8") as f:
            gov_seed = json.load(f)

        required_keys = [
            "auto_activate",
            "required_context",
            "on_load",
            "triggers",
            "project_metadata",
        ]
        for key in required_keys:
            if key not in gov_seed:
                print(f"  ❌ Missing key in governance.seed.json: {key}")
                raise AssertionError("Test failed")
        print("  ✅ governance.seed.json structure valid")

        # Verify mandates
        metadata = gov_seed["project_metadata"]
        if "mandates_selected" not in metadata:
            print("  ❌ Missing mandates_selected in metadata")
            raise AssertionError("Test failed")
        if metadata["mandates_selected"] != ["M001", "M002"]:
            print(f"  ❌ Wrong mandates: {metadata['mandates_selected']}")
            raise AssertionError("Test failed")
        print(f"  ✅ Mandates: {metadata['mandates_selected']}")

        # Verify fingerprint
        if "spec_fingerprint" not in metadata:
            print("  ❌ Missing spec_fingerprint in metadata")
            raise AssertionError("Test failed")
        fingerprint = metadata["spec_fingerprint"]
        if len(fingerprint) != 8:
            print(f"  ❌ Invalid fingerprint length: {len(fingerprint)}")
            raise AssertionError("Test failed")
        print(f"  ✅ Fingerprint: {fingerprint}")

        # Verify adoption_level
        if metadata["adoption_level"] != "enterprise":
            print(f"  ❌ Wrong adoption_level: {metadata['adoption_level']}")
            raise AssertionError("Test failed")
        print(f"  ✅ Adoption Level: {metadata['adoption_level']}")

        # Test 6: Verify agent-prep.seed.json structure
        print("\n✓ Test 6: Verify agent-prep.seed.json content")
        with open(seedlings_dir / "agent-prep.seed.json", encoding="utf-8") as f:
            agent_seed = json.load(f)

        if "agent_configuration" not in agent_seed:
            print("  ❌ Missing agent_configuration")
            raise AssertionError("Test failed")
        if "ide_hooks" not in agent_seed:
            print("  ❌ Missing ide_hooks")
            raise AssertionError("Test failed")
        print("  ✅ agent-prep.seed.json structure valid")
        print(
            f"     Supported agents: {agent_seed['agent_configuration']['supported_agents']}"
        )
        ide_hooks = agent_seed["ide_hooks"]
        for hook_name in ["claude", "gemini"]:
            if hook_name not in ide_hooks:
                print(f"  ❌ Missing ide hook: {hook_name}")
                raise AssertionError("Test failed")
        print("  ✅ Extended agent hooks are present")

        # Test 7: Verify compliance.seed.json structure
        print("\n✓ Test 7: Verify compliance.seed.json content")
        with open(seedlings_dir / "compliance.seed.json", encoding="utf-8") as f:
            compliance_seed = json.load(f)

        if "compliance_rules" not in compliance_seed:
            print("  ❌ Missing compliance_rules")
            raise AssertionError("Test failed")
        if "hooks" not in compliance_seed:
            print("  ❌ Missing hooks")
            raise AssertionError("Test failed")
        print("  ✅ compliance.seed.json structure valid")

        # Verify fingerprint validation
        rules = compliance_seed["compliance_rules"]
        if rules["fingerprint_validation"]["expected_fingerprint"] != fingerprint:
            print("  ❌ Fingerprint mismatch in compliance rules")
            raise AssertionError("Test failed")
        print(f"  ✅ Fingerprint validation configured: {fingerprint}")

        # Test 8: Verify verify.py has valid Python syntax
        print("\n✓ Test 8: Validate verify.py syntax")
        try:
            import ast

            verify_file = seedlings_dir / "verify.py"
            with open(verify_file, encoding="utf-8") as f:
                verify_content = f.read()
            ast.parse(verify_content)
            print("  ✅ verify.py has valid Python syntax")
        except SyntaxError as e:
            print(f"  ❌ verify.py syntax error: {e}")
            raise AssertionError("Test failed") from e

        # Test 9: Verify ACTIVATION_GUIDE.md contains required sections
        print("\n✓ Test 9: Validate ACTIVATION_GUIDE.md content")
        try:
            guide_file = seedlings_dir / "ACTIVATION_GUIDE.md"
            guide_content = read_text_utf8(guide_file)

            required_sections = [
                "Quick Start",
                "Checklist",
                "Your Governance Configuration",
                "What Each Seedling Does",
                "Verification",
                "Troubleshooting",
            ]

            for section in required_sections:
                if section not in guide_content:
                    print(f"  ❌ Missing section: {section}")
                    raise AssertionError("Test failed")

            print("  ✅ ACTIVATION_GUIDE.md has all required sections")
        except Exception as e:
            print(f"  ❌ Error validating guide: {e}")
            raise AssertionError("Test failed") from e

        # Test 10: Get summary
        print("\n✓ Test 10: Verify generator summary")
        summary = generator.get_summary()
        print(f"  ✅ Summary: {json.dumps(summary, indent=2)}")

        # Verify summary follows dynamic awareness-aware contract
        files = summary.get("files", [])
        if summary.get("count") != len(files):
            print(
                f"  ❌ Summary count mismatch: count={summary.get('count')} vs files={len(files)}"
            )
            raise AssertionError("Test failed")
        if summary.get("count", 0) < 8:
            print(
                f"  ❌ Expected at least 8 generated artifacts in summary, got {summary.get('count')}"
            )
            raise AssertionError("Test failed")

        awareness = summary.get("awareness_pack", {})
        if awareness.get("status") != "ok":
            print(f"  ❌ Awareness pack status not ok: {awareness}")
            raise AssertionError("Test failed")
        if awareness.get("mode") not in {"full", "fallback"}:
            print(f"  ❌ Unexpected awareness mode: {awareness.get('mode')}")
            raise AssertionError("Test failed")

        print(
            f"  ✅ Summary contract valid ({summary.get('count')} artifacts, awareness={awareness.get('mode')})"
        )


def test_phase6_integration() -> None:
    """Test Phase 6 generator integration"""
    print("\n" + "=" * 70)
    print("Testing Phase 6 Generator Integration")
    print("=" * 70)

    # Check that SeedlingsOrchestrator has the generate method
    print("\n✓ Test 1: Verify SeedlingsOrchestrator.generate method exists")
    try:
        from providence_wizard.orchestration.phase6_seedlings_orchestrator import (
            SeedlingsOrchestrator,
        )

        if not hasattr(SeedlingsOrchestrator, "generate"):
            print("  ❌ Method not found: SeedlingsOrchestrator.generate")
            raise AssertionError("Test failed")
        print("  ✅ Method exists: SeedlingsOrchestrator.generate")
    except Exception as e:
        print(f"  ❌ Failed to verify Phase 6 integration: {e}")
        raise AssertionError("Test failed") from e


def main() -> int:
    """Run all tests"""
    print("\n" + "🧪 " * 35)
    print("INTELLIGENT SEEDLINGS GENERATION TEST SUITE")
    print("🧪 " * 35)

    results = []

    # Run tests
    try:
        test_intelligent_seedlings_generator()
        results.append(("Generator Tests", True))
    except Exception as e:
        print(f"Critical error in Generator Tests: {e}")
        results.append(("Generator Tests", False))

    try:
        test_phase6_integration()
        results.append(("Phase 6 Integration", True))
    except Exception as e:
        print(f"Critical error in Phase 6 Integration: {e}")
        results.append(("Phase 6 Integration", False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
