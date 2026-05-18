# Workflow Documentation

This document describes the end-to-end workflows in OnePilot AI, from user interaction to AI processing and external action execution.

---

## User Journey

```mermaid
flowchart TD
    Start([User Visits App]) --> Login{Authenticated?}
    Login -->|No| LoginPage[Login Page]
    LoginPage --> EnterCreds[Enter Email/Password]
    EnterCreds --> Auth[JWT Authentication]
    Auth --> Dashboard
    
    Login -->|Yes| Dashboard[Dashboard]
    Dashboard --> ChooseAction{Choose Action}
    
    ChooseAction -->|Ask Question| Workspace[AI Workspace]
    ChooseAction -->|Upload Docs| Knowledge[Knowledge Base]
    ChooseAction -->|View Leads| Leads[Leads Page]
    ChooseAction -->|Review Actions| Approvals[Approvals Queue]
    ChooseAction -->|Check Usage| Usage[Usage Dashboard]
    ChooseAction -->|View Memory| Memory[Memory Page]
    
    Workspace --> TypeMessage[Type Message]
    TypeMessage --> Submit[Submit to Agent]
    Submit --> Processing[AI Processing]
    Processing --> Response[Display Response]
    Response --> ApprovalNeeded{Action Needs<br/>Approval?}
    
    ApprovalNeeded -->|Yes| NotifyUser[Notify User]
    NotifyUser --> Approvals
    ApprovalNeeded -->|No| Complete[Conversation Updated]
    
    Approvals --> ReviewAction[Review Action Details]
    ReviewAction --> Decision{Approve or<br/>Reject?}
    Decision -->|Approve| Execute[Execute Action]
    Decision -->|Reject| Decline[Mark Rejected]
    Execute --> AuditLog[Log to Audit]
    Decline --> AuditLog
    
    Knowledge --> UploadDoc[Upload Document]
    UploadDoc --> ProcessDoc[Chunk & Embed]
    ProcessDoc --> SearchReady[Document Searchable]
    
    Complete --> End([Continue Using App])
    AuditLog --> End
    SearchReady --> End
```

---

## AI Workflow

```mermaid
flowchart TD
    Start([User Message<br/>Received]) --> ExtractContext[Extract Context:<br/>org_id, user_id,<br/>conversation_id]
    
    ExtractContext --> SafetyCheck{Safety<br/>Guardrails}
    SafetyCheck -->|Blocked| SafetyReject[Return Safety Error<br/>+ Log Audit Event]
    SafetyCheck -->|Pass| IntentClassify[Intent Classification<br/>via LLM]
    
    IntentClassify --> QuotaCheck{Check Quota:<br/>chat_messages}
    QuotaCheck -->|Exceeded| QuotaError[Return Quota Error]
    QuotaCheck -->|Available| RouteIntent{Route by Intent}
    
    RouteIntent -->|knowledge_search| RAGPath[RAG Path]
    RouteIntent -->|lead_support| LeadPath[Lead Path]
    RouteIntent -->|email_drafting| EmailPath[Email Path]
    RouteIntent -->|general_assistant| GeneralPath[General Path]
    RouteIntent -->|workflow_action| WorkflowPath[Workflow Path]
    RouteIntent -->|out_of_scope| Decline[Polite Decline]
    RouteIntent -->|clarification| Clarify[Ask Clarification]
    
    RAGPath --> RetrieveKnowledge[Query Vector Store<br/>Retrieve Top K Chunks]
    RetrieveKnowledge --> RankChunks[Rank by Similarity]
    RankChunks --> GenerateRAG[Generate Answer<br/>with Citations]
    GenerateRAG --> Synthesize
    
    LeadPath --> LookupLead[Lookup Lead<br/>from CRM]
    LookupLead --> UpdateOrRead{Update<br/>Needed?}
    UpdateOrRead -->|Read Only| Synthesize[Synthesize Response]
    UpdateOrRead -->|Update| LeadUpdate[Mark Approval Required]
    LeadUpdate --> Synthesize
    
    EmailPath --> DraftEmail[Draft Email<br/>via LLM]
    DraftEmail --> SendCheck{Send<br/>Requested?}
    SendCheck -->|Yes| EmailApproval[Mark Approval Required]
    SendCheck -->|No| Synthesize
    EmailApproval --> Synthesize
    
    GeneralPath --> LLMCall[Direct LLM Call<br/>No Tools]
    LLMCall --> Synthesize
    
    WorkflowPath --> SelectTools[Select Tools:<br/>CRM, Calendar, etc.]
    SelectTools --> ExternalAction[Mark Approval Required]
    ExternalAction --> Synthesize
    
    Synthesize --> ApprovalCheck{Approval<br/>Required?}
    ApprovalCheck -->|Yes| CreateApprovalReq[Create ApprovalRequest<br/>in Database]
    ApprovalCheck -->|No| LogUsage[Log UsageEvent<br/>+ AuditLog]
    
    CreateApprovalReq --> LogUsage
    LogUsage --> UpdateMemory[Update Conversation<br/>and Long-Term Memory]
    UpdateMemory --> ReturnResponse[Return Response<br/>to User]
    
    Decline --> ReturnResponse
    Clarify --> ReturnResponse
    SafetyReject --> ReturnResponse
    QuotaError --> ReturnResponse
```

---

## RAG Workflow

```mermaid
flowchart TD
    Start([User Query]) --> PreProcess[Pre-process Query:<br/>lowercase, trim]
    PreProcess --> EmbedQuery[Embed Query<br/>via Embedding Provider]
    
    EmbedQuery --> VectorSearch[Vector Similarity Search<br/>in Qdrant]
    VectorSearch --> FilterTenant[Filter by<br/>organization_id]
    FilterTenant --> TopK[Retrieve Top K<br/>Chunks]
    
    TopK --> Threshold{Similarity<br/>&gt; Threshold?}
    Threshold -->|No| NoEvidence[Return:<br/>&quot;Not enough evidence&quot;]
    Threshold -->|Yes| RankChunks[Rank Chunks<br/>by Relevance]
    
    RankChunks --> BuildPrompt[Build Prompt:<br/>Query + Context]
    BuildPrompt --> LLMGenerate[Generate Answer<br/>via LLM]
    
    LLMGenerate --> ExtractCitations[Extract Citations<br/>from Chunks]
    ExtractCitations --> GroundCheck{Answer<br/>Grounded?}
    
    GroundCheck -->|No| Refuse[Refuse to Answer<br/>+ Log Warning]
    GroundCheck -->|Yes| FormatResponse[Format Response<br/>with Citations]
    
    FormatResponse --> LogRAGUsage[Log UsageEvent:<br/>rag_queries]
    LogRAGUsage --> Return([Return to User])
    
    NoEvidence --> Return
    Refuse --> Return
```

---

## Agent Workflow

The agent workflow follows LangGraph's node-based orchestration. See [agent_workflow.md](agent_workflow.md) for detailed implementation.

### High-Level Agent Flow

1. **Safety Check** — prompt injection detection, sensitive data scanning
2. **Intent Classification** — route to appropriate handler
3. **Quota Check** — enforce plan limits
4. **Tool Selection** — agent picks relevant tools based on intent
5. **Tool Execution** — call RAG, CRM, email, calendar, etc.
6. **Approval Gate** — create approval request if external action is needed
7. **Response Synthesis** — generate user-facing response
8. **Memory Update** — persist conversation and learned facts
9. **Usage Logging** — record tokens, cost, latency

---

## Human Approval Workflow

```mermaid
flowchart TD
    Start([Agent Wants to<br/>Perform Action]) --> CheckType{Action Type}
    
    CheckType -->|Read-Only| DirectExecute[Execute Immediately]
    CheckType -->|External Write| CreateRequest[Create ApprovalRequest]
    
    CreateRequest --> StoreDB[(Store in Postgres:<br/>status = pending)]
    StoreDB --> NotifyUser[Notify User:<br/>&quot;Action pending approval&quot;]
    
    NotifyUser --> UserReview[User Opens<br/>Approvals Page]
    UserReview --> ViewDetails[View Action Details:<br/>payload, reason, risk]
    
    ViewDetails --> Decision{User Decision}
    Decision -->|Approve| MarkApproved[Update status:<br/>approved]
    Decision -->|Reject| MarkRejected[Update status:<br/>rejected]
    
    MarkApproved --> ExecuteAction[Execute Action<br/>via Provider]
    ExecuteAction --> LogSuccess[Log AuditLog:<br/>action_executed]
    
    MarkRejected --> LogReject[Log AuditLog:<br/>action_rejected]
    
    DirectExecute --> LogDirect[Log AuditLog:<br/>action_executed]
    
    LogSuccess --> Done([Complete])
    LogReject --> Done
    LogDirect --> Done
```

---

## Document Ingestion Workflow

```mermaid
flowchart TD
    Start([User Uploads<br/>Document]) --> ValidateFile{File Type<br/>Supported?}
    
    ValidateFile -->|No| RejectFile[Reject:<br/>unsupported type]
    ValidateFile -->|Yes| CheckQuota{Storage<br/>Quota OK?}
    
    CheckQuota -->|Exceeded| QuotaError[Return Quota Error]
    CheckQuota -->|Available| ParseFile[Parse Document:<br/>markdown, text,<br/>PDF, DOCX]
    
    ParseFile --> SectionSplit[Split by Sections:<br/>headers, paragraphs]
    SectionSplit --> ChunkContent[Chunk Content:<br/>~500 tokens per chunk]
    
    ChunkContent --> StoreDB[(Store Document<br/>+ Chunks in Postgres)]
    StoreDB --> EmbedChunks[Embed Each Chunk<br/>via Embedding Provider]
    
    EmbedChunks --> UpsertVector[Upsert to Vector DB<br/>with metadata]
    UpsertVector --> UpdateQuota[Update UsageQuota:<br/>document_uploads,<br/>storage_mb]
    
    UpdateQuota --> LogAudit[Log AuditLog:<br/>document_uploaded]
    LogAudit --> Success([Document Ready<br/>for Search])
    
    RejectFile --> Error([Error Response])
    QuotaError --> Error
```

---

## Notes

- All workflows enforce **tenant isolation** — every query includes `organization_id`
- All external actions log to **AuditLog** with actor, timestamp, and payload
- All LLM/embedding calls log to **UsageEvent** with token counts and cost estimates
- All approval requests create a database record before execution
- Fallback providers activate automatically when real API keys are missing
