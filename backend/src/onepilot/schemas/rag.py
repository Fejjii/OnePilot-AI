from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2048)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict | None = None


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    section: str | None = None
    score: float


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    section: str | None = None
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    total_found: int = 0
    weak_evidence: bool = False
    fallback_used: bool = False


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2048)
    top_k: int = Field(default=5, ge=1, le=10)


class AnswerResponse(BaseModel):
    query: str
    answer: str
    confidence: float
    citations: list[Citation] = Field(default_factory=list)
    weak_evidence: bool = False
    fallback_used: bool = False
    model: str
