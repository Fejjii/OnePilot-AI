from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class PlanCode(StrEnum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    BUSINESS = "business"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_INFO = "needs_more_info"


class Intent(StrEnum):
    GENERAL_ASSISTANT = "general_assistant"
    KNOWLEDGE_SEARCH = "knowledge_search"
    LEAD_SUPPORT = "lead_support"
    EMAIL_DRAFTING = "email_drafting"
    DOCUMENT_SUMMARY = "document_summary"
    WORKFLOW_ACTION = "workflow_action"
    OUT_OF_SCOPE = "out_of_scope"
    CLARIFICATION = "clarification"


class UsageFeature(StrEnum):
    CHAT_MESSAGES = "chat_messages"
    RAG_QUERIES = "rag_queries"
    DOCUMENT_UPLOADS = "document_uploads"
    STORAGE_MB = "storage_mb"
    EMAIL_DRAFTS = "email_drafts"
    LEAD_WORKFLOWS = "lead_workflows"
    TOOL_CALLS = "tool_calls"
    USERS = "users"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
