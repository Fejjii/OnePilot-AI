# AI Engineering Best Practices

This document describes the AI engineering principles, patterns, and practices implemented in OnePilot AI.

---

## 1. Prompt Engineering Approach

### Principle: Separation of Concerns
Prompts are **not hardcoded** in service logic. They are:
- Defined as template strings in separate files or config
- Versioned and tracked like code
- Testable and inspectable

### Implementation
- **Intent Classification Prompt:** Located in `agents/prompts.py`
- **RAG Answer Prompt:** Located in `rag/prompts.py`
- **Email Drafting Prompt:** Located in `services/email.py` (template with variables)

### Prompt Template Structure
```python
RAG_ANSWER_PROMPT = """
You are a helpful business assistant. Answer the user's question using ONLY the provided context.

Context:
{context}

User Question:
{question}

Rules:
1. Only use information from the context above
2. If the context doesn't contain enough information, say so
3. Cite the source document for each claim
4. Be concise and professional
"""
```

### Versioning
- Each prompt change is tracked via Git
- Major prompt revisions include version comments
- Breaking changes trigger evaluation re-runs

---

## 2. RAG Strategy

### Architecture
OnePilot AI uses a **3-stage RAG pipeline**:

1. **Ingestion:**
   - Parse document (markdown, text, PDF, DOCX)
   - Section-aware chunking (~500 tokens per chunk)
   - Embed each chunk via OpenAI `text-embedding-3-small` (or fallback)
   - Store in Qdrant with metadata (document_id, ordinal, section)

2. **Retrieval:**
   - Embed user query
   - Cosine similarity search in tenant's collection
   - Filter chunks by similarity threshold (0.7)
   - Rank top K chunks (default: 5)

3. **Synthesis:**
   - Build prompt: query + top K chunks
   - Generate answer via LLM
   - Extract citations from chunk metadata
   - Validate answer is grounded in context

### Weak Evidence Guardrail
If no chunks exceed the similarity threshold, the system **refuses to answer**:
```python
if max_similarity < SIMILARITY_THRESHOLD:
    return "I don't have enough information in the knowledge base to answer that."
```

This prevents hallucination and ensures factual grounding.

### Citation Extraction
Every RAG response includes:
```json
{
  "answer": "...",
  "citations": [
    {
      "document_id": "doc_123",
      "chunk_id": "chunk_456",
      "section": "Pricing Overview",
      "similarity": 0.89
    }
  ]
}
```

---

## 3. Guardrails

### 3.1 Prompt Injection Detection
**Location:** `security/guardrails.py`

**Approach:** Regex + keyword matching

**Patterns Detected:**
- Ignore previous instructions
- System override attempts
- Jailbreak attempts
- Role confusion

**Action:** Block request, log audit event, return safe error

**Example:**
```python
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|the)\s+instructions",
    r"disregard\s+your\s+programming",
    r"you\s+are\s+now\s+a\s+different\s+assistant",
    ...
]
```

### 3.2 Sensitive Data Redaction
**Location:** `security/guardrails.py`

**Approach:** Regex matching + context-aware filtering

**Patterns Redacted:**
- Credit card numbers (Luhn algorithm validation)
- SSNs (US format)
- API keys (common prefixes: `sk-`, `pk_`, etc.)
- Email addresses (optionally)
- Phone numbers (US format)

**Action:** Replace with `[REDACTED]`, log warning, continue

### 3.3 Input Validation
**Location:** All service entry points

**Approach:** Pydantic schema validation

**Validated Fields:**
- String length limits
- Email format
- URL format
- Enum membership (status, role, etc.)
- Required vs optional fields

---

## 4. Error Handling

### Principle: Fail Clearly, Never Silently

### LLM Provider Errors
**Strategy:** Automatic fallback to mock provider

**Implementation:**
```python
try:
    response = real_llm_provider.generate(prompt)
except Exception as e:
    logger.warning(f"LLM provider failed: {e}")
    response = fallback_llm_provider.generate(prompt)
    response.metadata["fallback_used"] = True
```

**Logged:** Error type, timestamp, fallback used

### Tool Call Failures
**Strategy:** Log error, continue with remaining tools, note in response

**Example:**
```python
tool_results = []
for tool in selected_tools:
    try:
        result = tool.execute()
        tool_results.append(result)
    except Exception as e:
        logger.error(f"Tool {tool.name} failed: {e}")
        tool_results.append({
            "tool": tool.name,
            "error": str(e),
            "fallback": None
        })
```

### Database Errors
**Strategy:** Rollback transaction, return user-friendly error

**Implementation:**
- SQLAlchemy transactions are explicit
- On error: `session.rollback()`
- Return structured error schema with `error_code` and `message`

---

## 5. Retry Logic

### LLM API Calls
**Strategy:** Exponential backoff with jitter

**Implementation:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError))
)
def call_llm_api(prompt):
    return openai_client.chat.completions.create(...)
```

### Embedding API Calls
**Strategy:** Same as LLM (3 retries, exponential backoff)

### Vector DB Queries
**Strategy:** Single retry on timeout

**Reasoning:** Vector DB queries should be fast; multiple retries indicate larger issue

---

## 6. Logging

### Structured Logging
**Library:** Python `logging` with JSON formatter

**Fields:**
- `timestamp` (UTC)
- `level` (INFO, WARNING, ERROR)
- `service` (e.g., "ChatService", "RAGService")
- `organization_id` (for tenant scoping)
- `user_id` (for attribution)
- `request_id` (for distributed tracing)
- `message`
- `metadata` (arbitrary JSON)

**Example:**
```json
{
  "timestamp": "2026-05-15T10:30:00Z",
  "level": "INFO",
  "service": "ChatService",
  "organization_id": "org_abc123",
  "user_id": "usr_def456",
  "request_id": "req_789xyz",
  "message": "Agent workflow completed",
  "metadata": {
    "intent": "knowledge_search",
    "tools_used": ["rag_search"],
    "latency_ms": 1250
  }
}
```

### Security: No Secrets in Logs
- API keys are **never** logged
- Passwords are **never** logged
- Email content is logged only in dev mode (redacted in production)
- PII is redacted via guardrails before logging

---

## 7. Observability

### 7.1 Audit Logs
**Purpose:** Compliance, debugging, security investigations

**Logged Actions:**
- User login/logout
- Document upload
- Approval request creation
- Approval decision (approve/reject)
- Agent action execution
- Quota limit exceeded

**Schema:**
```python
AuditLog(
    organization_id="org_abc",
    user_id="usr_def",
    action="document_uploaded",
    resource_type="Document",
    resource_id="doc_123",
    detail={"filename": "pricing.pdf", "size_bytes": 12345},
    ip_address="192.168.1.1",
    created_at=datetime.utcnow()
)
```

### 7.2 Usage Events
**Purpose:** Token tracking, cost estimation, quota enforcement

**Logged Events:**
- Every LLM call (input/output tokens)
- Every embedding call (input tokens)
- Every tool call
- Every RAG query

**Schema:**
```python
UsageEvent(
    organization_id="org_abc",
    user_id="usr_def",
    feature="chat_messages",
    model="gpt-4o-mini",
    provider="openai",
    input_tokens=150,
    output_tokens=300,
    estimated_cost=0.00045,
    fallback_used=False,
    latency_ms=1200,
    created_at=datetime.utcnow()
)
```

### 7.3 LangSmith Tracing
**Optional:** Enabled via `LANGSMITH_TRACING=true`

**Exported Data:**
- Full agent workflow trace
- LLM call inputs/outputs
- Tool call arguments/results
- Latency per step

**Usage:** Debugging, evaluation, optimization

---

## 8. Evaluation Approach

### 8.1 Intent Classification Evaluation
**Location:** `evaluation/intent_eval.py`

**Dataset:** 50 labeled examples per intent (400 total)

**Metrics:**
- Accuracy
- Precision, Recall, F1 per intent
- Confusion matrix

**Run Command:**
```bash
cd backend
python -m onepilot.evaluation.runner
```

### 8.2 RAG Evaluation
**Status:** Partial implementation

**Planned Metrics:**
- Answer relevance (LLM-as-judge)
- Faithfulness (context grounding)
- Retrieval precision@K
- Citation accuracy

**Approach:** RAGAS-style automated evaluation

---

## 9. Cost and Usage Tracking

### Token Counting
**Implementation:** `tiktoken` library for accurate token counting

**Where:**
- Before every LLM call (estimate)
- After every LLM call (actual from API response)
- Before every embedding call

### Cost Estimation
**Formula:**
```python
cost = (input_tokens / 1_000_000) * INPUT_PRICE + (output_tokens / 1_000_000) * OUTPUT_PRICE
```

**Pricing (as of 2024):**
- `gpt-4o-mini`: $0.15 / 1M input, $0.60 / 1M output
- `text-embedding-3-small`: $0.02 / 1M tokens

**Storage:** Every usage event includes `estimated_cost` field

### Usage Dashboard
**Frontend:** `frontend/src/app/usage/page.tsx`

**Displays:**
- Total tokens used (current period)
- Estimated cost
- Breakdown by feature (chat, RAG, email, etc.)
- Quota status

---

## 10. Layered Architecture Rationale

### Why Layers?
1. **Separation of concerns** — routers don't do business logic, services don't do SQL
2. **Testability** — mock repositories and providers in service tests
3. **Reusability** — services are called by both API routers and agent tools
4. **Maintainability** — changes to DB schema don't affect service contracts

### Layer Contracts
- **Routers:** Accept HTTP requests, validate schemas, return HTTP responses
- **Services:** Accept typed inputs, orchestrate business logic, return typed outputs
- **Repositories:** Accept entity operations, return domain models
- **Providers:** Accept external requests, return normalized results

---

## 11. Typed Schema Approach

### Why Pydantic?
1. **Runtime validation** — catch invalid data at API boundaries
2. **Auto-generated OpenAPI docs** — FastAPI integration
3. **Serialization** — JSON encoding/decoding
4. **IDE support** — autocomplete, type hints

### Schema Hierarchy
```
onepilot/schemas/
├── user.py          # UserCreate, UserRead, UserUpdate
├── organization.py  # OrganizationCreate, OrganizationRead, ...
├── document.py      # DocumentCreate, DocumentRead, ...
├── chat.py          # ChatRequest, ChatResponse, Message
├── lead.py          # LeadCreate, LeadRead, LeadUpdate
└── approval.py      # ApprovalRequest, ApprovalDecision
```

### Pattern
- `*Create` — for POST requests (no ID)
- `*Read` — for GET responses (includes ID, timestamps)
- `*Update` — for PATCH requests (all fields optional)

---

## 12. Security Considerations

### Authentication
- **JWT with HS256** — signed tokens with secret key
- **bcrypt password hashing** — salted, work factor 12
- **Dev auth bypass** — controlled via `DEV_AUTH_ENABLED` flag (disable in production)

### Authorization (RBAC)
- **4 roles:** Owner, Admin, Member, Viewer
- **Permission checks** at service layer
- **Role hierarchy:** Owner > Admin > Member > Viewer

### Tenant Isolation
- **Defense in depth:**
  1. JWT contains `organization_id`
  2. Service methods validate `organization_id` matches principal
  3. Repository queries filter by `organization_id`
  4. Vector collections are namespaced by `organization_id`

### Data at Rest
- **Postgres:** No encryption (add pgcrypto for production)
- **Redis:** No encryption (enable TLS for production)
- **Qdrant:** No encryption (enable TLS for production)

### Data in Transit
- **Local dev:** HTTP only
- **Production:** HTTPS required (terminate at reverse proxy)

---

## 13. Production Readiness Gaps

**Current Limitations:**
1. **No streaming** — synchronous LLM calls only
2. **No background workers** — all processing is request/response
3. **In-memory rate limiting** — resets on restart
4. **JWT in localStorage** — XSS vulnerability (use HTTP-only cookies in production)
5. **Mock external providers** — no real email/CRM/calendar integration
6. **No Redis session management** — stateless JWT only
7. **No file persistence** — uploaded files processed and discarded (chunks retained)

**See [limitations_roadmap.md](limitations_roadmap.md) for full list.**

---

## 14. Key Design Decisions

### Why LangGraph?
- **Explicit state management** — no hidden context
- **Node-based composition** — easy to visualize and debug
- **Conditional routing** — intent-based branching
- **Synchronous execution** — simpler than async/await for this use case

### Why Pydantic v2?
- **Performance** — 5-50x faster than v1
- **Better validation errors** — clear, actionable messages
- **Strict mode** — catch coercion bugs early

### Why SQLAlchemy 2.x?
- **Type-safe ORM** — mypy compatible
- **Improved performance** — lazy loading optimizations
- **AsyncIO support** — future-ready (not used yet)

### Why Qdrant?
- **Filtered search** — critical for tenant isolation
- **Payload storage** — no need for dual storage
- **Docker-friendly** — easy local dev setup

---

## Summary

OnePilot AI follows **production-grade AI engineering practices**:

✅ **Prompt templates** are versioned and testable  
✅ **RAG pipeline** includes weak evidence guardrails  
✅ **Security guardrails** detect prompt injection and redact sensitive data  
✅ **Error handling** with automatic fallback providers  
✅ **Structured logging** with tenant and request scoping  
✅ **Audit logs** for compliance and debugging  
✅ **Usage tracking** for cost estimation and quota enforcement  
✅ **Layered architecture** for separation of concerns  
✅ **Typed schemas** for runtime validation  
✅ **Tenant isolation** enforced at multiple layers  

These practices make OnePilot AI **maintainable, testable, secure, and scalable**.
