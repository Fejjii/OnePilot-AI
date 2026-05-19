from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    intent_accuracy: float = 0.0
    routing_accuracy: float = 0.0
    rag_golden_pass_rate: float = 0.0
    citation_presence_rate: float = 0.0
    source_hit_rate: float = 0.0
    weak_evidence_correctness: float = 0.0
    safety_guardrail_pass_rate: float = 0.0
    total_cases: int = 0
    failed_cases: int = 0


class HitlApprovalSafety(BaseModel):
    sensitive_actions_require_approval: bool = True
    ai_can_draft_not_send_without_approval: bool = True
    approval_decisions_audit_logged: bool = True
    admin_owner_review_actions: bool = True
    gated_action_types: list[str] = Field(default_factory=list)


class EvaluationSummaryResponse(BaseModel):
    available: bool
    message: str | None = None
    generated_at: str | None = None
    run_command: str | None = None
    disclaimer: str | None = None
    metrics: EvaluationMetrics | None = None
    suites: dict[str, Any] | None = None
    failed_cases: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    future_roadmap: list[str] = Field(default_factory=list)
    hitl_approval_safety: HitlApprovalSafety | None = None
