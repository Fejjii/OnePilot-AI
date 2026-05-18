from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from onepilot.schemas.chat import Citation


class EmailDraftRequest(BaseModel):
    context: str = Field(min_length=1, max_length=8000)
    tone: str = "professional"
    recipient_name: str | None = None
    recipient_email: str | None = None


class EmailDraft(BaseModel):
    """Structured email draft returned by the email assistant tool."""

    model_config = ConfigDict(extra="forbid")

    subject: str
    body: str
    tone: str = "professional"
    recipient_placeholder: str = "[recipient]"
    context_used: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    risk_level: str = "medium"
    approval_required: bool = True


class EmailDraftResponse(BaseModel):
    """API response containing a draft and (optionally) an approval id."""

    draft: EmailDraft
    approval_id: str | None = None
