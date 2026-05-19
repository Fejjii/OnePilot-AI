# Architecture

## System Overview

OnePilot AI follows a layered, multi-tenant SaaS architecture. Every layer has a single responsibility and communicates through well-defined interfaces.

```mermaid
flowchart TB
    subgraph Client ["Client Layer"]
        Browser["Browser (Next.js)"]
    end

    subgraph API ["API Layer (FastAPI)"]
        Middleware["Middleware<br/>(Request ID, CORS, Logging)"]
        Routers["Routers<br/>(thin, validation only)"]
        AuthDep["Auth Dependencies<br/>(JWT + DEV_AUTH fallback)"]
    end

    subgraph Business ["Business Logic Layer"]
        Services["Services<br/>(auth, org, plan, quota,<br/>chat, rag, lead, email,<br/>approval, usage, memory, audit)"]
        Agents["LangGraph Agent<br/>(router, nodes, tools)"]
    end

    subgraph Data ["Data & Integration Layer"]
        Repos["Repositories<br/>(SQLAlchemy 2.x sync)"]
        Providers["Provider Adapters<br/>(LLM, Embeddings, Vector,<br/>CRM, Email, Calendar,<br/>Search, Billing)"]
    end

    subgraph Infra ["Infrastructure"]
        Postgres[(PostgreSQL)]
        Redis[(Redis)]
        Qdrant[(Qdrant)]
        External["External APIs<br/>(OpenAI, HubSpot, Gmail, etc.)"]
    end

    Browser --> Middleware --> Routers
    Routers --> AuthDep
    Routers --> Services
    Services --> Agents
    Agents --> Services
    Services --> Repos
    Services --> Providers
    Repos --> Postgres
    Providers --> External
    Providers -.->|"fallback/mock"| Providers
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
    R->>A: Resolve Principal (JWT / DEV_AUTH)
    A-->>R: Principal (user_id, org_id, role, plan)
    R->>R: Validate request body
    R->>S: Call service method
    S->>S: Check permissions
    S->>S: Check quota
    S->>DB: Read/write data
    S->>P: Call external provider (if needed)
    P-->>S: Provider result
    S->>DB: Log usage/audit
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
| **Providers** | External system integration | Every provider has a mock/fallback. |
| **Security** | Auth, RBAC, guardrails | Runs before sensitive actions. |

## Provider Adapter Pattern

Every external integration follows the same pattern:

```mermaid
flowchart LR
    subgraph Registry ["Provider Registry"]
        Factory["get_*_provider(settings)"]
    end

    Factory -->|"env key present"| RealImpl["Real Provider<br/>(OpenAI, Qdrant, etc.)"]
    Factory -->|"env key missing"| MockImpl["Mock Provider<br/>(deterministic, in-memory)"]

    RealImpl --> ExternalAPI["External API"]
    MockImpl --> InMemory["In-Memory Store"]
```

- `base.py` defines the interface (ABC/Protocol)
- Mock providers are deterministic and suitable for tests/demos
- Real providers are activated by setting the appropriate env key
- The registry logs `fallback_used=True` when mocks are active

## Frontend to Backend Flow

```mermaid
flowchart LR
    User["User Browser"] --> NextJS["Next.js App"]
    NextJS -->|REST API<br/>JSON| FastAPI["FastAPI Backend"]
    FastAPI --> Middleware["Request Middleware"]
    Middleware --> AuthCheck{"JWT<br/>Valid?"}
    AuthCheck -->|Yes| Router["API Router"]
    AuthCheck -->|No + DEV_AUTH| DevAuth["Dev Auth Fallback"]
    DevAuth --> Router
    AuthCheck -->|No| Error401["401 Unauthorized"]
    Router --> Service["Service Layer"]
    Service --> Data["Data/Provider Layer"]
    Data --> Response["JSON Response"]
    Response --> NextJS
```

## External Provider Integration Flow

```mermaid
flowchart TB
    Service["Service Layer"] --> ProviderFactory["Provider Factory"]
    ProviderFactory --> EnvCheck{"API Key<br/>Present?"}
    
    EnvCheck -->|Yes| RealProvider["Real Provider"]
    EnvCheck -->|No| MockProvider["Mock Provider"]
    
    RealProvider --> OpenAI["OpenAI API"]
    RealProvider --> Qdrant["Qdrant API"]
    RealProvider --> HubSpot["HubSpot API"]
    RealProvider --> Gmail["Gmail API"]
    RealProvider --> Serper["Serper API"]
    
    MockProvider --> InMemory["In-Memory<br/>Deterministic Fallback"]
    
    OpenAI --> Result["Provider Result"]
    Qdrant --> Result
    HubSpot --> Result
    Gmail --> Result
    Serper --> Result
    InMemory --> Result
    
    Result --> Service
```

## AI Orchestration Flow

```mermaid
flowchart TD
    Start([User Message]) --> Safety{Safety<br/>Check}
    Safety -->|blocked| SafetyError[Safety Error]
    Safety -->|safe| IntentClassifier["Intent Classifier<br/>(LLM or Rules)"]
    
    IntentClassifier --> QuotaCheck{"Quota<br/>Available?"}
    QuotaCheck -->|No| QuotaError[Quota Exceeded]
    QuotaCheck -->|Yes| Route{Route by Intent}
    
    Route -->|knowledge_search| RAG["RAG Tool"]
    Route -->|lead_support| LeadTool["Lead Tool"]
    Route -->|email_drafting| EmailTool["Email Tool"]
    Route -->|general_assistant| LLM["Direct LLM"]
    Route -->|workflow_action| WorkflowTool["Workflow Tool"]
    
    RAG --> ToolResult["Tool Results"]
    LeadTool --> ToolResult
    EmailTool --> ToolResult
    LLM --> ToolResult
    WorkflowTool --> ToolResult
    
    ToolResult --> Synthesize["Synthesize Response"]
    Synthesize --> ApprovalCheck{"Requires<br/>Approval?"}
    
    ApprovalCheck -->|Yes| CreateApproval["Create Approval<br/>Request"]
    ApprovalCheck -->|No| LogUsage["Log Usage &<br/>Audit Event"]
    CreateApproval --> LogUsage
    
    LogUsage --> UpdateMemory["Update Memory"]
    UpdateMemory --> Done([Return to User])
```

## Multilingual Layer

Response language is resolved before agent execution and passed through chat, RAG, and general-chat paths.

| Component | Role |
|-----------|------|
| `LanguageService` | Heuristic detection (EN/DE/FR/ES) with optional OpenAI disambiguation |
| `language_preference` on chat requests | `auto` or fixed `en` / `de` / `fr` / `es` from the workspace UI |
| `RAGService` | Retrieves in source language; optional English query expansion; answers in response language |
| `i18n_messages` | Localized fallback strings when providers are unavailable |
| Frontend `LanguageSelector` | Sets `language_preference` on `/workspace` chat and speech flows |

Citations and document metadata stay in the knowledge base’s original language.

## Multi-Tenant Isolation

- Every business entity is scoped by `organization_id`
- The `TenantMixin` adds `organization_id` to all relevant models
- The `BaseRepository` enforces `organization_id` on all queries
- The `ensure_same_org()` guard prevents cross-tenant access at the service layer
- API dependencies resolve the `Principal` (user_id, org_id, role, plan) from the JWT
