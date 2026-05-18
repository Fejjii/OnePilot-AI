"""Run all evaluation harnesses and generate combined report.

Runs:
1. Intent classification evaluation
2. RAG retrieval evaluation

Outputs combined JSON and Markdown reports.

Usage:

    python -m onepilot.evaluation.run_all_evals
    python -m onepilot.evaluation.run_all_evals --output-dir custom/path
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from onepilot.evaluation.run_intent_eval import main as intent_eval_main
from onepilot.evaluation.run_rag_eval import main as rag_eval_main

DEFAULT_OUTPUT_DIR = Path("reports/evaluation")


def generate_combined_report(output_dir: Path) -> dict:
    """Load individual eval reports and combine them."""
    combined = {
        "test_suite": "onepilot_ai_comprehensive_eval",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": {},
        "summary": {},
    }

    # Load intent eval report
    intent_json = output_dir / "intent_eval_latest.json"
    if intent_json.exists():
        intent_data = json.loads(intent_json.read_text())
        combined["tests"]["intent_classification"] = intent_data
        combined["summary"]["intent_accuracy"] = intent_data.get("accuracy", 0.0)

    # Load RAG eval report
    rag_json = output_dir / "rag_eval_latest.json"
    if rag_json.exists():
        rag_data = json.loads(rag_json.read_text())
        combined["tests"]["rag_retrieval"] = rag_data
        combined["summary"]["rag_precision_at_3"] = rag_data.get("precision_at_3", 0.0)
        combined["summary"]["rag_recall_at_3"] = rag_data.get("recall_at_3", 0.0)

    # Calculate overall pass/fail
    intent_pass = combined["summary"].get("intent_accuracy", 0.0) >= 0.85
    rag_pass = combined["summary"].get("rag_precision_at_3", 0.0) >= 0.70

    combined["summary"]["overall_pass"] = intent_pass and rag_pass
    combined["summary"]["tests_passed"] = sum([intent_pass, rag_pass])
    combined["summary"]["tests_total"] = 2

    return combined


def generate_combined_markdown(combined: dict, output_dir: Path) -> str:
    """Generate combined Markdown report."""
    lines = [
        "# OnePilot AI Evaluation Summary",
        "",
        f"**Generated:** {combined['timestamp']}",
        "",
        "## Overall Results",
        "",
        f"- **Tests passed:** {combined['summary']['tests_passed']}/{combined['summary']['tests_total']}",
        f"- **Overall status:** {'✅ PASS' if combined['summary']['overall_pass'] else '❌ FAIL'}",
        "",
        "## Test Results",
        "",
        "### Intent Classification",
        "",
    ]

    if "intent_classification" in combined["tests"]:
        intent = combined["tests"]["intent_classification"]
        lines.append(f"- **Accuracy:** {intent.get('accuracy', 0.0):.2%}")
        lines.append(f"- **Total cases:** {intent.get('total', 0)}")
        lines.append(f"- **Correct:** {intent.get('correct', 0)}")
        lines.append(f"- **Status:** {'✅ PASS (≥85%)' if intent.get('accuracy', 0.0) >= 0.85 else '❌ FAIL (<85%)'}")
        lines.append("")
        lines.append(f"[View detailed intent eval report](intent_eval_latest.md)")
    else:
        lines.append("- ⚠️ No data available")

    lines.extend([
        "",
        "### RAG Retrieval",
        "",
    ])

    if "rag_retrieval" in combined["tests"]:
        rag = combined["tests"]["rag_retrieval"]
        lines.append(f"- **Precision@3:** {rag.get('precision_at_3', 0.0):.2%}")
        lines.append(f"- **Recall@3:** {rag.get('recall_at_3', 0.0):.2%}")
        lines.append(f"- **Total queries:** {rag.get('total_queries', 0)}")
        lines.append(f"- **Status:** {'✅ PASS (≥70%)' if rag.get('precision_at_3', 0.0) >= 0.70 else '❌ FAIL (<70%)'}")
        lines.append("")
        lines.append(f"[View detailed RAG eval report](rag_eval_latest.md)")
    else:
        lines.append("- ⚠️ No data available")

    lines.extend([
        "",
        "## Recommendations",
        "",
    ])

    if not combined["summary"]["overall_pass"]:
        lines.append("The evaluation suite has identified areas for improvement:")
        lines.append("")
        if "intent_classification" in combined["tests"]:
            intent_acc = combined["tests"]["intent_classification"].get("accuracy", 0.0)
            if intent_acc < 0.85:
                lines.append(f"- **Intent classification:** Accuracy ({intent_acc:.2%}) is below target (85%). Review confusion matrix and add more training examples.")
        if "rag_retrieval" in combined["tests"]:
            rag_prec = combined["tests"]["rag_retrieval"].get("precision_at_3", 0.0)
            if rag_prec < 0.70:
                lines.append(f"- **RAG retrieval:** Precision@3 ({rag_prec:.2%}) is below target (70%). Consider improving embeddings or document chunking strategy.")
    else:
        lines.append("All evaluation metrics meet or exceed target thresholds. The system is performing well.")

    lines.extend([
        "",
        "## Next Steps",
        "",
        "1. Review individual test reports for detailed breakdowns",
        "2. Address any failing tests before deployment",
        "3. Consider running continuous evaluation in CI/CD pipeline",
        "4. Expand test coverage with additional edge cases",
        "",
    ])

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all evaluation harnesses")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-intent", action="store_true", help="Skip intent evaluation")
    parser.add_argument("--skip-rag", action="store_true", help="Skip RAG evaluation")
    args = parser.parse_args(argv)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("OnePilot AI Comprehensive Evaluation Suite")
    print("=" * 60)
    print()

    # Run intent evaluation
    if not args.skip_intent:
        print("Running intent classification evaluation...")
        intent_eval_main(["--output-dir", str(output_dir)])
        print()

    # Run RAG evaluation
    if not args.skip_rag:
        print("Running RAG retrieval evaluation...")
        rag_eval_main(["--output-dir", str(output_dir)])
        print()

    # Generate combined report
    print("Generating combined report...")
    combined = generate_combined_report(output_dir)
    combined_json = output_dir / "latest.json"
    combined_json.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print(f"[OK] Combined JSON: {combined_json}")

    combined_md = output_dir / "latest.md"
    combined_md.write_text(generate_combined_markdown(combined, output_dir), encoding="utf-8")
    print(f"[OK] Combined Markdown: {combined_md}")

    print()
    print("=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    print(f"Overall status: {'PASS' if combined['summary']['overall_pass'] else 'FAIL'}")
    print(f"Tests passed:   {combined['summary']['tests_passed']}/{combined['summary']['tests_total']}")

    if "intent_accuracy" in combined["summary"]:
        print(f"Intent accuracy: {combined['summary']['intent_accuracy']:.2%}")
    if "rag_precision_at_3" in combined["summary"]:
        print(f"RAG precision@3: {combined['summary']['rag_precision_at_3']:.2%}")

    print()
    print(f"View full report: {combined_md}")
    print()

    return 0 if combined["summary"]["overall_pass"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
