# OnePilot AI Evaluation Summary

**Generated:** 2026-05-18T17:01:31.998531+00:00

## Overall Results

- **Tests passed:** 1/2
- **Overall status:** ❌ FAIL

## Test Results

### Intent Classification

- **Accuracy:** 100.00%
- **Total cases:** 30
- **Correct:** 30
- **Status:** ✅ PASS (≥85%)

[View detailed intent eval report](intent_eval_latest.md)

### RAG Retrieval

- **Precision@3:** 0.00%
- **Recall@3:** 0.00%
- **Total queries:** 5
- **Status:** ❌ FAIL (<70%)

[View detailed RAG eval report](rag_eval_latest.md)

## Recommendations

The evaluation suite has identified areas for improvement:

- **RAG retrieval:** Precision@3 (0.00%) is below target (70%). Consider improving embeddings or document chunking strategy.

## Next Steps

1. Review individual test reports for detailed breakdowns
2. Address any failing tests before deployment
3. Consider running continuous evaluation in CI/CD pipeline
4. Expand test coverage with additional edge cases
