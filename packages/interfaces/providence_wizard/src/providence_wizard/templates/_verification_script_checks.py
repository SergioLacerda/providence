"""verify.py generated-script sections: SeedlingLoader discovery and mandate
verification methods of GovernanceVerifier. Split out of
_verification_script_template.py to keep files under the 200-line convention.
"""

from __future__ import annotations


def _check_seedling_loader_method() -> str:
    return '''    def check_seedling_loader(self) -> bool:
        """Test SeedlingLoader discovery"""
        try:
            # Robust path discovery: search for tools directory up to 4 levels deep
            root = self.project_root
            found_root = False
            for _ in range(5):
                if (root / "tools" / "governance").exists():
                    sys.path.insert(0, str(root))
                    found_root = True
                    break
                if root == root.parent:
                    break
                root = root.parent

            if not found_root:
                # Fallback: try to find repository root by looking for 'packages' or '.git'
                current_path = Path(__file__).resolve().parent
                repo_root = None
                for _ in range(10): # Limit depth to prevent infinite loop
                    if (current_path / "packages").is_dir() or (current_path / ".git").is_dir():
                        repo_root = current_path
                        break
                    if current_path == current_path.parent: # Reached filesystem root
                        break
                    current_path = current_path.parent

                if repo_root:
                    sys.path.insert(0, str(repo_root))
                else:
                    # Last resort, might not be correct for all setups
                    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

            from tools.governance.seedling_loader import SeedlingLoader

            loader = SeedlingLoader(self.project_root)
            loaded = loader.load_all()

            if len(loaded) >= 3:
                logger.info(f"   SeedlingLoader: Discovered {len(loaded)} seedlings")
                self.checks["SeedlingLoader"] = "pass"
                self.passed += 1
                return True
            else:
                logger.warning(f"    SeedlingLoader: Found only {len(loaded)} seedlings (expected 3+)")
                self.checks["SeedlingLoader"] = "warn"
                self.warnings += 1
                return False
        except Exception as e:
            logger.warning(f"    SeedlingLoader: Could not test")
            self.checks["SeedlingLoader"] = "warn"
            self.warnings += 1
            return False

'''


def _verify_mandates_method(mandate_ids_str: str) -> str:
    return f'''    def verify_mandates(self) -> bool:
        """Verify mandates are configured"""
        expected = {{'{mandate_ids_str}'}}
        gov_seed_path = self.project_root / ".providence/seedlings/governance.seed.json"

        try:
            with open(gov_seed_path, "r") as f:
                data = json.load(f)
                configured = set(data.get("project_metadata", {{}}).get("mandates_selected", []))

            if configured == expected:
                logger.info(f"   Mandates: {{', '.join(expected)}}")
                self.checks["Mandates"] = "pass"
                self.passed += 1
                return True
            else:
                logger.warning(f"   Mandates mismatch: Expected {{expected}}, got {{configured}}")
                self.checks["Mandates"] = "fail"
                self.failed += 1
                return False
        except Exception as e:
            logger.warning(f"   Mandates: Could not verify")
            self.checks["Mandates"] = "fail"
            self.failed += 1
            return False

'''
