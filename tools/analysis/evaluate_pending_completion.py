#!/usr/bin/env python3
"""
Providence Analysis Pending Items Completion Evaluator

Workflow para avaliar se pendências foram implementadas e movê-las para .analysis/done

Critérios de Conclusão (conforme .analysis/README.md):
1. proposal.md - Proposta do trabalho
2. tasks.md com todos os itens checkados ✓
3. specs/*/spec.md - Especificações
4. assessment.md e/ou summary.md - Evidência de execução

Um item é considerado IMPLEMENTADO quando:
- É uma pasta com estrutura completa + evidence, OU
- É um arquivo de design que está referenciado em código/docs, OU
- É um arquivo de discovery/analysis com findings atualizados, OU
- Tem status marker no nome (tipo "2026-06-11-...-DONE.md")
"""

import json
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from providence_core.utils.text_io import read_text_utf8, write_text_utf8

# Configuração
ANALYSIS_DIR = Path("/home/sergio/dev/providence/.analysis")
PENDING_DIR = ANALYSIS_DIR / "pending"
DONE_DIR = ANALYSIS_DIR / "done"
WORKFLOW_LOG = ANALYSIS_DIR / ".completion_audit.log"

# Tipos de items que rastreamos
ITEM_TYPES = {
    "discovery": ["discovery", "discovery.md"],
    "design": ["design.md"],
    "analysis": ["analysis.md"],
    "report": ["report.md"],
    "spec": ["spec.md"],
    "plan": ["plan.md"],
    "workflow": ["workflow", "workflow.md"],
}


def _classify_done_marker(name: str) -> tuple[str, bool, str, list[str]] | None:
    if "DONE" in name or "-completed" in name or "-finished" in name:
        return "done", True, "Marked as DONE in filename", ["✓ DONE marker in name"]
    return None


def _classify_report_file(
    file_type: str, has_completion_markers: bool, has_findings: bool
) -> tuple[str, bool, str, list[str]] | None:
    if file_type == "report" and (has_completion_markers or has_findings):
        return (
            "done",
            True,
            "Report file with findings/conclusions",
            [f"✓ {file_type} with findings"],
        )
    return None


def _classify_design_file(file_type: str) -> tuple[str, bool, str, list[str]] | None:
    if file_type == "design":
        # Design docs geralmente ficam em pending até serem implementadas
        return "pending", False, "Design document (move when implemented)", []
    return None


def _classify_discovery_file(
    file_type: str, content: str, has_findings: bool, has_substantial_content: bool
) -> tuple[str, bool, str, list[str]] | None:
    if file_type != "discovery":
        return None
    # Discovery files: move se tem conteúdo substancial
    if has_substantial_content and (has_findings or len(content) > 1000):
        return (
            "done",
            True,
            "Discovery file with substantial findings",
            ["✓ Discovery with content"],
        )
    return "pending", False, "Discovery file (needs more content)", []


def _classify_workflow_file(
    file_type: str, has_substantial_content: bool
) -> tuple[str, bool, str, list[str]] | None:
    if file_type != "workflow":
        return None
    # Workflow files: move se tem implementação
    if has_substantial_content:
        return "done", True, "Workflow file (complete)", ["✓ Workflow documented"]
    return "pending", False, "Workflow file (incomplete)", []


def _classify_analysis_file(
    file_type: str, has_findings: bool, has_substantial_content: bool
) -> tuple[str, bool, str, list[str]] | None:
    if file_type != "analysis":
        return None
    # Analysis files: move se tem findings
    if has_findings and has_substantial_content:
        return "done", True, "Analysis file with findings", ["✓ Analysis documented"]
    return "pending", False, "Analysis file (review needed)", []


def _classify_unknown_file(
    file_type: str, has_completion_markers: bool, has_substantial_content: bool
) -> tuple[str, bool, str, list[str]] | None:
    if file_type != "unknown":
        return None
    # Unknown files: move apenas se explicitamente marcado
    if has_completion_markers and has_substantial_content:
        return (
            "done",
            True,
            "File with completion markers and content",
            ["✓ Content documented"],
        )
    return None


class CompletionEvaluator:
    """Avalia se um item pendente foi implementado."""

    def __init__(self) -> None:
        self.audit_log: list[dict[str, Any]] = []
        self.moved_items: list[str] = []
        self.kept_items: list[str] = []

    def evaluate_item(self, item_path: Path) -> dict[str, Any]:
        """
        Avalia se um item foi implementado.

        Returns:
            {
                "name": str,
                "type": str,
                "status": "done" | "pending",
                "reason": str,
                "evidence": [list of completion indicators],
                "move": bool  # True se deve mover para done/
            }
        """
        name = item_path.name
        evidence: list[str] = []

        # 1. Checar se é pasta
        if item_path.is_dir():
            return self._evaluate_folder(item_path, name, evidence)

        # 2. Checar se é arquivo
        if item_path.is_file():
            return self._evaluate_file(item_path, name, evidence)

        return {
            "name": name,
            "type": "unknown",
            "status": "pending",
            "reason": "Item is neither file nor directory",
            "evidence": [],
            "move": False,
        }

    def _evaluate_folder(
        self, folder_path: Path, name: str, evidence: list[str]
    ) -> dict[str, Any]:
        """Avalia pasta de análise."""
        files = list(folder_path.glob("*"))
        file_names = [f.name for f in files]

        # Critérios de conclusão
        has_proposal = "proposal.md" in file_names or "PROPOSAL.md" in file_names
        has_tasks_done = self._check_tasks_completed(folder_path)
        has_specs = any(
            f.name.startswith("spec") or "spec" in f.name or "SPEC" in f.name
            for f in files
            if f.is_dir()
        ) or any(
            "spec" in f.name.lower()
            for f in files
            if f.is_file() and f.name.endswith(".md")
        )
        has_evidence = (
            "assessment.md" in file_names
            or "summary.md" in file_names
            or "INDEX.md" in file_names
            or "index.md" in file_names
        ) or (
            "report.md" in file_names
            or any(
                f.name.endswith("-report.md") or f.name.endswith("-REPORT.md")
                for f in files
            )
        )

        # Contar arquivos .md como indicador de conteúdo
        md_files = [f for f in files if f.name.endswith(".md")]
        has_substantial_content = len(md_files) >= 5  # 5+ docs = substantial

        # Collect evidence
        if has_proposal:
            evidence.append("✓ proposal.md")
        if has_tasks_done:
            evidence.append("✓ tasks.md (completed)")
        if has_specs:
            evidence.append("✓ specs/ folder or spec files")
        if has_evidence:
            evidence.append("✓ assessment/summary/index/report")
        if has_substantial_content:
            evidence.append(f"✓ substantial content ({len(md_files)} MD files)")

        # Determine status
        status = "pending"
        move = False
        reason = ""

        # Critério 1: Completamente estruturado
        if has_proposal and has_tasks_done and has_specs and has_evidence:
            status = "done"
            move = True
            reason = "Complete structure with all required components"
        # Critério 2: Tem evidence + substantial content (indicador forte)
        elif has_evidence and (has_proposal or has_substantial_content):
            status = "done"
            move = True
            reason = "Evidence + substantial documentation"
        # Critério 3: Completado no nome
        elif "DONE" in name or "-completed" in name or "-finished" in name:
            status = "done"
            move = True
            reason = "Marked as DONE/completed in folder name"
        # Critério 4: Tem muitas evidências, mesmo sem proposal formal
        elif len(evidence) >= 2:
            # Mais permissivo: se tem evidence, pode estar pronto
            status = "done"
            move = True
            reason = f"Multiple completion indicators ({len(evidence)})"

        return {
            "name": name,
            "type": "folder",
            "status": status,
            "reason": reason,
            "evidence": evidence,
            "move": move,
        }

    def _evaluate_file(
        self, file_path: Path, name: str, evidence: list[str]
    ) -> dict[str, Any]:
        """Avalia arquivo de análise."""
        file_type = "unknown"

        # Detectar tipo
        for ftype, patterns in ITEM_TYPES.items():
            if any(p in name for p in patterns):
                file_type = ftype
                break

        # Ler arquivo para análise
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""

        # Indicadores de conclusão
        has_completion_markers = any(
            marker in content
            for marker in [
                "## Summary",
                "## Conclusão",
                "## Recomendações",
                "## Próximos Passos",
                "## Checklist",
                "✓",
                "[x]",
                "COMPLETED",
                "DONE",
            ]
        )

        has_findings = any(
            section in content
            for section in [
                "## Findings",
                "## Achados",
                "## Results",
                "## Resultados",
                "## Implementation",
                "## Status",
                "## Conclusions",
                "## Conclusões",
            ]
        )

        # Checar tamanho do arquivo (>500 bytes = conteúdo substancial)
        file_size = file_path.stat().st_size
        has_substantial_content = file_size > 500

        status, move, reason = self._classify_file(
            name=name,
            file_type=file_type,
            content=content,
            has_completion_markers=has_completion_markers,
            has_findings=has_findings,
            has_substantial_content=has_substantial_content,
            evidence=evidence,
        )

        if not evidence:
            evidence = [f"→ {file_type} file"]

        return {
            "name": name,
            "type": file_type,
            "status": status,
            "reason": reason,
            "evidence": evidence,
            "move": move,
        }

    def _classify_file(
        self,
        *,
        name: str,
        file_type: str,
        content: str,
        has_completion_markers: bool,
        has_findings: bool,
        has_substantial_content: bool,
        evidence: list[str],
    ) -> tuple[str, bool, str]:
        """Aplica os critérios de classificação por tipo de arquivo."""
        classifiers: list[Callable[[], tuple[str, bool, str, list[str]] | None]] = [
            lambda: _classify_done_marker(name),
            lambda: _classify_report_file(
                file_type, has_completion_markers, has_findings
            ),
            lambda: _classify_design_file(file_type),
            lambda: _classify_discovery_file(
                file_type, content, has_findings, has_substantial_content
            ),
            lambda: _classify_workflow_file(file_type, has_substantial_content),
            lambda: _classify_analysis_file(
                file_type, has_findings, has_substantial_content
            ),
            lambda: _classify_unknown_file(
                file_type, has_completion_markers, has_substantial_content
            ),
        ]

        for classify in classifiers:
            result = classify()
            if result is not None:
                status, move, reason, extra_evidence = result
                evidence.extend(extra_evidence)
                return status, move, reason

        return "pending", False, ""

    def _check_tasks_completed(self, folder_path: Path) -> bool:
        """Verifica se tasks.md tem todos os itens checkados."""
        tasks_file = folder_path / "tasks.md"
        if not tasks_file.exists():
            return False

        try:
            content = read_text_utf8(tasks_file)
            # Contar [ ] vs [x]
            unchecked = content.count("- [ ]")
            checked = content.count("- [x]")

            # Se não tem unchecked E tem pelo menos um checked, está completo
            return unchecked == 0 and checked > 0
        except OSError:
            return False

    def process_pending_items(
        self, dry_run: bool = False, interactive: bool = False
    ) -> None:
        """Processa todos os itens em pending."""
        if not PENDING_DIR.exists():
            print(f"❌ Pending directory not found: {PENDING_DIR}")
            return

        print(f"\n{'=' * 70}")
        print("Providence Analysis Completion Evaluator")
        print(f"{'=' * 70}")
        print(f"📁 Scanning: {PENDING_DIR}")
        print(f"Dry-run: {'Yes' if dry_run else 'No'}")
        print(f"Interactive: {'Yes' if interactive else 'No'}\n")

        items = sorted([p for p in PENDING_DIR.iterdir()])
        done_count = 0
        pending_count = 0
        evaluations = []

        for item_path in items:
            # Skip dot files
            if item_path.name.startswith("."):
                continue

            evaluation = self.evaluate_item(item_path)

            # Print result
            status_icon = "✓" if evaluation["move"] else "→"
            status_text = evaluation["status"].upper()
            print(f"{status_icon} {evaluation['name']:<50} [{status_text}]")
            print(f"  Type: {evaluation['type']}")
            print(f"  Reason: {evaluation['reason']}")
            if evaluation["evidence"]:
                print(f"  Evidence: {', '.join(evaluation['evidence'])}")
            print()

            # Track
            self.audit_log.append(evaluation)
            evaluations.append(evaluation)

            if evaluation["move"]:
                done_count += 1
                self.moved_items.append(evaluation["name"])
            else:
                pending_count += 1
                self.kept_items.append(evaluation["name"])

        # Interactive mode: ask user
        if interactive:
            self._interactive_mode(evaluations, pending_count, done_count)

        # Summary
        print(f"{'=' * 70}")
        print("Summary:")
        print(f"  ✓ Ready to move to done/: {done_count}")
        print(f"  → Staying in pending/: {pending_count}")
        print(f"{'=' * 70}\n")

        # Perform moves if not dry-run
        if not dry_run and done_count > 0:
            self._perform_moves()

        # Save audit log
        self._save_audit_log()

    def _interactive_mode(
        self, evaluations: list[dict[str, Any]], pending_count: int, done_count: int
    ) -> None:
        """Modo interativo para escolher manualmente quais itens mover."""
        print("\n" + "=" * 70)
        print("INTERACTIVE MODE: Review pending items for manual moves")
        print("=" * 70 + "\n")

        # Items sugeridos para mover
        suggested = [e for e in evaluations if e["move"]]
        if suggested:
            print(f"✓ Suggested for move ({len(suggested)}):\n")
            for i, e in enumerate(suggested, 1):
                print(f"  {i}. {e['name']}")
            print()

        # Items questionáveis (pendentes)
        questionable = [
            e
            for e in evaluations
            if not e["move"] and "discovery" in e["type"] or "workflow" in e["type"]
        ]
        if questionable:
            print(f"❓ Manual review candidates ({len(questionable)}):\n")
            for i, e in enumerate(questionable, 1):
                print(f"  {i}. {e['name']}")
                print(f"     → {e['reason']}")
            print()

            # Oferecer prompt para incluir manualmente
            resp = input(
                "Enter item numbers to move (comma-separated, or 'skip'): "
            ).strip()
            if resp.lower() != "skip" and resp:
                try:
                    selected_indices = [int(x.strip()) - 1 for x in resp.split(",")]
                    for idx in selected_indices:
                        if 0 <= idx < len(questionable):
                            questionable[idx]["move"] = True
                            self.moved_items.append(questionable[idx]["name"])
                            if questionable[idx]["name"] in self.kept_items:
                                self.kept_items.remove(questionable[idx]["name"])
                            print(f"✓ Added: {questionable[idx]['name']}")
                except ValueError:
                    print("Invalid input")

        print()

    def _perform_moves(self) -> None:
        """Move completed items to done/"""
        print("Moving completed items...\n")

        for evaluation in self.audit_log:
            if not evaluation["move"]:
                continue

            src = PENDING_DIR / evaluation["name"]
            dst = DONE_DIR / evaluation["name"]

            if not src.exists():
                print(f"⚠️  Source not found: {src}")
                continue

            if dst.exists():
                print(f"⚠️  Destination already exists: {dst}")
                continue

            try:
                if src.is_dir():
                    shutil.move(str(src), str(dst))
                else:
                    shutil.move(str(src), str(dst))
                print(f"✓ Moved: {evaluation['name']}")
            except Exception as e:
                print(f"❌ Error moving {evaluation['name']}: {e}")

        print()

    def _save_audit_log(self) -> None:
        """Salva log de auditoria."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "pending_dir": str(PENDING_DIR),
            "done_dir": str(DONE_DIR),
            "moved_count": len(self.moved_items),
            "kept_count": len(self.kept_items),
            "moved_items": self.moved_items,
            "kept_items": self.kept_items,
            "details": self.audit_log,
        }

        try:
            write_text_utf8(WORKFLOW_LOG, json.dumps(log_data, indent=2))
            print(f"📋 Audit log saved: {WORKFLOW_LOG}")
        except Exception as e:
            print(f"⚠️  Could not save audit log: {e}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate and move completed analysis items"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate moves without actually moving files",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode: choose which items to move",
    )

    args = parser.parse_args()

    evaluator = CompletionEvaluator()
    evaluator.process_pending_items(dry_run=args.dry_run, interactive=args.interactive)


if __name__ == "__main__":
    main()
