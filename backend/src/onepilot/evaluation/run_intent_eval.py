"""Deterministic intent and routing evaluation harness.

Reads JSONL rows with expected_intent and optional expected_message_class,
runs rule-based classifiers, and writes reports to reports/evaluation/.

No OpenAI key required.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from onepilot.agents.intent_classifier import classify
from onepilot.agents.message_classifier import classify_message
from onepilot.core.constants import Intent, MessageClass
from onepilot.evaluation.reporting import REPORT_DIR, utc_now_iso

DEFAULT_DATASET = Path(__file__).parent / "datasets" / "intent_eval.jsonl"


@dataclass(slots=True)
class EvalReport:
    total: int = 0
    correct: int = 0
    routing_total: int = 0
    routing_correct: int = 0
    per_intent_correct: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    per_intent_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    confusion: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    failures: list[dict[str, str]] = field(default_factory=list)
    case_results: list[dict[str, object]] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now_iso)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    @property
    def routing_accuracy(self) -> float:
        return self.routing_correct / self.routing_total if self.routing_total else 0.0

    def to_dict(self) -> dict:
        return {
            "test_name": "intent_and_routing",
            "timestamp": self.timestamp,
            "total": self.total,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "intent_accuracy": round(self.accuracy, 4),
            "routing_total": self.routing_total,
            "routing_correct": self.routing_correct,
            "routing_accuracy": round(self.routing_accuracy, 4),
            "per_intent_accuracy": {
                k: round(self.per_intent_correct[k] / v, 4) if v else 0.0
                for k, v in self.per_intent_total.items()
            },
            "confusion": {k: dict(v) for k, v in self.confusion.items()},
            "failures": self.failures,
            "case_results": self.case_results,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Intent & Routing Evaluation Report",
            "",
            f"**Generated:** {self.timestamp}",
            "",
            "## Summary",
            "",
            f"- **Total cases:** {self.total}",
            f"- **Intent accuracy:** {self.accuracy:.2%}",
            f"- **Routing accuracy:** {self.routing_accuracy:.2%}",
            "",
            "## Per-intent accuracy",
            "",
            "| Intent | Correct | Total | Accuracy |",
            "|--------|---------|-------|----------|",
        ]
        for intent in sorted(self.per_intent_total):
            correct = self.per_intent_correct[intent]
            total = self.per_intent_total[intent]
            pct = (correct / total) if total else 0.0
            lines.append(f"| {intent} | {correct} | {total} | {pct:.0%} |")

        if self.failures:
            lines.extend([
                "",
                "## Failures",
                "",
                "| Message | Expected | Predicted | Suite |",
                "|---------|----------|-----------|-------|",
            ])
            for row in self.failures[:20]:
                msg = str(row.get("message", "")).replace("|", "\\|")[:60]
                lines.append(
                    f"| {msg} | {row.get('expected', '')} | {row.get('predicted', '')} | {row.get('suite', '')} |"
                )
        return "\n".join(lines)


def evaluate(rows: list[dict]) -> EvalReport:
    report = EvalReport()
    for row in rows:
        message = str(row.get("message", "")).strip()
        expected = str(row.get("expected_intent", "")).strip()
        expected_class = str(row.get("expected_message_class", "")).strip()
        category = str(row.get("category", "")).strip()
        if not message or not expected:
            continue
        try:
            Intent(expected)
        except ValueError:
            continue

        msg_result = classify_message(message)
        predicted_class = msg_result.message_class.value
        intent_result = classify(message, message_class=msg_result.message_class)
        predicted = intent_result.intent.value

        report.total += 1
        report.per_intent_total[expected] += 1
        report.confusion[expected][predicted] += 1

        intent_ok = predicted == expected
        if intent_ok:
            report.correct += 1
            report.per_intent_correct[expected] += 1

        routing_ok: bool | None = None
        if expected_class:
            try:
                MessageClass(expected_class)
            except ValueError:
                expected_class = ""
        if expected_class:
            report.routing_total += 1
            routing_ok = predicted_class == expected_class
            if routing_ok:
                report.routing_correct += 1

        passed = intent_ok and (routing_ok is None or routing_ok)
        case = {
            "message": message,
            "category": category,
            "expected_intent": expected,
            "predicted_intent": predicted,
            "intent_pass": intent_ok,
            "passed": passed,
        }
        if expected_class:
            case["expected_message_class"] = expected_class
            case["predicted_message_class"] = predicted_class
            case["routing_pass"] = routing_ok
        report.case_results.append(case)

        if not intent_ok:
            report.failures.append({
                "message": message,
                "expected": expected,
                "predicted": predicted,
                "suite": "intent",
                "category": category,
            })
        elif routing_ok is False:
            report.failures.append({
                "message": message,
                "expected": expected_class,
                "predicted": case.get("predicted_message_class", ""),
                "suite": "routing",
                "category": category,
            })
    return report


def load_dataset(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_reports(report: EvalReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    (output_dir / "intent_eval_latest.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (output_dir / "intent_eval_latest.md").write_text(report.to_markdown(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run intent/routing evaluation")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    rows = load_dataset(args.dataset)
    report = evaluate(rows)
    write_reports(report, args.output_dir)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"Dataset: {args.dataset}")
    print(f"Intent accuracy:   {report.accuracy:.2%} ({report.correct}/{report.total})")
    print(f"Routing accuracy:  {report.routing_accuracy:.2%} ({report.routing_correct}/{report.routing_total})")
    print(f"Failures: {len(report.failures)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
