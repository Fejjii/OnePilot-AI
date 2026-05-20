# Data Model

## Entity Relationship Diagram

```mermaid
erDiagram
    Organization ||--o{ OrganizationMember : has
    Organization ||--o{ Subscription : has
    Organization ||--o{ UsageQuota : tracks
    Organization ||--o{ Document : owns
    Organization ||--o{ Conversation : owns
    Organization ||--o{ Lead : owns
    Organization ||--o{ ApprovalRequest : owns
    Organization ||--o{ AuditLog : produces
    Organization ||--o{ UsageEvent : emits
    Organization ||--o{ MemoryItem : stores
    User ||--o{ OrganizationMember : belongs_to
    Plan ||--o{ Subscription : defines
    OrganizationMember }o--|| User : references
    Document ||--o{ DocumentChunk : contains
    Conversation ||--o{ Message : contains

    Organization {
        string id PK
        string name
        string slug UK
        datetime created_at
    }

    User {
        string id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
    }

    Conversation {
        string id PK
        string organization_id FK
        string user_id FK
        string title
        datetime created_at
    }

    Message {
        string id PK
        string conversation_id FK
        string role
        text content
        json metadata
        datetime created_at
    }

    Lead {
        string id PK
        string organization_id FK
        string name
        string email
        string status
        string priority
    }

    ApprovalRequest {
        string id PK
        string organization_id FK
        string action_type
        string status
        json proposed_payload
        string risk_level
        datetime created_at
    }

    Document {
        string id PK
        string organization_id FK
        string title
        int chunk_count
        string status
    }

    DocumentChunk {
        string id PK
        string document_id FK
        string section
        text content
    }

    AuditLog {
        string id PK
        string organization_id FK
        string user_id
        string action
        json detail
        datetime created_at
    }

    UsageEvent {
        string id PK
        string organization_id FK
        string feature
        string model
        float estimated_cost
        bool fallback_used
        datetime created_at
    }

    MemoryItem {
        string id PK
        string organization_id FK
        string key
        text value
    }
```

## Provider Diagnostics (runtime, not persisted)

Provider health is computed at request time from env configuration and live probes. Exposed via `GET /health` and `GET /providers` — **never stores OAuth tokens or API keys**.

| Field | Source |
|-------|--------|
| `mode` | live / mock / missing / optional / unhealthy |
| `capabilities` | e.g. draft, send, availability, create_event |
| `requires_approval` | HITL policy flags |

---

## Plan Limits

| Feature | Free | Pro | Team | Business |
|---------|------|-----|------|----------|
| Chat Messages | 50 | 500 | 2,000 | 10,000 |
| RAG Queries | 20 | 200 | 1,000 | 5,000 |
| Document Uploads | 5 | 50 | 200 | 1,000 |
| Storage (MB) | 100 | 1,000 | 5,000 | 25,000 |
| Email Drafts | 10 | 100 | 500 | 2,000 |
| Lead Workflows | 5 | 50 | 200 | 1,000 |
| Tool Calls | 30 | 300 | 1,000 | 5,000 |
| Users | 1 | 1 | 10 | 50 |

## Roles

| Role | Permissions |
|------|------------|
| Owner | Full admin — manage org, team, data, settings, billing |
| Admin | Manage team, data, settings |
| Member | Use AI tools, read data |
| Viewer | Read-only access |

## Core Entities

- **Document / DocumentChunk** — uploaded files, section-aware chunks, tenant-scoped Qdrant collections
- **Conversation / Message** — chat sessions and turns with intent/tool metadata
- **Lead** — sales leads with status, priority, source (seeded demo data)
- **ApprovalRequest** — human-in-the-loop queue for Gmail, Calendar, CRM actions
- **AuditLog** — append-only sensitive action log
- **UsageEvent** — token, latency, cost per LLM/tool call
- **MemoryItem** — persistent org/conversation facts for the agent

All entities enforce `organization_id` at the repository layer.

## Demo Data

The fictional company **NovaEdge Solutions** provides realistic demo data via `backend/src/onepilot/demo_data/`:

- 19 knowledge base markdown documents
- 12 leads, 8 approvals (with pending items), 40 usage events, 25 audit log entries
- Idempotent `POST /demo/seed` and `docker compose run --rm seed`
