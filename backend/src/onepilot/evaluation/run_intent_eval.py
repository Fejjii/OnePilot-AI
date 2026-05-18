"""Deterministic intent-classifier evaluation harness.

Reads a JSONL file of ``{"message": ..., "expected_intent": ...}`` rows,
runs the rule-based classifier, and prints a summary report:

    total
    correct
    accuracy
    confusion summary (expected -> {predicted: count})

No OpenAI key required. Usage:

    python -m onepilot.evaluation.run_intent_eval
    python -m onepilot.evaluation.run_intent_eval --dataset path/to/file.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from onepilot.agents.intent_classifier import classify
from onepilot.core.constants import Intent

DEFAULT_DATASET = (
    Path(__file__).parent / "datasets" / "intent_eval.jsonl"
)


@dataclass(slots=True)
class EvalReport:
    total: int = 0
    correct: int = 0
    per_intent_correct: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    per_intent_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    confusion: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    failures: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "per_intent_accuracy": {
                k: round(self.per_intent_correct[k] / v, 4) if v else 0.0
                for k, v in self.per_intent_total.items()
            },
            "confusion": {k: dict(v) for k, v in self.confusion.items()},
            "failures": [
                {"message": m, "expected": e, "predicted": p}
                for m, e, p in self.failures
            ],
        }


def evaluate(rows: list[dict]) -> EvalReport:
    report = EvalReport()
    for row in rows:
        message = str(row.get("message", "")).strip()
        expected = str(row.get("expected_intent", "")).strip()
        if not message or not expected:
            continue
        try:
            Intent(expected)
        except ValueError:
            continue

        result = classify(message)
        predicted = result.intent.value

        report.total += 1
        report.per_intent_total[expected] += 1
        report.confusion[expected][predicted] += 1
        if predicted == expected:
            report.correct += 1
            report.per_intent_correct[expected] += 1
        else:
            report.failures.append((message, expected, predicted))
    return report


def load_dataset(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run intent classifier evaluation")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--json", action="store_true", help="Print JSON output only")
    args = parser.parse_args(argv)

    rows = load_dataset(args.dataset)
    report = evaluate(rows)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"Dataset: {args.dataset}")
    print(f"Total:    {report.total}")
    print(f"Correct:  {report.correct}")
    print(f"Accuracy: {report.accuracy:.2%}")
    print()
    print("Per-intent accuracy:")
    for intent, total in sorted(report.per_intent_total.items()):
        correct = report.per_intent_correct[intent]
        pct = (correct / total) if total else 0.0
        print(f"  {intent:<22} {correct}/{total}  ({pct:.0%})")
    print()
    print("Confusion (expected -> predicted):")
    for expected in sorted(report.confusion):
        for predicted, count in sorted(report.confusion[expected].items()):
            marker = "" if expected == predicted else "  <-- mismatch"
            print(f"  {expected:<22} -> {predicted:<22} {count}{marker}")
    if report.failures:
        print()
        print("Failures:")
        for message, expected, predicted in report.failures:
            print(f"  expected={expected:<20} predicted={predicted:<20} | {message!r}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
