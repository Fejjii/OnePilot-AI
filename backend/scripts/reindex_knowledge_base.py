#!/usr/bin/env python3
"""
reindex_knowledge_base.py — Rebuild chunks and vector index for an organization.

Does not create duplicate documents. Reuses existing rows and upserts vectors with
stable point ids (organization_id, document_id, chunk ordinal).

Usage
-----
    uv run python scripts/reindex_knowledge_base.py --organization-id org_demo_onepilot
    uv run python scripts/reindex_knowledge_base.py --organization-id org_demo_onepilot --source-dir src/onepilot/demo_data/novaedge_docs
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from onepilot.core.config import get_settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.logging import configure_logging
from onepilot.demo_data.seed import NOVAEDGE_DOCS_DIR
from onepilot.providers import get_embeddings_provider, get_vector_provider
from onepilot.repositories.organizations import OrganizationRepository
from onepilot.repositories.session import SessionLocal, init_db
from onepilot.security.auth import Principal
from onepilot.services import document_service


def _validate_qdrant(
    *,
    settings,
    vector,
    collection: str,
    principal: Principal,
    embeddings,
) -> tuple[bool, int, int]:
    """Return (collection_exists, point_count, sample_search_hits). Never logs secrets."""
    if not settings.has_qdrant:
        return False, 0, 0

    point_count = 0
    collection_exists = False
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            prefer_grpc=False,
            timeout=30.0,
        )
        info = client.get_collection(collection)
        collection_exists = True
        point_count = int(getattr(info, "points_count", 0) or 0)
    except Exception as exc:
        print(f"  Qdrant collection check failed: {exc}")
        return False, 0, 0

    sample_hits = 0
    if point_count > 0:
        from onepilot.services import rag_service

        session = SessionLocal()
        try:
            outcome = rag_service.search(
                session,
                principal=principal,
                query="NovaEdge services integrations HubSpot Gmail Calendar",
                top_k=3,
                settings=settings,
                embeddings=embeddings,
                vector=vector,
                enforce_quota=False,
            )
            sample_hits = len(outcome.hits)
        finally:
            session.close()

    return collection_exists, point_count, sample_hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reindex knowledge base vectors for an organization")
    parser.add_argument("--organization-id", required=True)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=NOVAEDGE_DOCS_DIR,
        help="Directory of markdown sources used to rebuild missing chunks (demo seed files)",
    )
    parser.add_argument("--user-id", default=None, help="Optional user id for audit context")
    args = parser.parse_args(argv)

    configure_logging()
    settings = get_settings()
    init_db()

    session = SessionLocal()
    try:
        org_repo = OrganizationRepository(session)
        if not org_repo.get(args.organization_id):
            print(f"Organization not found: {args.organization_id}")
            return 1

        principal = Principal(
            user_id=args.user_id or settings.DEV_USER_ID,
            organization_id=args.organization_id,
            role=Role.OWNER,
            plan_code=PlanCode.BUSINESS,
        )

        embeddings = get_embeddings_provider(settings)
        vector = get_vector_provider(settings)

        result = document_service.reindex_knowledge_base(
            session,
            principal=principal,
            settings=settings,
            embeddings=embeddings,
            vector=vector,
            source_dir=args.source_dir,
            rebuild_missing_chunks=True,
        )
    finally:
        session.close()

    collection_exists, point_count, sample_hits = _validate_qdrant(
        settings=settings,
        vector=vector,
        collection=result.qdrant_collection,
        principal=principal,
        embeddings=embeddings,
    )

    print("\nReindex result:")
    print(f"  documents_seen     : {result.documents_seen}")
    print(f"  documents_created  : {result.documents_created}")
    print(f"  documents_skipped  : {result.documents_skipped}")
    print(f"  chunks_created     : {result.chunks_created}")
    print(f"  chunks_reindexed   : {result.chunks_reindexed}")
    print(f"  vector_upserts     : {result.vector_upserts}")
    print(f"  qdrant_collection  : {result.qdrant_collection}")
    print(f"  provider_mode      : {result.provider_mode}")
    print(f"  qdrant_configured  : {result.qdrant_configured}")
    print(f"  sample_search_hits : {result.sample_search_hits}")

    if result.qdrant_configured:
        print("\nQdrant validation:")
        print(f"  collection_exists  : {collection_exists}")
        print(f"  vector_count       : {point_count}")
        print(f"  sample_search_hits : {sample_hits}")

    if result.vector_upserts == 0 and result.documents_seen > 0:
        print("\n[WARN] No vectors upserted. Ensure source markdown files exist for missing chunks.")
        return 1

    if result.qdrant_configured and point_count == 0:
        print("\n[WARN] Qdrant collection has zero points after reindex.")
        return 1

    print("\n✓ Reindex complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
