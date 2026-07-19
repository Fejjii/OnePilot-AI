from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemoryWriteRequest(BaseModel):
    scope: str = Field(default="user", max_length=32)
    key: str = Field(min_length=1, max_length=255)
    value: str
    ttl_seconds: int | None = Field(default=None, ge=1)


class MemoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str | None
    scope: str
    key: str
    value: str
    ttl_seconds: int | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MemoryListResponse(BaseModel):
    items: list[MemoryItemResponse]
    total: int


class MemoryStatusResponse(BaseModel):
    agent_memory_enabled: bool
    reason: str
    user_disabled: bool
    shared_demo_tenant: bool
    item_count: int
    max_items: int
    max_chars: int


class MemoryPreferenceRequest(BaseModel):
    disabled: bool


class MemoryClearResponse(BaseModel):
    deleted_count: int
