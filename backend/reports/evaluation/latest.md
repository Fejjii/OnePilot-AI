# OnePilot AI — Evaluation & Quality Summary

**Generated:** 2026-07-19T15:23:34.187073+00:00

These are deterministic evaluation checks for demo-quality gating. They are not a replacement for full production RAGAS or human evaluation.

## Quality metrics

| Metric | Value |
|--------|-------|
| Intent accuracy | 100.0% |
| Routing accuracy | 100.0% |
| RAG golden pass rate | 100.0% |
| Citation presence rate | 100.0% |
| Source hit rate | 90.0% |
| Weak-evidence correctness | 100.0% |
| Safety guardrail pass rate | 100.0% |
| Total cases | 68 |
| Failed cases | 0 |

## How to regenerate

```bash
cd backend && uv run python -m onepilot.evaluation.run_all_evals
```

## Limitations

- Small labeled datasets (demo scope, not statistically significant).
- RAG eval uses deterministic keyword scoring over demo docs, not live vector search.
- No automated RAGAS faithfulness or LangSmith dataset runs in this harness.
- Multilingual RAG cases use offline heuristics; production quality needs human review.

## Future roadmap (RAGAS / LangSmith)

- RAGAS faithfulness
- RAGAS context precision
- RAGAS context recall
- RAGAS answer relevancy
- LangSmith evaluation datasets and regression runs on deploy