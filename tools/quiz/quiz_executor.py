#!/usr/bin/env python3
"""Providence Architecture Quiz Executor — interactive multiple-choice quiz."""

import json
import sys
from pathlib import Path
from typing import Any


class QuizExecutor:
    def __init__(self, quiz_file: Path | None = None) -> None:
        if quiz_file is None:
            project_root = Path(__file__).resolve().parents[2]
            quiz_file = project_root / "tools" / "quiz" / "quiz_questions.json"

        self.quiz_file = quiz_file
        try:
            with open(self.quiz_file, encoding="utf-8") as f:
                self.quiz_data: dict[str, Any] = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Quiz file not found: {self.quiz_file}")
            sys.exit(2)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in quiz file: {e}")
            sys.exit(2)

    # ------------------------------------------------------------------
    # Interactive mode
    # ------------------------------------------------------------------

    def run(self) -> bool:
        """Run the quiz interactively. Returns True if the user passes."""
        meta = self.quiz_data["metadata"]
        questions: list[dict[str, Any]] = self.quiz_data["questions"]
        threshold: int = meta.get("pass_threshold", 70)

        print(f"\n{'=' * 60}")
        print(f"  {meta['title']}")
        print(f"  {meta['description']}")
        print(f"  Questions: {len(questions)}  |  Pass threshold: {threshold}%")
        print(f"{'=' * 60}\n")
        print("Answer each question by typing the option number (1-4).\n")

        correct = 0
        for i, q in enumerate(questions, 1):
            print(f"Q{i}/{len(questions)} [{q['difficulty'].upper()}] {q['question']}")
            for j, opt in enumerate(q["options"], 1):
                print(f"  {j}. {opt}")

            answer = self._prompt_answer(len(q["options"]))
            expected = q["correct_answer"] + 1  # JSON uses 0-based index

            if answer == expected:
                print("  Correct!\n")
                correct += 1
            else:
                print(f"  Wrong. Correct answer: {expected}. {q['explanation']}\n")

        score = int(correct / len(questions) * 100)
        passed = score >= threshold

        print(f"{'=' * 60}")
        print(f"  Result: {correct}/{len(questions)} correct  ({score}%)")
        print(f"  Status: {'PASS' if passed else 'FAIL'}  (threshold: {threshold}%)")
        print(f"{'=' * 60}\n")
        return passed

    # ------------------------------------------------------------------
    # Silent / CI mode — validate file + return pass stub
    # ------------------------------------------------------------------

    def run_silent(self) -> bool:
        """Validate quiz file is readable and structurally correct. No prompts."""
        meta = self.quiz_data.get("metadata", {})
        questions = self.quiz_data.get("questions", [])

        if not questions:
            print("ERROR: Quiz has no questions.")
            return False

        threshold = meta.get("pass_threshold", 70)
        title = meta.get("title", "Unknown")
        print(
            f"Quiz OK: '{title}' — {len(questions)} questions, threshold {threshold}%"
        )
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _prompt_answer(self, n_options: int) -> int:
        while True:
            try:
                raw = input(f"  Your answer (1-{n_options}): ").strip()
            except EOFError:
                raise SystemExit("Quiz interrupted: stdin closed.") from None
            try:
                value = int(raw)
                if 1 <= value <= n_options:
                    return value
                print(f"  Please enter a number between 1 and {n_options}.")
            except ValueError:
                print(f"  Please enter a number between 1 and {n_options}.")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Providence Architecture Foundation Quiz"
    )
    parser.add_argument("--file", type=Path, help="Path to quiz JSON file (optional)")
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Validate quiz file only — no interactive prompts (for CI)",
    )
    args = parser.parse_args()

    executor = QuizExecutor(quiz_file=args.file)

    if args.silent:
        return 0 if executor.run_silent() else 1

    passed = executor.run()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
