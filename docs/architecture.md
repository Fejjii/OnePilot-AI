# Architecture

## Recruiter-friendly overview

OnePilot AI is a **multi-tenant AI operations workspace**: a Next.js client talks to a FastAPI backend that runs a LangGraph agent, a RAG pipeline, and approval-gated provider adapters.

| Piece | Role |
|-------|------|
| Frontend | Landing, guided workspace, knowledge, leads, approvals, memory, usage, settings |
| API layer | Thin routers, JWT principal, validation |
| Services | Business logic, quotas, audit, memory, RAG, approvals |
| Agent | Two-stage routing → tools → structured response |
| Providers | OpenAI / Serper / Gmail / Calendar / Stripe / HubSpot with mock or live modes |
| Data | PostgreSQL (tenant-scoped), Redis (rate limits), Qdrant or in-memory vectors |

**Public demo track:** Vercel frontend + Railway backend. Gmail and Calendar are **mock**. Shared-demo agent memory is disabled and cleared on demo start. See [capabilities.md](capabilities.md) and [safety_and_privacy.md](safety_and_privacy.md).

```mermaid
flowchart TB
    User[Reviewer browser] --> Landing[Landing Try the demo]
    Landing --> FE[Next.js app]
    FE -->|JWT REST| API[FastAPI]
    API --> Agent[LangGraph agent]
    API --> RAG[RAG knowledge]
    API --> HITL[Approvals]
    Agent --> Tools[Tools]
    Tools --> Adapters[Provider adapters]
    Adapters --> MockGC[Mock Gmail Calendar on public demo]
    Adapters --> Data[(Postgres Redis Qdrant/fallback)]
    HITL --> Adapters
```

## System Overview

OnePilot AI follows a layered, multi-tenant SaaS architecture. Every layer has a single responsibility and communicates through well-defined interfaces.

### System architecture

```mermaid
flowchart TB
    User[User Browser]

    subgraph Frontend [Next.js Frontend]
        Pages[Dashboard Workspace Knowledge Leads Approvals Usage Evaluation Settings]
    end

    subgraph Backend [FastAPI Backend]
        Routers[Routers chat knowledge approvals health providers]
        Services[Services auth rag lead approval usage audit memory]
        Agent[LangGraph Agent two-stage routing]
        Tools[Tool Registry]
        RAG[RAG Service]
        ApprovalSvc[Approval Service]
        UsageSvc[Usage Service]
        AuditLog[Audit Logging]
        Diagnostics[Provider Diagnostics]
    end

    subgraph Data [Data Layer]
        Postgres[(Postgres)]
        Redis[(Redis cache and rate limit)]
        Qdrant[(Qdrant vectors)]
    end

    subgraph External [External Providers]
        OpenAI[OpenAI LLM embeddings speech]
        Serper[Serper Web Search]
        Gmail[Gmail API]
        GCal[Google Calendar API]
    end

    User --> Pages
    Pages -->|REST JSON| Routers
    Routers --> Services
    Services --> Agent
    Agent --> Tools
    Tools --> RAG
    Tools --> Serper
    Tools --> Gmail
    Tools --> GCal
    Services --> ApprovalSvc
    Services --> UsageSvc
    Services --> AuditLog
    Routers --> Diagnostics
    Services --> Postgres
    Services --> Redis
    RAG --> Qdrant
    RAG --> OpenAI
    Agent --> OpenAI
    Gmail --> External
    GCal --> External
    Serper --> External
```

## Request Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant M as Middleware
    participant R as Router
    participant A as Auth Dep
    participant S as Service
    participant DB as Repository
    participant P as Provider

    C->>M: HTTP Request
    M->>M: Assign Request ID
    M->>M: Log request
    M->>R: Forward to router
    R->>A: Resolve Principal JWT or DEV_AUTH
    A-->>R: Principal user_id org_id role plan
    R->>R: Validate request body
    R->>S: Call service method
    S->>S: Check permissions
    S->>S: Check quota
    S->>DB: Read or write data
    S->>P: Call external provider if needed
    P-->>S: Provider result
    S->>DB: Log usage and audit
    S-->>R: Service result
    R-->>C: HTTP Response
```

## Layer Responsibilities

| Layer | Responsibility | Rules |
|-------|---------------|-------|
| **Routers** | HTTP validation, routing | No business logic. Call services only. |
| **Services** | Business logic, orchestration | No direct DB queries. Call repos/providers. |
| **Agents** | AI workflow orchestration | Call tools only through tool registry. |
| **Tools** | Bridge between agents and services | Thin wrappers that call services. |
| **Repositories** | Data persistence | Enforce tenant isolation. Own SQL. |
| **Providers** | External system integration | Every provider has mock/fallback/live modes. |
| **Security** | Auth, RBAC, guardrails | Runs before sensitive actions. |

## Provider Adapter Pattern

Every external integration follows the same pattern with diagnostics and safe fallback:

```mermaid
flowchart TB
    Tool[Agent Tool] --> Service[Service Layer]
    Service --> Factory[get provider factory]
    Factory --> ModeCheck{Credentials and mode}

    ModeCheck -->|live| LiveProvider[Live Provider]
    ModeCheck -->|mock or missing| MockProvider[Mock Provider]

    LiveProvider --> ExternalAPI[External API]
    MockProvider --> InMemory[In Memory deterministic]

    LiveProvider --> Diagnostics[Provider Diagnostics]
    MockProvider --> Diagnostics

    Diagnostics --> HealthEndpoint[GET health and providers]
    ExternalAPI --> Result[Provider Result]
    InMemory --> Result
    Result --> Service
```

- `base.py` defines the interface (ABC/Protocol)
- Mock providers are deterministic and suitable for tests/demos
- Live providers are activated by setting the appropriate env keys
- `/providers` and Settings show mode without exposing secrets
- The registry logs `fallback_used=True` when mocks are active

## AI Orchestration Flow

```mermaid
flowchart TD
    Start([User Message]) --> Safety{Safety Check}
    Safety -->|blocked| SafetyError[Safety Error and audit]
    Safety -->|safe| MessageClass[Stage 1 Message Classifier]
    MessageClass --> IntentClassifier[Stage 2 Intent Classifier]
    IntentClassifier --> QuotaCheck{Quota Available}
    QuotaCheck -->|No| QuotaError[Quota Exceeded]
    QuotaCheck -->|Yes| Route{Route by Intent}

    Route -->|knowledge_search| RAG[RAG Tool rag.answer]
    Route -->|web_search| WebTool[external.web_search Serper]
    Route -->|web_and_knowledge| WebRAG[Web plus RAG Tools]
    Route -->|email_drafting| EmailTool[email.draft]
    Route -->|calendar| CalTool[calendar check suggest create]
    Route -->|compound_workflow| Compound[web search email calendar]
    Route -->|general_assistant| LLM[Direct LLM]
    Route -->|workflow_action| WorkflowTool[Workflow Tools]

    RAG --> Synthesize[Synthesize Response with citations]
    WebTool --> Synthesize
    WebRAG --> Synthesize
    EmailTool --> Synthesize
    CalTool --> Synthesize
    Compound --> Synthesize
    LLM --> Synthesize
    WorkflowTool --> Synthesize

    Synthesize --> Guardrails[Guardrails and confidence]
    Guardrails --> ApprovalCheck{Requires Approval}
    ApprovalCheck -->|Yes| CreateApproval[Create Approval Request]
    ApprovalCheck -->|No| LogUsage[Log Usage and Audit]
    CreateApproval --> LogUsage
    LogUsage --> UpdateMemory[Update Memory]
    UpdateMemory --> Done([Return to User])
```

## RAG and Hybrid Retrieval

Internal knowledge and external web search are kept separate end-to-end:

```mermaid
flowchart LR
    subgraph Internal [Internal Knowledge]
        Docs[Knowledge Documents]
        Chunk[Chunking section aware]
        Embed[Embedding OpenAI or fallback]
        Store[(Qdrant tenant scoped)]
    end

    subgraph Retrieval [Hybrid Retrieval]
        Query[User Query]
        RAGRetrieve[RAG retrieval rag.answer]
        SerperSearch[Serper external.web_search]
    end

    subgraph Output [Synthesis]
        InternalCite[Internal citations doc title section]
        ExternalCite[External citations page title URL]
        Answer[Combined answer with separated evidence]
    end

    Docs --> Chunk --> Embed --> Store
    Query --> RAGRetrieve
    Query --> SerperSearch
    Store --> RAGRetrieve
    SerperSearch --> ExternalCite
    RAGRetrieve --> InternalCite
    InternalCite --> Answer
    ExternalCite --> Answer
```

## Approval Workflow

External side effects never run without human review:

```mermaid
sequenceDiagram
    participant Agent as LangGraph Agent
    participant Approval as Approval Service
    participant Admin as Admin or Owner
    participant Gmail as Gmail Provider
    participant Cal as Google Calendar
    participant Audit as Audit Log

    Agent->>Approval: Propose action draft or event
    Approval->>Approval: Create ApprovalRequest pending
    Agent-->>Admin: Notify pending approval in UI

    alt Approved
        Admin->>Approval: Approve request
        Approval->>Gmail: Create draft after Gmail approval
        Approval->>Cal: Create event after Calendar approval
        Gmail-->>Approval: Execution metadata draft id
        Cal-->>Approval: Execution metadata event id
        Approval->>Audit: Log approval and execution
    else Rejected
        Admin->>Approval: Reject request
        Approval->>Audit: Log rejection no retry
    else Needs more info
        Admin->>Approval: Request clarification
        Approval-->>Admin: Stays pending
    end
```

Gmail **send** remains disabled by default (`GMAIL_SEND_ENABLED=false`). Calendar availability and slot suggestions do not require approval; event creation does.

## Frontend to Backend Flow

```mermaid
flowchart LR
    User[User Browser] --> NextJS[Next.js App]
    NextJS -->|REST API JSON| FastAPI[FastAPI Backend]
    FastAPI --> Middleware[Request Middleware]
    Middleware --> AuthCheck{JWT Valid}
    AuthCheck -->|Yes| Router[API Router]
    AuthCheck -->|No plus DEV_AUTH| DevAuth[Dev Auth Fallback]
    DevAuth --> Router
    AuthCheck -->|No| Error401[401 Unauthorized]
    Router --> Service[Service Layer]
    Service --> Data[Data and Provider Layer]
    Data --> Response[JSON Response]
    Response --> NextJS
```

## Multilingual Layer

Response language is resolved before agent execution and passed through chat, RAG, and general-chat paths.

| Component | Role |
|-----------|------|
| `LanguageService` | Heuristic detection EN DE FR ES with optional OpenAI disambiguation |
| `language_preference` on chat requests | auto or fixed en de fr es from workspace UI |
| `RAGService` | Retrieves in source language optional English expansion answers in response language |
| `i18n_messages` | Localized fallback strings when providers unavailable |
| Frontend language selector | Sets language_preference on workspace chat and speech only one selector |

Citations and document metadata stay in the knowledge base original language.

## Multi-Tenant Isolation

- Every business entity is scoped by `organization_id`
- The `TenantMixin` adds `organization_id` to all relevant models
- The `BaseRepository` enforces `organization_id` on all queries
- The `ensure_same_org()` guard prevents cross-tenant access at the service layer
- API dependencies resolve the `Principal` user_id org_id role plan from the JWT

See [data_model.md](data_model.md) for entity relationships.
