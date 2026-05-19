"""Run all evaluation harnesses and write combined latest.json / latest.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from onepilot.evaluation.reporting import (
    REPORT_DIR,
    build_combined_summary,
    combined_markdown,
    write_json,
    write_markdown,
)
from onepilot.evaluation.run_intent_eval import evaluate as evaluate_intent
from onepilot.evaluation.run_intent_eval import load_dataset as load_intent_dataset
from onepilot.evaluation.run_intent_eval import DEFAULT_DATASET as INTENT_DATASET
from onepilot.evaluation.run_rag_eval import DEFAULT_DATASET as RAG_DATASET
from onepilot.evaluation.run_rag_eval import evaluate_rag, load_dataset as load_rag_dataset
from onepilot.evaluation.run_rag_eval import load_demo_index, write_reports as write_rag_reports
from onepilot.evaluation.run_intent_eval import write_reports as write_intent_reports
from onepilot.evaluation.run_safety_eval import DEFAULT_DATASET as SAFETY_DATASET
from onepilot.evaluation.run_safety_eval import evaluate as evaluate_safety
from onepilot.evaluation.run_safety_eval import load_dataset as load_safety_dataset
from onepilot.evaluation.run_safety_eval import write_reports as write_safety_reports

DEFAULT_INTENT = INTENT_DATASET
DEFAULT_RAG = RAG_DATASET
DEFAULT_SAFETY = SAFETY_DATASET


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all evaluation harnesses")
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--skip-intent", action="store_true")
    parser.add_argument("--skip-rag", action="store_true")
    parser.add_argument("--skip-safety", action="store_true")
    args = parser.parse_args(argv)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("OnePilot AI — Evaluation & Quality Suite")
    print("=" * 60)

    intent_report: dict | None = None
    rag_report: dict | None = None
    safety_report: dict | None = None

    if not args.skip_intent:
        print("Running intent & routing evaluation…")
        intent = evaluate_intent(load_intent_dataset(DEFAULT_INTENT))
        write_intent_reports(intent, output_dir)
        intent_report = intent.to_dict()
        print(f"  Intent: {intent.accuracy:.1%}  Routing: {intent.routing_accuracy:.1%}")

    if not args.skip_rag:
        print("Running RAG golden evaluation…")
        rag = evaluate_rag(load_rag_dataset(DEFAULT_RAG), load_demo_index())
        write_rag_reports(rag, output_dir)
        rag_report = rag.to_dict()
        print(f"  RAG golden pass: {rag.rag_golden_pass_rate:.1%}")

    if not args.skip_safety:
        print("Running safety & HITL evaluation…")
        safety = evaluate_safety(load_safety_dataset(DEFAULT_SAFETY))
        write_safety_reports(safety, output_dir)
        safety_report = safety.to_dict()
        print(f"  Safety pass: {safety.safety_guardrail_pass_rate:.1%}")

    combined = build_combined_summary(
        intent_report=intent_report,
        rag_report=rag_report,
        safety_report=safety_report,
    )
    write_json(output_dir / "latest.json", combined)
    write_markdown(output_dir / "latest.md", combined_markdown(combined))

    print()
    print("Combined report:", output_dir / "latest.json")
    m = combined["metrics"]
    print(f"Total cases: {m['total_cases']}  Failed: {m['failed_cases']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
