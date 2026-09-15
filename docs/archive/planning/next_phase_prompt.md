# Recommended Next Prompt — Phase 3 + Phase 4

Copy and paste this into your next Cursor chat session:

---

## Prompt

Implement Phase 3 and Phase 4 of OnePilot AI.

### Phase 3: Demo Data (NovaEdge Solutions)

Generate 19 realistic knowledge base documents in `backend/src/onepilot/demo_data/novaedge_docs/`:

1. `company_profile.md` — NovaEdge Solutions B2B AI automation consultancy profile
2. `services_overview.md` — available services and capabilities
3. `pricing_plans.md` — starter, growth, enterprise pricing tiers
4. `sales_playbook.md` — sales methodology, qualification framework
5. `objection_handling.md` — common objections and rebuttals
6. `integration_guide_hubspot_gmail_calendar.md` — integration setup guides
7. `customer_faq.md` — frequently asked questions
8. `support_troubleshooting.md` — troubleshooting guide
9. `escalation_policy.md` — escalation procedures
10. `refund_policy.md` — refund and cancellation terms
11. `onboarding_guide.md` — new customer onboarding SOP
12. `customer_success_sop.md` — customer success playbook
13. `data_privacy_policy.md` — data handling and GDPR
14. `ai_usage_policy.md` — responsible AI usage guidelines
15. `security_policy.md` — security practices and compliance
16. `email_templates.md` — email templates for various scenarios
17. `discovery_call_script.md` — discovery call structure and questions
18. `demo_call_checklist.md` — demo preparation checklist
19. `sample_meeting_notes.md` — sample meeting notes from client calls

Each document should be 500-1500 words, realistic, and internally consistent with the NovaEdge brand.

Create `backend/src/onepilot/demo_data/generate_company_data.py`:
- Uses Faker with a fixed seed (42) for determinism
- Generates: 200 leads, 75 customers, 200 support tickets, 100 conversations, 50 email drafts, 30 appointments, usage events, approval requests, audit logs
- All scoped to `DEV_ORG_ID=org_demo_novaedge`
- Returns structured dicts (not DB models yet — the entity models come in Phase 5+)

Create `backend/src/onepilot/demo_data/seed.py`:
- Idempotent orchestrator that creates the demo org + user if missing
- Ingests the 19 knowledge base documents through the document service
- Safe to re-run

### Phase 4: RAG & Knowledge Base

Implement the RAG pipeline:

1. `backend/src/onepilot/rag/ingestion.py` — file reader for PDF, DOCX, TXT, MD, CSV (extract text + metadata)
2. `backend/src/onepilot/rag/chunking.py` — recursive character splitter (chunk_size ~500 tokens, overlap ~50)
3. `backend/src/onepilot/rag/retrieval.py` — hybrid retrieval: semantic search via Qdrant + keyword/metadata filtering
4. `backend/src/onepilot/rag/reranking.py` — simple score fusion (semantic + keyword scores)
5. `backend/src/onepilot/rag/citations.py` — generate citation objects from search results

Implement services:
1. `backend/src/onepilot/services/document_service.py` — upload, store metadata in Postgres, trigger ingestion + chunking + embedding + Qdrant upsert
2. `backend/src/onepilot/services/rag_service.py` — search knowledge base with hybrid retrieval, return citations

Add document-related models to `repositories/models.py`:
- `Document(id, organization_id, filename, content_type, size_bytes, chunk_count, status, uploaded_by, created_at, updated_at)`
- `DocumentChunk(id, document_id, organization_id, content, section, page_number, chunk_index, metadata, created_at)`

Add Alembic migration `0002_documents.py`.

Wire the Qdrant provider for real (use the existing `QdrantVectorProvider` stub) and keep `MemoryVectorProvider` as fallback.

Add API endpoints:
- `POST /documents/upload` — multipart file upload, validates file, ingests, returns document metadata
- `GET /documents` — list documents for current org
- `POST /knowledge/search` — hybrid search with citations

Add ~20 tests covering:
- Chunking edge cases (empty doc, very short doc, very long doc)
- Retrieval recall on seeded NovaEdge corpus (embed + search roundtrip with memory vector provider)
- Citation correctness (citation includes document title, section)
- File validation in ingestion pipeline
- Graceful behavior on weak evidence (low-score results)
- API endpoint integration tests

Do not implement the agent graph, tools, or approval system yet — those come in Phase 5+.
