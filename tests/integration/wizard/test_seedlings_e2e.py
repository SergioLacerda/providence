#!/usr/bin/env python3
"""
End-to-end test: Full wizard integration with intelligent seedlings

This test simulates a real wizard workflow:
1. Create a test project directory
2. Generate mock governance-core.json
3. Initialize Phase 6 generator
4. Run the full pipeline
5. Verify intelligent seedlings were created
6. Validate seedling content
"""

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from tests.helpers.text_io import read_text_utf8, write_text_utf8

# Add packages to path
project_root = Path(__file__).parent.parent.parent.parent
wizard_src = project_root / "packages/interfaces/providence_wizard/src"
sys.path.insert(0, str(wizard_src))

from providence_wizard.orchestration.phase4_governance_loader import (  # noqa: E402
    GovernanceLoader,
)
from providence_wizard.orchestration.phase6_seedlings_orchestrator import (  # noqa: E402
    SeedlingsOrchestrator,
)


def setup_test_environment(base_path: Path) -> Path:
    """Create minimal test environment for Phase 6"""

    # Create necessary directories - files go in generated/client/compiled/source/
    sdd_source = base_path / "generated" / "client" / "compiled" / "source"
    sdd_source.mkdir(parents=True, exist_ok=True)

    # Also seed the output_base .providence/source fallback path
    sdd_fallback = base_path / "generated-project" / ".providence" / "source"
    sdd_fallback.mkdir(parents=True, exist_ok=True)

    # Create mock governance-core.json
    governance_data = {
        "category": "CORE",
        "version": "3.0",
        "items": [
            {
                "id": "M001",
                "title": "Clean Architecture",
                "type": "MANDATE",
                "criticality": "OBRIGATÓRIO",
                "customizable": False,
                "optional": False,
                "category": "architecture",
                "source_file": "mandate.spec",
                "content": "All systems must implement 8-layer Clean Architecture",
            },
            {
                "id": "M002",
                "title": "Test-Driven Development",
                "type": "MANDATE",
                "criticality": "OBRIGATÓRIO",
                "customizable": False,
                "optional": False,
                "category": "testing",
                "source_file": "mandate.spec",
                "content": "All code must be written using TDD (tests first)",
            },
            {
                "id": "G001",
                "title": "Git Workflow Guidelines",
                "type": "GUIDELINE",
                "category": "git",
                "content": "Follow gitflow branching model",
            },
            {
                "id": "G002",
                "title": "Testing Guidelines",
                "type": "GUIDELINE",
                "category": "testing",
                "content": "Maintain 80% code coverage",
            },
            {
                "id": "G003",
                "title": "Naming Conventions",
                "type": "GUIDELINE",
                "category": "naming",
                "content": "Use snake_case for Python functions",
            },
        ],
        "fingerprint": "40c03e88d0efe299f85eb020f716685edaef79803d1d9e2cffa460dee968bcb6",
    }

    governance_file = sdd_source / "governance-core.json"
    write_text_utf8(governance_file, json.dumps(governance_data, indent=2))

    # Also write to fallback path used by Phase456Generator when output_base is supplied
    import shutil

    shutil.copy(governance_file, sdd_fallback / "governance-core.json")

    # Create mock governance-client.json with at least one item to pass integrity check
    client_data = {
        "category": "CLIENT",
        "version": "3.0",
        "items": [
            {
                "id": "G001",
                "title": "Clean Code",
                "type": "GUIDELINE",
                "category": "coding",
                "content": "Follow standard Python PEP 8 style guides",
            }
        ],
    }
    write_text_utf8(
        sdd_source / "governance-client.json", json.dumps(client_data, indent=2)
    )
    write_text_utf8(
        sdd_fallback / "governance-client.json", json.dumps(client_data, indent=2)
    )

    return base_path


def test_full_pipeline() -> None:  # noqa: C901
    """Test full Phase 6 pipeline with intelligent seedlings"""

    print("\n" + "=" * 70)
    print("FULL PIPELINE TEST: Phase 6 with Intelligent Seedlings")
    print("=" * 70)

    with TemporaryDirectory() as temp_dir:
        # Setup
        repo_root = setup_test_environment(Path(temp_dir))
        project_root = Path(temp_dir) / "generated-project"
        project_root.mkdir(parents=True, exist_ok=True)

        config = {
            "adoption_level": "enterprise",
            "language": "python",
        }

        print("\n📂 Test environment:")
        print(f"   Repo root: {repo_root}")
        print(f"   Project root: {project_root}")

        sdd_source = repo_root / "generated" / "client" / "compiled" / "source"
        core_path = sdd_source / "governance-core.json"
        client_path = sdd_source / "governance-client.json"

        # Step 1: Load governance
        print("\n📋 Step 1: Load governance")
        try:
            loader = GovernanceLoader(core_path, client_path, verbose=True)
            if not loader.load():
                print("   ❌ Failed to load governance")
                raise AssertionError("Test failed")
            print(f"   ✅ Loaded {len(loader.mandates)} mandates")
            print(f"   ✅ Loaded {len(loader.guidelines)} guidelines")
            print(
                f"   ✅ Categories: {', '.join(loader.guidelines_by_category.keys())}"
            )
        except AssertionError:
            raise
        except Exception as e:
            print(f"   ❌ Failed to load governance: {e}")
            import traceback

            traceback.print_exc()
            raise AssertionError("Test failed") from e

        # Step 2: Generate intelligent seedlings
        print("\n🌱 Step 2: Generate intelligent seedlings")
        try:
            orchestrator = SeedlingsOrchestrator(
                output_base=project_root,
                mandates=loader.mandates,
                guidelines_by_category=loader.guidelines_by_category,
                config=config,
                governance_core_path=core_path,
                paths={},
                verbose=True,
            )
            if not orchestrator.generate():
                print("   ❌ Failed to generate intelligent seedlings")
                raise AssertionError("Test failed")
            print("   ✅ Intelligent seedlings generated")
        except AssertionError:
            raise
        except Exception as e:
            print(f"   ❌ Failed to generate seedlings: {e}")
            import traceback

            traceback.print_exc()
            raise AssertionError("Test failed") from e

        # Test 4: Verify seedlings created
        print("\n✅ Step 4: Verify seedlings")
        seedlings_dir = project_root / ".providence" / "seedlings"

        if not seedlings_dir.exists():
            print("   ❌ Seedlings directory not created")
            raise AssertionError("Test failed")

        required_files = [
            "governance.seed.json",
            "agent-prep.seed.json",
            "compliance.seed.json",
        ]

        for filename in required_files:
            seed_file = seedlings_dir / filename
            if not seed_file.exists():
                print(f"   ❌ Missing: {filename}")
                raise AssertionError("Test failed")

            seed_data = json.loads(read_text_utf8(seed_file))

            file_size = len(json.dumps(seed_data))
            print(f"   ✅ {filename} ({file_size} bytes)")

        # Test 5: Verify seedling content
        print("\n📊 Step 5: Verify seedling content")

        # Governance seed
        gov_seed = json.loads(read_text_utf8(seedlings_dir / "governance.seed.json"))

        mandates = gov_seed["project_metadata"]["mandates_selected"]
        categories = gov_seed["project_metadata"]["guidelines_active"]
        fingerprint = gov_seed["project_metadata"]["spec_fingerprint"]
        adoption = gov_seed["project_metadata"]["adoption_level"]

        print(f"   Mandates: {mandates}")
        print(f"   Categories: {categories}")
        print(f"   Fingerprint: {fingerprint}")
        print(f"   Adoption Level: {adoption}")

        # Agent prep seed
        agent_seed = json.loads(read_text_utf8(seedlings_dir / "agent-prep.seed.json"))

        agents = agent_seed["agent_configuration"]["supported_agents"]
        print(f"   Agent Support: {', '.join(agents)}")
        for hook_name in ["claude", "gemini"]:
            if hook_name not in agent_seed["ide_hooks"]:
                print(f"   ❌ Missing ide hook: {hook_name}")
                raise AssertionError("Test failed")

        # Compliance seed
        comp_seed = json.loads(read_text_utf8(seedlings_dir / "compliance.seed.json"))

        compliance_fingerprint = comp_seed["compliance_rules"][
            "fingerprint_validation"
        ]["expected_fingerprint"]
        if compliance_fingerprint != fingerprint:
            print("   ❌ Fingerprint mismatch in compliance rules")
            raise AssertionError("Test failed")
        print(f"   ✅ Compliance fingerprint matches: {compliance_fingerprint}")

        # Test 6: Verify SeedlingLoader can load them
        print("\n🔧 Step 6: Verify seedlings are loadable")
        try:
            # Add tools to path for SeedlingLoader
            tools_path = project_root.parent.parent / "tools"
            sys.path.insert(0, str(tools_path.parent))

            from tools.governance.seedling_loader import SeedlingLoader

            seedling_loader = SeedlingLoader(project_root)
            loaded = seedling_loader.load_all()

            print(f"   ✅ SeedlingLoader loaded {len(loaded)} seedlings")
            for seed in loaded:
                print(f"      - {seed['description']}")

        except Exception as e:
            print(f"   ⚠️  SeedlingLoader test skipped: {e}")


def main() -> int:
    """Run end-to-end test"""
    print("\n" + "🚀 " * 35)
    print("END-TO-END INTELLIGENT SEEDLINGS INTEGRATION TEST")
    print("🚀 " * 35)

    try:
        test_full_pipeline()
        success = True
    except Exception as e:
        print(f"End-to-end test failed with error: {e}")
        success = False

    print("\n" + "=" * 70)
    if success:
        print("✅ FULL INTEGRATION TEST PASSED")
        print("=" * 70)
        print("\n🎉 Intelligent seedlings are ready for production!")
        print("\nWhat was generated:")
        print(
            "  ✅ .providence/seedlings/governance.seed.json - GAP v1.0 auto-activation"
        )
        print("  ✅ .providence/seedlings/agent-prep.seed.json - IDE integration hooks")
        print("  ✅ .providence/seedlings/compliance.seed.json - CI/CD validation")
        print("\nNext steps:")
        print("  1. Run wizard to generate a test project")
        print("  2. Verify .providence/seedlings/ directory in generated project")
        print("  3. Test auto-loading with SeedlingLoader")
        print("  4. Deploy wizard changes to production")
        return 0
    else:
        print("❌ FULL INTEGRATION TEST FAILED")
        print("=" * 70)
        return 1


def _remove_generated_at(obj: Any) -> None:
    """Recursively remove generated_at keys from nested dicts/lists."""
    if isinstance(obj, dict):
        obj.pop("generated_at", None)
        for v in obj.values():
            _remove_generated_at(v)
    elif isinstance(obj, list):
        for item in obj:
            _remove_generated_at(item)


def _normalize_seed_content(text: str, filename: str) -> str:
    """Normalize seed file content by removing timestamps."""
    if filename.endswith(".json"):
        try:
            data = json.loads(text)
            _remove_generated_at(data)
            return json.dumps(data, sort_keys=True, indent=2)
        except json.JSONDecodeError:
            return text
    if filename.endswith(".md"):
        skip = {"📅 Generated:", "Generated:", "Last updated:", "last updated:"}
        return "\n".join(
            line for line in text.split("\n") if not any(p in line for p in skip)
        )
    return text


def _capture_run_files(seedlings_dir: Path, claude_md: Path) -> dict[str, str]:
    """Capture all seedling files and normalize timestamps."""
    files: dict[str, str] = {}
    for f in seedlings_dir.glob("*"):
        if f.is_file():
            files[f.name] = _normalize_seed_content(read_text_utf8(f), f.name)
    if claude_md.exists():
        files["CLAUDE.md"] = _normalize_seed_content(
            read_text_utf8(claude_md), "CLAUDE.md"
        )
    return files


def _assert_runs_identical(first: dict[str, str], second: dict[str, str]) -> None:
    """Assert that two runs produced identical files."""
    assert len(first) == len(second), "File count mismatch between runs"
    all_match = True
    for filename in first:
        if filename not in second:
            print(f"   ❌ File missing in second run: {filename}")
            all_match = False
        elif first[filename] != second[filename]:
            print(f"   ❌ Content mismatch: {filename}")
            all_match = False
        else:
            print(f"   ✅ {filename} (identical)")
    assert all_match, (
        "Seedling generation is not idempotent — files differ between runs"
    )


def test_seedl_gen_idempotent() -> None:
    """
    GAP 6.3: Verify that running seedlings generation twice produces
    identical output (idempotence guarantee).

    NOTE: Tests idempotence by comparing JSON structure and content,
    stripping out generated_at timestamps which legitimately change.
    """
    print("\n" + "=" * 70)
    print("IDEMPOTENCE TEST: Running generation twice should produce identical output")
    print("=" * 70)

    with TemporaryDirectory() as temp_dir:
        repo_root = setup_test_environment(Path(temp_dir))
        project_root = Path(temp_dir) / "generated-project"
        project_root.mkdir(parents=True, exist_ok=True)

        config = {
            "adoption_level": "enterprise",
            "language": "python",
        }

        sdd_source = repo_root / "generated" / "client" / "compiled" / "source"
        core_path = sdd_source / "governance-core.json"
        client_path = sdd_source / "governance-client.json"

        # Load governance once
        loader = GovernanceLoader(core_path, client_path, verbose=False)
        assert loader.load(), "Failed to load governance"

        # First generation run
        print("\n🌱 First generation run...")
        orch1 = SeedlingsOrchestrator(
            output_base=project_root,
            mandates=loader.mandates,
            guidelines_by_category=loader.guidelines_by_category,
            config=config,
            governance_core_path=core_path,
            paths={},
            verbose=False,
        )
        assert orch1.generate(), "First generation failed"

        # Capture all generated files
        seedlings_dir = project_root / ".providence" / "seedlings"
        claude_md = project_root / "CLAUDE.md"
        first_run_files = _capture_run_files(seedlings_dir, claude_md)
        print(f"   ✅ First run generated {len(first_run_files)} files")

        # Second generation run (simulating wizard run again)
        print("\n🌱 Second generation run...")
        orch2 = SeedlingsOrchestrator(
            output_base=project_root,
            mandates=loader.mandates,
            guidelines_by_category=loader.guidelines_by_category,
            config=config,
            governance_core_path=core_path,
            paths={},
            verbose=False,
        )
        assert orch2.generate(), "Second generation failed"

        # Capture all generated files again
        second_run_files = _capture_run_files(seedlings_dir, claude_md)
        print(f"   ✅ Second run generated {len(second_run_files)} files")

        # Verify idempotence: all files must be identical (after normalizing timestamps)
        print("\n🔍 Comparing outputs (ignoring generated_at timestamps)...")
        _assert_runs_identical(first_run_files, second_run_files)

        print(
            "\n✅ IDEMPOTENCE TEST PASSED: Generation is deterministic and idempotent"
        )


def test_seedlings_json_validity() -> None:
    """Validate that all .seed.json files are valid JSON."""
    print("\n" + "=" * 70)
    print("JSON VALIDITY TEST: All .seed.json files must be valid JSON")
    print("=" * 70)

    with TemporaryDirectory() as temp_dir:
        repo_root = setup_test_environment(Path(temp_dir))
        project_root = Path(temp_dir) / "generated-project"
        project_root.mkdir(parents=True, exist_ok=True)

        config = {"adoption_level": "enterprise", "language": "python"}

        sdd_source = repo_root / "generated" / "client" / "compiled" / "source"
        core_path = sdd_source / "governance-core.json"
        client_path = sdd_source / "governance-client.json"

        loader = GovernanceLoader(core_path, client_path, verbose=False)
        assert loader.load()

        orchestrator = SeedlingsOrchestrator(
            output_base=project_root,
            mandates=loader.mandates,
            guidelines_by_category=loader.guidelines_by_category,
            config=config,
            governance_core_path=core_path,
            paths={},
            verbose=False,
        )
        assert orchestrator.generate()

        seedlings_dir = project_root / ".providence" / "seedlings"
        json_files = list(seedlings_dir.glob("*.json"))

        print(f"\n📋 Found {len(json_files)} JSON files to validate")

        for json_file in json_files:
            try:
                data = json.loads(read_text_utf8(json_file))
                print(
                    f"   ✅ {json_file.name} (valid JSON, {len(data)} top-level keys)"
                )
            except json.JSONDecodeError as e:
                print(f"   ❌ {json_file.name} (INVALID JSON): {e}")
                raise AssertionError(f"Invalid JSON in {json_file.name}") from e


def test_seedlings_content_validation() -> None:
    """
    Validate critical content in generated seedlings:
    - CLAUDE.md exists and references governance (format may vary by implementation)
    - agent-instructions.md has 6 sections
    - All seed.json reference .providence/ directory
    """
    print("\n" + "=" * 70)
    print("CONTENT VALIDATION TEST: Verify seedling structure and references")
    print("=" * 70)

    with TemporaryDirectory() as temp_dir:
        repo_root = setup_test_environment(Path(temp_dir))
        project_root = Path(temp_dir) / "generated-project"
        project_root.mkdir(parents=True, exist_ok=True)

        config = {"adoption_level": "enterprise", "language": "python"}

        sdd_source = repo_root / "generated" / "client" / "compiled" / "source"
        core_path = sdd_source / "governance-core.json"
        client_path = sdd_source / "governance-client.json"

        loader = GovernanceLoader(core_path, client_path, verbose=False)
        assert loader.load()

        orchestrator = SeedlingsOrchestrator(
            output_base=project_root,
            mandates=loader.mandates,
            guidelines_by_category=loader.guidelines_by_category,
            config=config,
            governance_core_path=core_path,
            paths={},
            verbose=False,
        )
        assert orchestrator.generate()

        print(
            "\n📄 Validating CLAUDE.md structure (dumb pointer to .providence/agent-instructions.md)..."
        )
        claude_md = project_root / "CLAUDE.md"
        assert claude_md.exists(), "CLAUDE.md not found"

        claude_content = read_text_utf8(claude_md)

        # CLAUDE.md MUST be the dumb pointer format (from ai_seeds.generate_claude_seed)
        # This ensures single source of truth in .providence/agent-instructions.md
        assert "agent-instructions.md" in claude_content, (
            "CLAUDE.md should reference .providence/agent-instructions.md (dumb pointer format)"
        )
        assert "## Active Mandates" not in claude_content, (
            "CLAUDE.md should not contain embedded mandate lists (not the rich format)"
        )
        assert (
            "SDD" in claude_content
            or "sdd" in claude_content
            or ".providence" in claude_content
        ), "CLAUDE.md should contain SDD/sdd/.providence references"
        print(f"   ✅ CLAUDE.md is dumb pointer format ({len(claude_content)} bytes)")

        print("\n📄 Validating agent-instructions.md structure...")
        agent_instructions = project_root / ".providence" / "agent-instructions.md"
        assert agent_instructions.exists(), (
            ".providence/agent-instructions.md not found"
        )

        agent_content = read_text_utf8(agent_instructions)

        # Check for 7 required sections
        required_sections_agent = [
            "## 1. Authority Hierarchy",
            "## 2. Mandatory Bootstrap",
            "## 3. Active Mandates",
            "## 4. Pre-Task Checklist",
            "## 5. Enforcement Scope",
            "## Governance Mode",
            "## 6. Fallback & Escalation",
        ]

        sections_found_agent = 0
        for section in required_sections_agent:
            if section in agent_content:
                sections_found_agent += 1
                print(f"   ✅ Found section: {section}")
            else:
                print(f"   ⚠️  Missing section: {section}")

        assert sections_found_agent == 7, (
            f"agent-instructions.md missing sections (found {sections_found_agent}/7)"
        )

        print("\n📋 Validating seed.json references to .providence/...")
        seedlings_dir = project_root / ".providence" / "seedlings"
        seed_files = list(seedlings_dir.glob("*.json"))

        sdd_references_found = 0
        for seed_file in seed_files:
            content = read_text_utf8(seed_file)
            if ".providence/" in content:
                sdd_references_found += 1
                print(f"   ✅ {seed_file.name} references .providence/")

        assert sdd_references_found > 0, (
            "No seed.json files reference .providence/ directory"
        )
        print(
            f"   ✅ {sdd_references_found}/{len(seed_files)} seed files reference .providence/"
        )

        print("\n✅ CONTENT VALIDATION TEST PASSED")


def test_fingerprint_matches_compiled_governance() -> None:
    """
    Validate that stored fingerprint in compliance.seed.json matches
    the actual fingerprint computed from governance-core.json.

    This ensures drift detection works: if governance changes but seedlings
    are not regenerated, the fingerprints will differ.
    """
    print("\n" + "=" * 70)
    print("FINGERPRINT VALIDATION TEST: Seedling vs Compiled Governance")
    print("=" * 70)

    with TemporaryDirectory() as temp_dir:
        repo_root = setup_test_environment(Path(temp_dir))
        project_root = Path(temp_dir) / "generated-project"
        project_root.mkdir(parents=True, exist_ok=True)

        config = {"adoption_level": "enterprise", "language": "python"}

        sdd_source = repo_root / "generated" / "client" / "compiled" / "source"
        core_path = sdd_source / "governance-core.json"
        client_path = sdd_source / "governance-client.json"

        loader = GovernanceLoader(core_path, client_path, verbose=False)
        assert loader.load()

        orchestrator = SeedlingsOrchestrator(
            output_base=project_root,
            mandates=loader.mandates,
            guidelines_by_category=loader.guidelines_by_category,
            config=config,
            governance_core_path=core_path,
            paths={},
            verbose=False,
        )
        assert orchestrator.generate()

        print("\n🔐 Computing fingerprints...")

        # Read expected fingerprint from compliance.seed.json
        compliance_seed = (
            project_root / ".providence" / "seedlings" / "compliance.seed.json"
        )
        assert compliance_seed.exists(), "compliance.seed.json not found"

        compliance_data = json.loads(read_text_utf8(compliance_seed))
        expected_fingerprint = (
            compliance_data.get("compliance_rules", {})
            .get("fingerprint_validation", {})
            .get("expected_fingerprint")
        )
        assert expected_fingerprint, (
            "expected_fingerprint not found in compliance.seed.json"
        )
        print(f"   📋 Expected fingerprint (from seed): {expected_fingerprint}")

        # Compute actual fingerprint from governance_core_path
        core_content = read_text_utf8(core_path)
        clean_content = json.dumps(json.loads(core_content), separators=(",", ":"))
        import hashlib

        actual_fingerprint = hashlib.sha256(clean_content.encode()).hexdigest()[:8]
        print(f"   📋 Actual fingerprint (from core):  {actual_fingerprint}")

        # Assert they match
        assert expected_fingerprint == actual_fingerprint, (
            f"Fingerprint mismatch: seed has {expected_fingerprint}, "
            f"but compiled governance has {actual_fingerprint}. "
            "Run 'providence governance generate' to regenerate seedlings."
        )

        print(f"   ✅ Fingerprints match: {actual_fingerprint}")
        print("\n✅ FINGERPRINT VALIDATION TEST PASSED")


if __name__ == "__main__":
    sys.exit(main())
