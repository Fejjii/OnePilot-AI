# Evaluation

> **Status:** Evaluation harness implemented with JSON and Markdown reporting.

---

## Philosophy

This evaluation is designed for a capstone project: it demonstrates awareness of AI evaluation best practices without requiring a full MLOps pipeline. The goal is to show that the system behaves correctly, safely, and consistently across the key dimensions that matter for a business AI product.

---

## Running Evaluations

### Quick Start

Run all evaluations and generate combined report:

```bash
cd backend
python -m onepilot.evaluation.run_all_evals
```

This will:
1. Run intent classification evaluation
2. Run RAG retrieval evaluation
3. Generate combined JSON and Markdown reports in `reports/evaluation/`

### Individual Evaluations

**Intent Classification:**
```bash
python -m onepilot.evaluation.run_intent_eval
```

**RAG Retrieval:**
```bash
python -m onepilot.evaluation.run_rag_eval
```

### Custom Output

**Save to custom location:**
```bash
python -m onepilot.evaluation.run_intent_eval \
  --json-output custom/path/intent.json \
  --markdown-output custom/path/intent.md
```

**JSON output to stdout:**
```bash
python -m onepilot.evaluation.run_intent_eval --json
```

---

## Evaluation Dimensions

### 1. Intent Classification Accuracy

**What:** Does the router classify user messages into the correct intent?

**Method:** The `backend/src/onepilot/evaluation/run_intent_eval.py` script runs a labeled dataset of sample inputs against the intent classifier and measures accuracy.

**Dataset:** 30+ samples spanning all 8 intents:
- `general_assistant`, `knowledge_search`, `lead_support`, `email_drafting`
- `document_summary`, `workflow_action`, `out_of_scope`, `clarification`

**Metric:** Classification accuracy (correct / total)

**Target:** ≥ 85% accuracy on the labeled dataset

**Run:**
```bash
cd backend
python -m onepilot.evaluation.run_intent_eval
```

**Output:**
- Console summary with accuracy and confusion matrix
- `reports/evaluation/intent_eval_latest.json` - Machine-readable results
- `reports/evaluation/intent_eval_latest.md` - Human-readable report

**Example output:**
```
Dataset: .../datasets/intent_eval.jsonl
Total:    32
Correct:  29
Accuracy: 90.62%

Per-intent accuracy:
  general_assistant      4/4   (100%)
  knowledge_search       5/5   (100%)
  lead_support          3/4   (75%)
  ...
```

---

### 2. RAG Retrieval Relevance

**What:** Does the retriever return relevant chunks for a given query?

**Method:** Golden query-document pairs are evaluated. Measures whether the correct document appears in the top-3 results (Precision@3).

**Metric:** Precision@3 and Recall@3

**Target:** ≥ 70% precision@3

**Run:**
```bash
cd backend
python -m onepilot.evaluation.run_rag_eval
```

**Output:**
- Console summary with precision/recall metrics
- `reports/evaluation/rag_eval_latest.json` - Machine-readable results
- `reports/evaluation/rag_eval_latest.md` - Human-readable report

**Example queries:**
- "How much does the Growth retainer cost?" → expected: `pricing_plans.md`
- "What is NovaEdge's refund policy?" → expected: `refund_policy.md`
- "How does NovaEdge handle data privacy?" → expected: `data_privacy.md`

**Note:** The current RAG eval implementation is a placeholder demonstrating the structure. For production use:
1. Seed knowledge base with test documents
2. Implement actual vector search against test queries
3. Compare retrieved documents against expected_documents list

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

**Total:** 494 tests passing (3 skipped in default CI/local runs).

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
| LangSmith tracing | ~10 |

Run with coverage:
```bash
cd backend
pytest -v --cov=onepilot --cov-report=term-missing
```

---

### 6. Tracing and Observability Evaluation

**What:** Are traces properly captured in both local and LangSmith modes?

**Method:** Tests verify that:
- Local trace mode works when LangSmith is disabled
- LangSmith live mode activates when configured with valid API key
- Trace metadata (trace_id, trace_url) is properly returned
- Sensitive data is redacted from trace metadata

**Verification:**

**Without LangSmith configured:**
```bash
# Provider diagnostics should show:
# LangSmith: mode=local, reason="LANGSMITH_API_KEY not set"

curl http://localhost:8000/providers | jq '.providers[] | select(.name=="LangSmith")'
```

**With LangSmith configured:**
```bash
# Set environment variables:
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=your_key_here
export LANGSMITH_PROJECT=onepilot-ai

# Provider diagnostics should show:
# LangSmith: mode=live, project=onepilot-ai, healthy=true

# Chat response should include trace_url
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test query"}' | jq '.trace_mode, .trace_url'
```

---

### 7. End-to-End Workflow Tests

**What:** Does the full demo scenario (lead inquiry → RAG → email draft → approval) work end-to-end?

**Method:** Integration tests that spin up the FastAPI test client, seed demo data, and run the full chat → approval flow.

---

## Evaluation Reports

All evaluation scripts generate both JSON (machine-readable) and Markdown (human-readable) reports in `reports/evaluation/`:

- `intent_eval_latest.json` / `intent_eval_latest.md` - Intent classification results
- `rag_eval_latest.json` / `rag_eval_latest.md` - RAG retrieval results  
- `latest.json` / `latest.md` - Combined evaluation summary

### Report Contents

**JSON reports include:**
- Test name and timestamp
- All raw metrics and scores
- Per-category breakdown
- Individual test case results
- Full failure details

**Markdown reports include:**
- Executive summary with pass/fail status
- Metrics tables
- Category performance breakdown
- Visual indicators (✓/✗)
- Actionable recommendations

### Viewing Reports

```bash
# View combined summary
cat reports/evaluation/latest.md

# View intent eval details
cat reports/evaluation/intent_eval_latest.md

# Parse JSON programmatically
python -c "import json; print(json.load(open('reports/evaluation/latest.json'))['summary'])"
```

---

## Current Status (Phase 9)

✅ **Implemented:**
- Intent classification evaluation with 32 test cases
- RAG retrieval evaluation framework (placeholder implementation)
- JSON and Markdown report generation
- Combined evaluation runner (`run_all_evals.py`)
- LangSmith live tracing with local fallback
- Trace mode visibility in AI Workspace UI
- Provider diagnostics for LangSmith status

⚠️ **Limitations:**
- RAG evaluation uses golden queries but needs vector store integration
- No automated RAGAS-style faithfulness metrics yet
- Sample sizes are small (suitable for capstone, not production)
- Manual review still needed for edge cases

🔄 **In Progress:**
- Expanding test coverage for tracing
- Adding more RAG golden query pairs
- Improving failure case documentation

---

## Future Improvements (Post-Capstone)

### RAGAS-Style Evaluation
When an OpenAI API key is available:
- **Faithfulness:** cosine similarity between answer and retrieved context
- **Answer relevance:** similarity between generated answer and original question
- **Context precision / recall:** how much of the retrieved context is relevant

### LangSmith Dataset Evaluation
- Upload golden test cases to LangSmith datasets
- Run evaluations directly in LangSmith platform
- Compare multiple model versions or configurations
- Track evaluation metrics over time
- Set up automated evaluation on PR/deploy

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
4. **Limited multilingual eval** — multilingual chat/RAG covered by pytest; no separate RAGAS suite per language yet
5. **No adversarial evaluation** — beyond the prompt injection patterns already tested
