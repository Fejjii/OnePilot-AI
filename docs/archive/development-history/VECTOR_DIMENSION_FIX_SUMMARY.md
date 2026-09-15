# Vector Dimension Mismatch Fix - Summary

## Problem Identified

After implementing real OpenAI providers, the app regressed:
- Documents showed 19 indexed and "Ready" in Postgres
- Knowledge Base search returned 0 results
- RAG answer returned: "I don't have a confident answer..." (weak-evidence-guard)
- UI showed: Model: `fallback-v1`, Fallback used: `true`

**Root Cause**: Dimension mismatch between embeddings providers
- System switched from fallback embeddings (384 dimensions) to OpenAI embeddings (1536 dimensions)
- Qdrant collection was recreated with new dimensions (automatic via `ensure_collection`)
- But existing documents in Postgres were not re-embedded
- Result: 19 documents in Postgres, 0 vectors in Qdrant

## Critical Bugs Fixed

### 1. Hardcoded Fallback Provider in Seed Endpoints
**File**: `backend/src/onepilot/api/routers/demo.py`

**Before**:
```python
result = seed_module.seed_knowledge_base(
    session,
    principal=principal,
    settings=settings,
    embeddings=FallbackEmbeddingsProvider(),  # FORCED FALLBACK
)
```

**After**:
```python
result = seed_module.seed_knowledge_base(
    session,
    principal=principal,
    settings=settings,
    # Uses configured provider (OpenAI when key exists, fallback otherwise)
)
```

### 2. No Automatic Reindexing on Provider Change
**File**: `backend/src/onepilot/demo_data/seed.py`

**Added**:
- Automatic detection when documents exist but vectors are missing
- Calls `reindex_organization_documents()` to re-embed all documents with current provider
- Debug logging showing provider, model, dimension, and vector counts
- Verification that fails fast if vectors are missing after seed

### 3. Qdrant Timeout Too Short
**File**: `backend/src/onepilot/providers/vector/qdrant_provider.py`

**Before**: `timeout=5.0` (caused timeouts during bulk upsert)  
**After**: `timeout=60.0` (handles bulk operations properly)

## Implementation Details

### Automatic Reindex Logic
```python
# Check if we need to reindex (documents exist but vectors are missing)
if existing_doc_count > 0:
    test_outcome = rag_service.search(...)
    if len(test_outcome.hits) == 0:
        # Reindex all documents with current embedding provider
        reindex_upserts = document_service.reindex_organization_documents(...)
```

### Debug Logging
```python
logger.info(
    "seed_start",
    organization_id=principal.organization_id,
    embedding_provider=embeddings_provider_name,  # "openai" or "fallback"
    embedding_model=embeddings_model,             # "text-embedding-3-small" or "fallback-embeddings"
    embedding_dimension=embeddings.dimension,     # 1536 or 384
    qdrant_collection=collection_name,
)
```

### Verification
Seed now fails fast with clear errors if:
- `document_count == 0` after seed
- `chunk_count == 0` but documents were created
- `vector_upsert_count == 0` but documents were created/reindexed
- `search_result_count == 0` but documents exist (indicates dimension mismatch)

## Provider Status Endpoint

`GET /providers` now returns detailed diagnostics:

```json
{
  "llm": {
    "configured": true,
    "active": true,
    "fallback_used": false,
    "provider": "openai",
    "model": "gpt-4o-mini"
  },
  "embeddings": {
    "configured": true,
    "active": true,
    "fallback_used": false,
    "provider": "openai",
    "model": "text-embedding-3-small",
    "dimension": 1536
  },
  "vector": {
    "configured": true,
    "active": true,
    "fallback_used": false,
    "provider": "qdrant"
  }
}
```

## Verification Results

### Before Fix
```bash
$ Invoke-RestMethod http://localhost:8000/knowledge/search
{
  "results": [],
  "total_found": 0,
  "weak_evidence": true,
  "fallback_used": true
}
```

### After Fix
```bash
$ docker compose build backend --no-cache
$ docker compose up -d
$ docker compose run --rm seed

# Seed output:
# - embedding_provider: openai
# - embedding_dimension: 1536
# - vector_upsert_count: 238 (reindexed all chunks)
# - search_result_count: 5

$ Invoke-RestMethod http://localhost:8000/knowledge/search
{
  "results": [5 results with OpenAI embeddings],
  "total_found": 5,
  "weak_evidence": false,
  "fallback_used": false
}
```

### Golden Query Test
**Query**: "What services does NovaEdge Solutions offer and what integrations are supported?"

**Result**:
```json
{
  "answer": "NovaEdge Solutions offers...HubSpot, Gmail/Google Workspace, Google Calendar...",
  "confidence": 0.9,
  "citations": [
    {"document_title": "NovaEdge Solutions — Services Overview", "score": 2.08},
    {"document_title": "Integration Guide — HubSpot, Gmail, Google Calendar", "score": 1.11}
  ],
  "weak_evidence": false,
  "fallback_used": false,
  "model": "gpt-4o-mini-2024-07-18"
}
```

✅ **All Requirements Met**:
1. Model shows `gpt-4o-mini` (not `fallback-v1`)
2. Fallback used: `false`
3. Sources include Services Overview and Integration Guide in top 5
4. Confidence: 90% (realistic, not inflated)
5. Answer mentions HubSpot, Gmail, Google Calendar
6. No weak evidence guard

## Behavior Summary

### When OPENAI_API_KEY is set:
- ✅ Uses OpenAI LLM (gpt-4o-mini)
- ✅ Uses OpenAI embeddings (text-embedding-3-small, 1536 dimensions)
- ✅ Seed automatically reindexes if vectors are missing
- ✅ Returns high-quality RAG answers
- ✅ `fallback_used=false` in all responses

### When OPENAI_API_KEY is missing:
- ✅ Uses fallback LLM (deterministic)
- ✅ Uses fallback embeddings (hash-based, 384 dimensions)
- ✅ System remains functional
- ✅ `fallback_used=true` with clear reason in logs

### On Provider Change:
- ✅ Seed detects dimension mismatch
- ✅ Automatically reindexes all documents
- ✅ Logs reindex reason and vector count
- ✅ Fails fast if reindex doesn't fix the issue

## Files Changed

1. `backend/src/onepilot/demo_data/seed.py` - Added reindex logic and verification
2. `backend/src/onepilot/api/routers/demo.py` - Removed hardcoded fallback provider
3. `backend/src/onepilot/providers/vector/qdrant_provider.py` - Increased timeout to 60s
4. `backend/tests/test_seed_reindex.py` - Added tests for reindex behavior (needs work due to quota requirements)

## Next Steps for Production

1. ✅ Build backend with fixes: `docker compose build backend --no-cache`
2. ✅ Restart services: `docker compose up -d`
3. ✅ Run seed: `docker compose run --rm seed`
4. ✅ Verify providers: `Invoke-RestMethod http://localhost:8000/providers`
5. ✅ Test search: `Invoke-RestMethod http://localhost:8000/knowledge/search`
6. ✅ Test in UI with golden query

## Monitoring

Check backend logs for seed events:
```bash
docker compose logs backend | grep seed_
```

Expected logs:
- `seed_start` - Shows provider, model, dimension
- `seed_reindex_required` - Triggered when vectors are missing
- `seed_reindexing` - Reindex starting
- `knowledge_base_reindexed` - Reindex complete with vector count
- `demo_seed_complete` - Final stats with verification

## Additional Notes

- Qdrant's `ensure_collection()` already handles dimension mismatches by recreating the collection
- The seed logic now detects when this happens and triggers reindex
- Reindex is idempotent - safe to run multiple times
- Fallback mode still works when no OpenAI key is present
- Provider selection happens at startup based on environment variables
