"""Shared helpers for evaluation report paths and combined summaries."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# backend/reports/evaluation (package lives under backend/src/onepilot/evaluation/)
REPORT_DIR = Path(__file__).resolve().parents[3] / "reports" / "evaluation"
LATEST_JSON = REPORT_DIR / "latest.json"
LATEST_MD = REPORT_DIR / "latest.md"

EMPTY_STATE_MESSAGE = (
    "Evaluation report not generated yet. Run backend evaluation script."
)

RUN_COMMAND = "cd backend && uv run python -m onepilot.evaluation.run_all_evals"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_latest_report() -> dict[str, Any] | None:
    if not LATEST_JSON.exists():
        return None
    try:
        return json.loads(LATEST_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_combined_summary(
    *,
    intent_report: dict[str, Any] | None,
    rag_report: dict[str, Any] | None,
    safety_report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge per-suite reports into API/UI-friendly latest.json shape."""
    failed_cases: list[dict[str, Any]] = []
    total_cases = 0

    intent_accuracy = 0.0
    routing_accuracy = 0.0
    if intent_report:
        intent_accuracy = float(intent_report.get("intent_accuracy", intent_report.get("accuracy", 0.0)))
        routing_accuracy = float(intent_report.get("routing_accuracy", 0.0))
        total_cases += int(intent_report.get("total", 0))
        for row in intent_report.get("failures", []):
            failed_cases.append({"suite": "routing", **row})

    rag_golden_pass_rate = 0.0
    citation_presence_rate = 0.0
    source_hit_rate = 0.0
    weak_evidence_correctness = 0.0
    if rag_report:
        rag_golden_pass_rate = float(rag_report.get("rag_golden_pass_rate", 0.0))
        citation_presence_rate = float(rag_report.get("citation_presence_rate", 0.0))
        source_hit_rate = float(rag_report.get("source_hit_rate", 0.0))
        weak_evidence_correctness = float(rag_report.get("weak_evidence_correctness", 0.0))
        total_cases += int(rag_report.get("total", 0))
        for row in rag_report.get("failures", []):
            failed_cases.append({"suite": "rag", **row})

    safety_guardrail_pass_rate = 0.0
    if safety_report:
        safety_guardrail_pass_rate = float(safety_report.get("safety_guardrail_pass_rate", 0.0))
        total_cases += int(safety_report.get("total", 0))
        for row in safety_report.get("failures", []):
            failed_cases.append({"suite": "safety", **row})

    return {
        "generated_at": utc_now_iso(),
        "status": "complete",
        "run_command": RUN_COMMAND,
        "disclaimer": (
            "These are deterministic evaluation checks for capstone/demo quality. "
            "They are not a replacement for full production RAGAS or human evaluation."
        ),
        "metrics": {
            "intent_accuracy": round(intent_accuracy, 4),
            "routing_accuracy": round(routing_accuracy, 4),
            "rag_golden_pass_rate": round(rag_golden_pass_rate, 4),
            "citation_presence_rate": round(citation_presence_rate, 4),
            "source_hit_rate": round(source_hit_rate, 4),
            "weak_evidence_correctness": round(weak_evidence_correctness, 4),
            "safety_guardrail_pass_rate": round(safety_guardrail_pass_rate, 4),
            "total_cases": total_cases,
            "failed_cases": len(failed_cases),
        },
        "suites": {
            "routing": intent_report,
            "rag": rag_report,
            "safety": safety_report,
        },
        "failed_cases": failed_cases,
        "limitations": [
            "Small labeled datasets (demo/capstone scope, not statistically significant).",
            "RAG eval uses deterministic keyword scoring over demo docs, not live vector search.",
            "No automated RAGAS faithfulness or LangSmith dataset runs in this harness.",
            "Multilingual RAG cases use offline heuristics; production quality needs human review.",
        ],
        "future_roadmap": [
            "RAGAS faithfulness",
            "RAGAS context precision",
            "RAGAS context recall",
            "RAGAS answer relevancy",
            "LangSmith evaluation datasets and regression runs on deploy",
        ],
    }


def combined_markdown(combined: dict[str, Any]) -> str:
    m = combined["metrics"]
    lines = [
        "# OnePilot AI — Evaluation & Quality Summary",
        "",
        f"**Generated:** {combined['generated_at']}",
        "",
        combined["disclaimer"],
        "",
        "## Quality metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Intent accuracy | {m['intent_accuracy']:.1%} |",
        f"| Routing accuracy | {m['routing_accuracy']:.1%} |",
        f"| RAG golden pass rate | {m['rag_golden_pass_rate']:.1%} |",
        f"| Citation presence rate | {m['citation_presence_rate']:.1%} |",
        f"| Source hit rate | {m['source_hit_rate']:.1%} |",
        f"| Weak-evidence correctness | {m['weak_evidence_correctness']:.1%} |",
        f"| Safety guardrail pass rate | {m['safety_guardrail_pass_rate']:.1%} |",
        f"| Total cases | {m['total_cases']} |",
        f"| Failed cases | {m['failed_cases']} |",
        "",
        "## How to regenerate",
        "",
        f"```bash\n{combined['run_command']}\n```",
        "",
        "## Limitations",
        "",
    ]
    for item in combined.get("limitations", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Future roadmap (RAGAS / LangSmith)", ""])
    for item in combined.get("future_roadmap", []):
        lines.append(f"- {item}")
    if combined.get("failed_cases"):
        lines.extend(["", "## Failed cases", ""])
        for fc in combined["failed_cases"][:25]:
            lines.append(f"- [{fc.get('suite', '?')}] {fc}")
    return "\n".join(lines)
