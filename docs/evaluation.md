# Evaluation & Quality

> **Status:** Deterministic offline evaluation harness, JSON/Markdown reports, `GET /evaluation/summary` API, and an **Evaluation** page in the UI.

---

## Philosophy

These checks are for **demo-quality regression gating**: they show how routing, RAG, and safety are tested without requiring RAGAS, LangSmith datasets, or OpenAI keys in CI.

These are deterministic demo-quality regression checks on a small labeled
dataset. They are not a claim that the AI system is universally 100% accurate.

They are **not** a production SLO, a RAGAS scorecard, or a substitute for human evaluation.

---

## Quick start

Run all suites and write combined reports:

```bash
cd backend
uv run python -m onepilot.evaluation.run_all_evals
```

Outputs:

| File | Purpose |
|------|---------|
| `reports/evaluation/latest.json` | Combined metrics for API + UI |
| `reports/evaluation/latest.md` | Human-readable summary |
| `reports/evaluation/intent_eval_latest.{json,md}` | Routing & intent details |
| `reports/evaluation/rag_eval_latest.{json,md}` | RAG golden set |
| `reports/evaluation/safety_eval_latest.{json,md}` | Guardrails & HITL policy |

View in the app: open **Evaluation** in the sidebar (after running the script above).

---

## Individual scripts

| Script | Dataset |
|--------|---------|
| `python -m onepilot.evaluation.run_intent_eval` | `evaluation/datasets/intent_eval.jsonl` |
| `python -m onepilot.evaluation.run_rag_eval` | `evaluation/datasets/rag_eval.jsonl` |
| `python -m onepilot.evaluation.run_safety_eval` | `evaluation/datasets/safety_eval.jsonl` |

---

## Metrics (combined `latest.json`)

Current **79-case deterministic evaluation suite** (offline report):

| Metric | Result | Meaning |
|--------|--------|---------|
| Intent accuracy | 100% | Stage-2 intent matches labeled intent (two-stage routing) |
| Routing accuracy | 100% | Stage-1 message class matches label |
| RAG golden pass | 100% | RAG golden cases pass source + citation + weak-evidence rules |
| Citation presence | 100% | Cases where citations expected vs actual (offline heuristic) |
| Source hit rate | 90% | Expected demo doc appears in top retrieved stems |
| Weak-evidence correctness | 100% | Out-of-KB / low-confidence cases flagged correctly |
| Safety / HITL pass | 100% | Injection blocked / approval policy cases pass |
| Total cases | 79 | Sum of cases across suites |
| Failed cases | 0 | Count of failures (listed in report) |

These are deterministic demo-quality regression checks on a small labeled
dataset. They are not a claim that the AI system is universally 100% accurate.

---

## What each suite covers

### Routing & intent (`intent_eval.jsonl`)

- Capability / help, small talk, correction / meta  
- Business knowledge, email drafting, lead qualification  
- Workflow actions, out of scope, ambiguous clarification  

Uses production two-stage flow: `classify_message` → `classify(..., message_class=...)`.

### RAG golden (`rag_eval.jsonl`)

- Services & integrations, pricing, refund policy  
- Onboarding, escalation, security & privacy  
- German / French / Spanish integration or services queries  
- Out-of-knowledge query (weak evidence expected)  

Offline keyword scoring over `demo_data/novaedge_docs/` — does **not** call the live vector store (no API cost, deterministic).

### Safety & HITL (`safety_eval.jsonl`)

- Prompt injection, bypass approval, reveal system prompt  
- Expose API key, send email without approval  
- Cross-tenant policy assertion, unsupported unsafe requests  
- Approval gating: `send_email` / `update_crm` require approval; `rag_search` does not  

---

## API

`GET /evaluation/summary` — reads `reports/evaluation/latest.json` if present.

Empty state when no report:

```json
{
  "available": false,
  "message": "Evaluation report not generated yet. Run backend evaluation script.",
  "run_command": "cd backend && uv run python -m onepilot.evaluation.run_all_evals"
}
```

Evaluations are **never** run inside the HTTP request.

---

## Human-in-the-loop (approval safety)

Documented on the Evaluation page and in `safety_eval` reports:

- Sensitive actions require approval  
- AI can draft but not send without approval  
- Decisions are audit-logged  
- Admin/Owner roles review the Approvals queue  

---

## Limitations

1. Small labeled sets (demo scope, not statistically significant)  
2. RAG eval uses keyword overlap on demo docs, not live embeddings  
3. No RAGAS faithfulness / answer relevancy automation  
4. Multilingual RAG labels are heuristic; human review recommended  
5. Intent labels document **current** router behavior for regression tracking  

---

## Future roadmap (optional)

When budget and stability allow:

| Track | Items |
|-------|--------|
| **RAGAS** | Faithfulness, context precision, context recall, answer relevancy |
| **LangSmith** | Golden datasets, PR regression, multi-model comparison |
| **CI** | Fail build if metrics drop below thresholds |
| **Online** | Thumbs-up/down, approval rate, weak-evidence rate over time |

---

## Related testing

Stable wording for this release (do not treat exact pytest counts as a product SLO):

- **900+** backend tests in CI — auth, RAG, agents, Serper, Gmail, Calendar, approvals, memory isolation, security, demo entry
- **180** frontend tests — pages, landing, demo flow, components
- **53** release/script tests
- Type checking, production builds, GitHub Actions CI, public smoke testing
- Golden RAG integration tests: `backend/tests/test_golden_rag.py`
- Security basics: `backend/tests/test_security_basics.py`
- Evaluation API: `backend/tests/test_evaluation_summary.py`
- UI: `frontend/src/app/(app)/evaluation/evaluation.test.tsx`
