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


class MessageClass(StrEnum):
    """High-level message classification (Stage 1 of routing)."""
    CAPABILITY_OR_HELP = "capability_or_help"
    CONVERSATIONAL = "conversational"
    CORRECTION_OR_META = "correction_or_meta"
    EXTERNAL_RESEARCH = "external_research"
    BUSINESS_KNOWLEDGE = "business_knowledge"
    WORKFLOW_REQUEST = "workflow_request"
    UNCLEAR = "unclear"
    OUT_OF_SCOPE = "out_of_scope"


class Intent(StrEnum):
    """Specific intent classification (Stage 2 of routing)."""
    GENERAL_ASSISTANT = "general_assistant"
    KNOWLEDGE_SEARCH = "knowledge_search"
    WEB_SEARCH = "web_search"
    WEB_AND_KNOWLEDGE = "web_and_knowledge"
    LEAD_SUPPORT = "lead_support"
    EMAIL_DRAFTING = "email_drafting"
    CALENDAR_AVAILABILITY = "calendar_availability"
    CALENDAR_SCHEDULING = "calendar_scheduling"
    CALENDAR_AND_EMAIL = "calendar_and_email"
    DOCUMENT_SUMMARY = "document_summary"
    WORKFLOW_ACTION = "workflow_action"
    COMPOUND_WORKFLOW = "compound_workflow"
    OUT_OF_SCOPE = "out_of_scope"
    CLARIFICATION = "clarification"


class LanguageCode(StrEnum):
    EN = "en"
    DE = "de"
    FR = "fr"
    ES = "es"


class LanguagePreference(StrEnum):
    AUTO = "auto"
    EN = "en"
    DE = "de"
    FR = "fr"
    ES = "es"


class UsageFeature(StrEnum):
    CHAT_MESSAGES = "chat_messages"
    WEB_SEARCH = "web_search"
    RAG_QUERIES = "rag_queries"
    DOCUMENT_UPLOADS = "document_uploads"
    STORAGE_MB = "storage_mb"
    EMAIL_DRAFTS = "email_drafts"
    GMAIL_CREATE_DRAFT = "gmail_create_draft"
    GMAIL_SEND_EMAIL = "gmail_send_email"
    CALENDAR_AVAILABILITY = "calendar_availability"
    CALENDAR_SUGGEST_SLOTS = "calendar_suggest_slots"
    CALENDAR_CREATE_EVENT = "calendar_create_event"
    CALENDAR_APPROVAL_CREATED = "calendar_approval_created"
    CALENDAR_APPROVAL_EXECUTED = "calendar_approval_executed"
    LEAD_WORKFLOWS = "lead_workflows"
    TOOL_CALLS = "tool_calls"
    USERS = "users"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
