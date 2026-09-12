"""User-facing message templates for InteractiveWizard."""

from pathlib import Path


def phase2_instructions_message(
    phase1_path: Path, output_path: Path, copied_files: list[str]
) -> str:
    """Phase2 Instructions Message."""
    files = ", ".join(copied_files)
    return (
        "stage...OK\n"
        f"source: {phase1_path.as_posix()}\n"
        f"target: {output_path.as_posix()}\n"
        f"files...OK ({len(copied_files)}): {files}\n"
    )


def phase3_completed_message() -> str:
    """Phase3 Completed Message."""
    return r"""
 COMPLETE WIZARD FLOW FINISHED!


YOUR GOVERNANCE PROJECT IS READY


 STEP 1: COPY TO YOUR PROJECT
   Copy the complete .providence/ directory to your project:

   Linux/macOS:
     cp -r .providence/ .

   Windows (PowerShell):
     Copy-Item -Path .providence -Destination . -Recurse

 STEP 2: ACTIVATE IN YOUR IDE
   1. Open project in VS Code / Cursor / ChatGPT
   2. Restart IDE
   3. Seedlings auto-activate on project load

 STEP 3: VERIFY
   Run the verification script:

   python .providence/seedlings/verify.py

 STEP 4: REVIEW CONFIGURATION
   Check ACTIVATION_GUIDE.md for your governance setup:

   Linux/macOS: cat .providence/seedlings/ACTIVATION_GUIDE.md
   Windows: Get-Content .providence\seedlings\ACTIVATION_GUIDE.md

 STEP 5: VERIFY SKILLS-FIRST AWARENESS
   providence runtime status
   providence governance validate
   providence skills list
   providence skills run sdd-validate-governance

 STEP 6: PASTE THIS IN YOUR AGENT PROMPT
   Please evaluate governance from project-root files first, then from `.providence`.
   Read `AGENTS.md`, `.providence/agent-instructions.md`, `.providence/metadata.json`,
   and `.providence/source/mandates/mandates.md`. Confirm:
   1) active mandates loaded, 2) current fingerprint, 3) any drift/blockers,
   4) next governed action using `sdd-*` commands only.

   Then complete the M015 bidirectional handshake yourself (do not skip
   this must be a genuine attestation, not a mechanical copy-paste):

     1. providence governance handshake --init
        (generates a challenge JSON with session_id/active_mandates/available_skills)

     2. providence governance handshake --response '<json>'
        where <json> = {
          "agent_id": "<your agent identity>",
          "understood_mandates": [<active mandate IDs from step 1>],
          "skills_to_use": [<skills you intend to invoke, e.g. "sdd-ask">],
          "acknowledged_signature": true,
          "compliance_declaration": true
        }
"""


def phase4_success_message(
    mandates: int, guidelines: int, categories: list[str], final_template_dir: Path
) -> str:
    """Phase4 Success Message."""
    return (
        "phase4...OK\n"
        f"mandates...OK ({mandates})\n"
        f"guidelines...OK ({guidelines})\n"
        f"categories...OK ({', '.join(categories)})\n"
        f"template...OK {final_template_dir}\n"
    )


def phase4_consolidation_failed_message(source_dir: Path, target_dir: Path) -> str:
    """Phase4 Consolidation Failed Message."""
    return (
        "\n Failed to consolidate final template bundle!\n"
        f"   Source: {source_dir.as_posix()}\n"
        f"   Target: {target_dir.as_posix()}"
    )


def phase6_seedlings_success_message(output_base: Path) -> str:
    """Phase6 Seedlings Success Message."""
    return (
        "seed...OK\n"
        "governance.seed.json...OK\n"
        "agent-prep.seed.json...OK\n"
        "compliance.seed.json...OK\n"
        "ACTIVATION_GUIDE.md...OK\n"
        "verify.py...OK\n"
        f"location: {output_base.as_posix()}/.providence/seedlings/\n"
    )
