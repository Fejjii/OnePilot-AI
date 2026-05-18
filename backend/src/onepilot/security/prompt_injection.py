from __future__ import annotations

import re

from pydantic import BaseModel

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"ignore\s+(previous|all|your)\s+instructions",
            re.IGNORECASE,
        ),
        "Instruction override attempt",
    ),
    (
        re.compile(
            r"(reveal|show|display)\s+(your\s+)?(system\s+prompt|instructions)"
            r"|what\s+is\s+your\s+system\s+prompt",
            re.IGNORECASE,
        ),
        "System prompt extraction attempt",
    ),
    (
        re.compile(
            r"delete\s+all\s+data|drop\s+all\s+tables|truncate",
            re.IGNORECASE,
        ),
        "Destructive data operation",
    ),
    (
        re.compile(
            r"(bypass|skip|without)\s+approval",
            re.IGNORECASE,
        ),
        "Approval bypass attempt",
    ),
    (
        re.compile(
            r"send\s+(email\s+)?without\s+(approval|checking)",
            re.IGNORECASE,
        ),
        "Unapproved action attempt",
    ),
    (
        re.compile(
            r"(expose|show|reveal)\s+(api\s+key|secret)"
            r"|print\s+environment",
            re.IGNORECASE,
        ),
        "Secret exfiltration attempt",
    ),
    (
        re.compile(
            r"act\s+as\s+admin"
            r"|pretend\s+you\s+are\s+admin"
            r"|you\s+are\s+now\s+admin"
            r"|escalate\s+privileges",
            re.IGNORECASE,
        ),
        "Privilege escalation attempt",
    ),
    (
        re.compile(
            r"execute\s+code|run\s+command|system\s*\(|os\.system|subprocess",
            re.IGNORECASE,
        ),
        "Code execution attempt",
    ),
]


class SafetyVerdict(BaseModel):
    blocked: bool
    reasons: list[str]
    risk_score: float


def check_prompt_injection(text: str) -> SafetyVerdict:
    reasons: list[str] = []
    for pattern, reason in _PATTERNS:
        if pattern.search(text):
            reasons.append(reason)

    risk_score = min(1.0, len(reasons) * 0.3)
    return SafetyVerdict(
        blocked=risk_score >= 0.3,
        reasons=reasons,
        risk_score=risk_score,
    )
