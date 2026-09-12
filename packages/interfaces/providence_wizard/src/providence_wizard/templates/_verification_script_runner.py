"""verify.py generated-script sections: the run() orchestration method plus
the CLI main()/entry point. Split out of _verification_script_template.py to
keep files under the 200-line convention.
"""

from __future__ import annotations


def _run_method() -> str:
    return '''    def run(self) -> bool:
        """Run all verification checks"""
        logger.debug("=" * 70)
        logger.info(" Governance Activation Verification")
        logger.debug("=" * 70)

        logger.info("\\n Directory Structure:")
        self.check_directory(".providence/source/mandates", ".providence/source/mandates")
        self.check_directory(".providence/source/guidelines", ".providence/source/guidelines")
        self.check_directory(".providence/runtime", ".providence/runtime")
        self.check_directory(".providence/seedlings", ".providence/seedlings")

        logger.info("\\n Required Files:")
        self.check_file(".providence/metadata.json", ".providence/metadata.json", must_be_json=True)
        self.check_file(".providence/runtime/mandate.bin", "mandate.bin")
        self.check_file(".providence/source/mandates/mandates.md", "mandates.md")
        self.check_file(".providence/seedlings/governance.seed.json", "governance.seed.json", must_be_json=True)
        self.check_file(".providence/seedlings/agent-prep.seed.json", "agent-prep.seed.json", must_be_json=True)
        self.check_file(".providence/seedlings/compliance.seed.json", "compliance.seed.json", must_be_json=True)

        logger.info("\\n Governance Configuration:")
        self.verify_mandates()

        logger.info("\\n Integration Tests:")
        self.check_seedling_loader()

        logger.debug("=" * 70)
        logger.info(" Summary")
        logger.debug("=" * 70)
        logger.info(f" Passed: {self.passed}")
        if self.warnings:
            logger.info(f"  Warnings: {self.warnings}")
        if self.failed:
            logger.info(f" Failed: {self.failed}")

        if self.failed == 0 and self.warnings == 0:
            logger.info("\\n Governance is fully activated!")
            return True
        elif self.failed == 0:
            logger.info(f"\\n  Governance is mostly activated ({self.warnings} warnings)")
            return True
        else:
            logger.info(f"\\n Governance activation failed ({self.failed} critical issues)")
            logger.info("\\n Next Steps:")
            logger.info("   1. Review ACTIVATION_GUIDE.md for troubleshooting")
            logger.info("   2. Verify all files copied from wizard output")
            logger.info("   3. Restart IDE and try again")
            return False

'''


def _main_and_entry_section() -> str:
    return """
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify governance activation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--project",
        "-p",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )

    args = parser.parse_args()

    verifier = GovernanceVerifier(project_root=args.project, verbose=args.verbose)
    success = verifier.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
    """
