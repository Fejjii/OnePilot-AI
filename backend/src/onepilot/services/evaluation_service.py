"""Read evaluation reports for the API (no eval execution at request time)."""

from __future__ import annotations

from typing import Any

from onepilot.evaluation.reporting import EMPTY_STATE_MESSAGE, RUN_COMMAND, load_latest_report
from onepilot.schemas.evaluation import (
    EvaluationMetrics,
    EvaluationSummaryResponse,
    HitlApprovalSafety,
)


def get_evaluation_summary() -> EvaluationSummaryResponse:
    raw = load_latest_report()
    if raw is None:
        return EvaluationSummaryResponse(
            available=False,
            message=EMPTY_STATE_MESSAGE,
            run_command=RUN_COMMAND,
        )

    metrics_raw = raw.get("metrics") or {}
    metrics = EvaluationMetrics(**metrics_raw)

    hitl: HitlApprovalSafety | None = None
    safety_suite = (raw.get("suites") or {}).get("safety") or {}
    hitl_raw = safety_suite.get("hitl_approval_safety")
    if hitl_raw:
        hitl = HitlApprovalSafety(**hitl_raw)
    else:
        hitl = HitlApprovalSafety(
            gated_action_types=[
                "send_email",
                "gmail_create_draft",
                "gmail_send_email",
                "schedule_meeting",
                "calendar_create_event",
                "google_calendar_create_event",
                "update_crm",
                "external_action",
                "high_risk_tool_call",
                "low_confidence_action",
            ],
        )

    return EvaluationSummaryResponse(
        available=True,
        generated_at=raw.get("generated_at"),
        run_command=raw.get("run_command", RUN_COMMAND),
        disclaimer=raw.get("disclaimer"),
        metrics=metrics,
        suites=raw.get("suites"),
        failed_cases=list(raw.get("failed_cases") or []),
        limitations=list(raw.get("limitations") or []),
        future_roadmap=list(raw.get("future_roadmap") or []),
        hitl_approval_safety=hitl,
    )


def build_sample_report() -> dict[str, Any]:
    """Deterministic sample for API tests."""
    return {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "status": "complete",
        "run_command": RUN_COMMAND,
        "disclaimer": "Sample evaluation report for tests.",
        "metrics": {
            "intent_accuracy": 0.95,
            "routing_accuracy": 0.92,
            "rag_golden_pass_rate": 0.88,
            "citation_presence_rate": 0.9,
            "source_hit_rate": 0.88,
            "weak_evidence_correctness": 1.0,
            "safety_guardrail_pass_rate": 1.0,
            "total_cases": 52,
            "failed_cases": 2,
        },
        "suites": {
            "routing": {"total": 30, "intent_accuracy": 0.95},
            "rag": {"total": 10, "rag_golden_pass_rate": 0.88},
            "safety": {
                "total": 12,
                "safety_guardrail_pass_rate": 1.0,
                "hitl_approval_safety": {
                    "sensitive_actions_require_approval": True,
                    "ai_can_draft_not_send_without_approval": True,
                    "approval_decisions_audit_logged": True,
                    "admin_owner_review_actions": True,
                    "gated_action_types": ["send_email", "update_crm"],
                },
            },
        },
        "failed_cases": [{"suite": "rag", "query": "example fail"}],
        "limitations": ["Sample limitation"],
        "future_roadmap": ["RAGAS faithfulness", "LangSmith datasets"],
    }
