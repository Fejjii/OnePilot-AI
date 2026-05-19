from __future__ import annotations

from fastapi import APIRouter

from onepilot.schemas.evaluation import EvaluationSummaryResponse
from onepilot.services import evaluation_service

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/summary", response_model=EvaluationSummaryResponse)
def evaluation_summary() -> EvaluationSummaryResponse:
    """Return the latest offline evaluation report if it exists."""
    return evaluation_service.get_evaluation_summary()
