# Evaluation

> **Status:** Evaluation harness implemented in Phase 8.

---

## Philosophy

This evaluation is designed for a capstone project: it demonstrates awareness of AI evaluation best practices without requiring a full MLOps pipeline. The goal is to show that the system behaves correctly, safely, and consistently across the key dimensions that matter for a business AI product.

---

## Evaluation Dimensions

### 1. Intent Classification Accuracy

**What:** Does the router classify user messages into the correct intent?

**Method:** The `backend/src/onepilot/evaluation/` module runs a labeled dataset of sample inputs against the intent classifier and measures accuracy.

**Dataset:** 30+ samples spanning all 8 intents:
- `general_assistant`, `knowledge_search`, `lead_support`, `email_drafting`
- `document_summary`, `workflow_action`, `out_of_scope`, `clarification`

**Metric:** Classification accuracy (correct / total)

**Run:**
```bash
cd backend
python -m onepilot.evaluation.runner
```

**Expected result:** ≥ 85% accuracy on the labeled dataset with the fallback classifier; ≥ 92% with OpenAI.

---

### 2. RAG Retrieval Relevance

**What:** Does the retriever return relevant chunks for a given query?

**Method:** 20 sample queries with manually labeled expected source documents. Measure whether the correct document appears in the top-3 results.

**Metric:** Precision@3 (fraction of queries where the correct doc is in top-3)

**Dataset:** `backend/src/onepilot/evaluation/datasets.py` — `RAG_EVAL_QUERIES`

**Example queries:**
- "How much does the Growth retainer cost?" → expected: `pricing_plans.md`
- "What is NovaEdge's refund policy?" → expected: `refund_policy.md`
- "How does NovaEdge handle data privacy?" → expected: `data_privacy.md`

---

### 3. RAG Answer Faithfulness

**What:** Is the generated answer grounded in the retrieved documents? Does it avoid hallucination?

**Method:** Manual review of a sample of 20 answers against their source chunks. Checklist:
- [ ] Every factual claim is supported by a citation
- [ ] No facts are invented that are absent from the source documents
- [ ] Weak-evidence answers correctly decline to answer

**Note:** This is currently manual because automated faithfulness metrics (RAGAS-style) require embedding-based comparison that is expensive without a dedicated evaluation budget.

---

### 4. Safety / Guardrail Tests

**What:** Are prompt injection attempts blocked? Are out-of-scope requests declined gracefully?

**Method:** Automated test suite with known attack patterns.

**Coverage (from `tests/test_security.py` and related):**
- 15+ prompt injection patterns (all should be blocked)
- 10+ benign inputs that look suspicious but are legitimate (should not be blocked)
- Out-of-scope requests (should return `out_of_scope` intent)
- Cross-tenant access attempts (should return 403)

---

### 5. Backend Test Coverage

**Total:** 221 tests passing across all phases.

| Area | Test Count (approx.) |
|------|----------------------|
| Auth & tenancy | ~45 |
| Plans & quotas | ~20 |
| Demo data generators | ~15 |
| Document ingestion & chunking | ~25 |
| RAG search & answers | ~30 |
| Agent workflow & intents | ~35 |
| Tools & approvals | ~25 |
| Memory | ~15 |
| Usage events & audit logs | ~11 |

Run with coverage:
```bash
cd backend
pytest -v --cov=onepilot --cov-report=term-missing
```

---

### 6. End-to-End Workflow Tests

**What:** Does the full demo scenario (lead inquiry → RAG → email draft → approval) work end-to-end?

**Method:** Integration tests that spin up the FastAPI test client, seed demo data, and run the full chat → approval flow.

---

## Future Improvements (Post-Capstone)

### RAGAS-Style Evaluation
When an OpenAI API key is available:
- **Faithfulness:** cosine similarity between answer and retrieved context
- **Answer relevance:** similarity between generated answer and original question
- **Context precision / recall:** how much of the retrieved context is relevant

### A/B Testing
- Compare fallback vs. OpenAI embeddings on retrieval Precision@5
- Compare LLM-based vs. keyword-based intent classifier accuracy

### Online Evaluation
- Log user thumbs-up/thumbs-down feedback
- Track approval rate (what fraction of agent actions are approved vs. rejected)
- Track weak-evidence rate over time (decreases as more knowledge is uploaded)

---

## Limitations of This Evaluation

1. **Small sample sizes** — 20–30 samples are not statistically significant
2. **Manual labeling** — no inter-annotator agreement calculation
3. **Fallback providers** — evaluation with fallback embeddings and LLM will understate production quality
4. **Single language** — English-only evaluation
5. **No adversarial evaluation** — beyond the prompt injection patterns already tested
