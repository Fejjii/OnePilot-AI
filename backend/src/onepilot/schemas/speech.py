from __future__ import annotations

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Response from speech transcription endpoint."""
    
    transcript: str = Field(..., description="Transcribed text")
    language: str | None = Field(None, description="Detected language code")
    duration: float | None = Field(None, description="Audio duration in seconds")
    provider: str = Field(..., description="Provider used (e.g., 'openai')")
    model: str = Field(..., description="Model used for transcription")
    fallback_used: bool = Field(..., description="Whether fallback was used")
    usage: dict = Field(default_factory=dict, description="Usage metadata")
