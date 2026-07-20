"""Seed a demo organization with the NovaEdge knowledge base.

The seeder is idempotent: re-running it does not duplicate documents.
Run it programmatically or via the `POST /demo/seed` API endpoint.

Deterministic demo identity
---------------------------
DEV_ORG_ID  = org_demo_onepilot   (set in .env / Settings)
DEV_USER_ID = usr_demo_admin       (set in .env / Settings)

Both the dev-auth bypass (no Bearer token) and the seed script resolve to the
same IDs, so /documents always returns the seeded content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.core.constants import PlanCode, Role
from onepilot.core.ids import new_id
from onepilot.core.logging import get_logger
from onepilot.providers import get_embeddings_provider, get_vector_provider
from onepilot.providers.embeddings.base import EmbeddingsProvider
from onepilot.providers.vector.base import VectorProvider
from onepilot.demo_data.generators import (
    generate_audit_logs,
    generate_usage_events,
)
from onepilot.repositories.approvals import ApprovalRequestRepository
from onepilot.repositories.audit import AuditLogRepository
from onepilot.repositories.documents import DocumentChunkRepository, DocumentRepository
from onepilot.repositories.leads import LeadRepository
from onepilot.repositories.models import (
    ApprovalRequest,
    AuditLog,
    Lead,
    Organization,
    OrganizationMember,
    Subscription,
    UsageEvent,
    User,
)
from onepilot.repositories.organizations import OrganizationMemberRepository, OrganizationRepository
from onepilot.repositories.plans import SubscriptionRepository
from onepilot.repositories.usage_events import UsageEventRepository
from onepilot.repositories.users import UserRepository
from onepilot.security.auth import Principal, hash_password
from onepilot.services import document_service

logger = get_logger(__name__)

DEMO_EMAIL = "admin@onepilot.ai"
DEMO_PASSWORD = "Demo1234!"
DEMO_FULL_NAME = "Demo Admin"
DEMO_ORG_NAME = "OnePilot AI"
DEMO_ORG_SLUG = "onepilot-ai-demo"

NOVAEDGE_DOCS_DIR: Path = Path(__file__).resolve().parent / "novaedge_docs"

# Curated NovaEdge-style leads for reviewer-friendly demos (deterministic).
CURATED_DEMO_LEADS: list[dict[str, str]] = [
    {
        "name": "Sarah Chen",
        "company": "Brightline Analytics",
        "email": "sarah.chen@brightline.io",
        "source": "demo_request",
        "status": "qualified",
        "urgency": "high",
        "intent": "demo",
        "pain_point": "Support team overwhelmed during product launches",
        "summary": "VP Operations exploring AI workspace for support automation and HubSpot sync.",
        "recommended_next_action": "Schedule discovery call and share Growth plan pricing.",
    },
    {
        "name": "Marcus Webb",
        "company": "Northwind Legal",
        "email": "marcus.webb@northwindlegal.com",
        "source": "referral",
        "status": "proposal",
        "urgency": "medium",
        "intent": "purchase",
        "pain_point": "Manual email triage for client intake",
        "summary": "Managing partner wants grounded answers from internal playbooks before client calls.",
        "recommended_next_action": "Send proposal for Business plan with approval gates enabled.",
    },
    {
        "name": "Elena Rossi",
        "company": "Helio Commerce",
        "email": "elena.rossi@heliocommerce.eu",
        "source": "linkedin",
        "status": "contacted",
        "urgency": "medium",
        "intent": "partnership",
        "pain_point": "Needs multilingual support for EU customers",
        "summary": "Head of CX evaluating RAG over policy docs with DE/FR response language.",
        "recommended_next_action": "Demo multilingual workspace and knowledge search.",
    },
    {
        "name": "James Okonkwo",
        "company": "Summit Field Services",
        "email": "j.okonkwo@summitfield.com",
        "source": "website",
        "status": "new",
        "urgency": "low",
        "intent": "demo",
        "pain_point": "Technicians repeat the same troubleshooting steps",
        "summary": "Operations lead downloaded pricing PDF and requested a walkthrough.",
        "recommended_next_action": "Send onboarding guide and offer a 30-minute demo.",
    },
    {
        "name": "Priya Nair",
        "company": "Atlas Health Clinics",
        "email": "priya.nair@atlashealth.org",
        "source": "conference",
        "status": "qualified",
        "urgency": "high",
        "intent": "purchase",
        "pain_point": "Strict audit requirements for AI-assisted workflows",
        "summary": "Compliance officer needs human approval before any external CRM or email action.",
        "recommended_next_action": "Walk through Approvals queue and audit log export.",
    },
    {
        "name": "Tom Berger",
        "company": "Riverstone Manufacturing",
        "email": "tberger@riverstonemfg.com",
        "source": "outbound_email",
        "status": "contacted",
        "urgency": "medium",
        "intent": "support",
        "pain_point": "Sales engineers lack a single source of truth for integrations",
        "summary": "RevOps manager asked about HubSpot + Gmail integration capabilities.",
        "recommended_next_action": "Share integration guide excerpt from the knowledge base.",
    },
    {
        "name": "Amira Hassan",
        "company": "Cedar Learning Group",
        "email": "amira@cedarlearning.edu",
        "source": "partner",
        "status": "won",
        "urgency": "low",
        "intent": "purchase",
        "pain_point": "Fragmented internal documentation across teams",
        "summary": "Closed on Team plan after successful pilot with 19-doc knowledge base.",
        "recommended_next_action": "Kick off onboarding and index remaining SOP library.",
    },
    {
        "name": "Daniel Cho",
        "company": "PixelForge Studio",
        "email": "daniel@pixelforge.studio",
        "source": "website",
        "status": "lost",
        "urgency": "low",
        "intent": "demo",
        "pain_point": "Budget constraints for Q2",
        "summary": "Creative agency liked the workspace but postponed until next quarter.",
        "recommended_next_action": "Add to nurture sequence with case study follow-up.",
    },
    {
        "name": "Olivia Grant",
        "company": "FinPulse Advisors",
        "email": "olivia.grant@finpulse.io",
        "source": "demo_request",
        "status": "new",
        "urgency": "high",
        "intent": "demo",
        "pain_point": "Analysts spend hours drafting client update emails",
        "summary": "COO interested in email drafting with mandatory human approval.",
        "recommended_next_action": "Demo Email Assistant flow in AI Workspace.",
    },
    {
        "name": "Ryan O'Connor",
        "company": "BluePeak Logistics",
        "email": "ryan.oconnor@bluepeaklogistics.com",
        "source": "referral",
        "status": "proposal",
        "urgency": "medium",
        "intent": "purchase",
        "pain_point": "Dispatch team needs faster access to escalation policy",
        "summary": "Director of Operations evaluating RAG for SOP lookup during incidents.",
        "recommended_next_action": "Run golden query on escalation policy during live demo.",
    },
    {
        "name": "Sophie Laurent",
        "company": "Maison Belle Retail",
        "email": "sophie.laurent@maisonbelle.fr",
        "source": "linkedin",
        "status": "contacted",
        "urgency": "medium",
        "intent": "partnership",
        "pain_point": "French customer inquiries against English KB articles",
        "summary": "E-commerce lead testing multilingual RAG with citation fidelity.",
        "recommended_next_action": "Show French workspace query with English document citations.",
    },
    {
        "name": "Kevin Park",
        "company": "NovaStack DevTools",
        "email": "kevin.park@novastack.dev",
        "source": "website",
        "status": "qualified",
        "urgency": "high",
        "intent": "purchase",
        "pain_point": "Engineering wants usage visibility and cost controls",
        "summary": "CTO reviewing Usage & Admin dashboards and quota enforcement.",
        "recommended_next_action": "Review usage events and invoice preview together.",
    },
]

SEEDED_APPROVAL_REASON = "Seeded demo approval for reviewer walkthrough"

# Curated NovaEdge-style approvals (deterministic, recruiter-friendly copy).
CURATED_DEMO_APPROVALS: list[dict] = [
    {
        "action_type": "send_email",
        "title": "Send follow-up email to Brightline Analytics",
        "description": (
            "Draft a renewal follow-up to Sarah Chen summarizing NovaEdge Growth plan "
            "pricing and next discovery-call options."
        ),
        "status": "pending",
        "risk_level": "high",
        "payload": {
            "to": "sarah.chen@brightline.io",
            "subject": "NovaEdge Growth plan — next steps for Brightline",
            "body_preview": (
                "Hi Sarah — following up on your demo request with Growth plan pricing "
                "and two proposed discovery slots next week."
            ),
        },
    },
    {
        "action_type": "schedule_meeting",
        "title": "Schedule discovery call with Northwind Legal",
        "description": (
            "Propose a 30-minute discovery call with Marcus Webb to review approval gates "
            "and grounded playbook answers."
        ),
        "status": "pending",
        "risk_level": "medium",
        "payload": {
            "attendee": "marcus.webb@northwindlegal.com",
            "duration_minutes": 30,
            "purpose": "Discovery call — approvals + knowledge base walkthrough",
        },
    },
    {
        "action_type": "send_email",
        "title": "Send proposal email to Atlas Health Clinics",
        "description": (
            "Share Business plan proposal emphasizing human approval before CRM/email actions "
            "for compliance review."
        ),
        "status": "approved",
        "risk_level": "high",
        "payload": {
            "to": "priya.nair@atlashealth.org",
            "subject": "NovaEdge Business plan proposal — audit-ready HITL",
            "body_preview": (
                "Priya — attached is the Business plan proposal with approval gates and "
                "audit logging called out for your compliance review."
            ),
        },
    },
    {
        "action_type": "update_crm",
        "title": "Update CRM stage for Helio Commerce",
        "description": "Move Elena Rossi to Contacted after multilingual workspace demo.",
        "status": "approved",
        "risk_level": "medium",
        "payload": {
            "lead": "Elena Rossi",
            "company": "Helio Commerce",
            "new_status": "contacted",
        },
    },
    {
        "action_type": "schedule_meeting",
        "title": "Book onboarding kickoff with Cedar Learning",
        "description": "Schedule onboarding kickoff after Team plan close.",
        "status": "approved",
        "risk_level": "medium",
        "payload": {
            "attendee": "amira@cedarlearning.edu",
            "duration_minutes": 45,
            "purpose": "Onboarding kickoff",
        },
    },
    {
        "action_type": "send_email",
        "title": "Nurture follow-up to PixelForge Studio",
        "description": "Send case-study nurture email after Q2 budget postpone.",
        "status": "rejected",
        "risk_level": "high",
        "payload": {
            "to": "daniel@pixelforge.studio",
            "subject": "Case study: AI ops for creative studios",
            "body_preview": "Daniel — sharing a short case study for when budget reopens.",
        },
    },
    {
        "action_type": "external_action",
        "title": "Share escalation policy excerpt with BluePeak",
        "description": (
            "Share a grounded escalation-policy excerpt from the knowledge base with "
            "Ryan O'Connor before the logistics incident review."
        ),
        "status": "needs_more_info",
        "risk_level": "medium",
        "payload": {
            "recipient": "ryan.oconnor@bluepeaklogistics.com",
            "document": "escalation_policy.md",
            "note": "Confirm which sections may leave the workspace",
        },
    },
    {
        "action_type": "send_email",
        "title": "Usage & quota walkthrough invite for NovaStack",
        "description": (
            "Invite Kevin Park to a walkthrough of Usage & Admin dashboards and quota "
            "enforcement."
        ),
        "status": "needs_more_info",
        "risk_level": "high",
        "payload": {
            "to": "kevin.park@novastack.dev",
            "subject": "NovaEdge usage visibility walkthrough",
            "body_preview": "Kevin — proposing two slots to review usage events and quotas.",
        },
    },
]


def ensure_demo_principal(session: Session, *, settings: Settings) -> Principal:
    """Upsert the demo org and user with deterministic IDs from settings.

    Idempotent: safe to call on every seed run.  Returns a Principal that
    matches DEV_ORG_ID / DEV_USER_ID so the dev-auth bypass and JWT tokens
    both resolve to the same tenant.
    """
    org_id = settings.DEV_ORG_ID
    user_id = settings.DEV_USER_ID

    org_repo = OrganizationRepository(session)
    if not org_repo.get(org_id):
        org_repo.create(
            Organization(id=org_id, name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG)
        )

    user_repo = UserRepository(session)
    if not user_repo.get(user_id):
        user_repo.create(
            User(
                id=user_id,
                email=DEMO_EMAIL,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=DEMO_FULL_NAME,
            )
        )

    member_repo = OrganizationMemberRepository(session)
    if not member_repo.get_membership(org_id, user_id):
        member_repo.create(
            OrganizationMember(
                id=new_id("mem"),
                organization_id=org_id,
                user_id=user_id,
                role=Role.OWNER,
            )
        )

    sub_repo = SubscriptionRepository(session)
    if not sub_repo.get_active(org_id):
        sub_repo.create(
            Subscription(
                id=new_id("sub"),
                organization_id=org_id,
                plan_code=PlanCode.BUSINESS,
                status="active",
            )
        )

    session.commit()

    logger.info(
        "demo_principal_ensured",
        org_id=org_id,
        user_id=user_id,
    )
    return Principal(
        user_id=user_id,
        organization_id=org_id,
        role=Role.OWNER,
        plan_code=PlanCode.BUSINESS,
    )


@dataclass(slots=True)
class SeedResult:
    documents_created: int
    documents_skipped: int
    total_documents: int
    total_chunks: int
    vector_upsert_count: int


@dataclass(slots=True)
class OperationalSeedResult:
    leads_created: int
    approvals_created: int
    usage_events_created: int
    audit_logs_created: int
    skipped: bool


def _insert_curated_approvals(
    approval_repo: ApprovalRequestRepository,
    *,
    principal: Principal,
) -> int:
    """Insert the curated NovaEdge approval set. Returns created count."""
    created = 0
    for item in CURATED_DEMO_APPROVALS:
        status = item["status"]
        approval_repo.create(
            ApprovalRequest(
                id=new_id("apv"),
                organization_id=principal.organization_id,
                action_type=item["action_type"],
                title=item["title"][:255],
                description=item["description"],
                proposed_payload={
                    "demo": True,
                    "curated": True,
                    **item["payload"],
                },
                risk_level=item["risk_level"],
                status=status,
                reason=SEEDED_APPROVAL_REASON,
                created_by=principal.user_id,
                reviewed_by=principal.user_id if status != "pending" else None,
            )
        )
        created += 1
    return created


def ensure_curated_demo_approvals(
    session: Session,
    *,
    principal: Principal,
) -> int:
    """Replace seeded demo approvals with curated recruiter-friendly copy.

    Safe for the shared public-demo org: only rows tagged with
    ``SEEDED_APPROVAL_REASON`` are removed. Agent-created approvals are kept.
    Returns the number of curated approvals inserted.
    """
    approval_repo = ApprovalRequestRepository(session)
    existing = approval_repo.list_for_org(principal.organization_id, limit=200)
    removed = 0
    for row in existing:
        if row.reason == SEEDED_APPROVAL_REASON:
            approval_repo.delete(row)
            removed += 1
    created = _insert_curated_approvals(approval_repo, principal=principal)
    logger.info(
        "curated_demo_approvals_refreshed",
        organization_id=principal.organization_id,
        removed=removed,
        created=created,
    )
    return created


def seed_operational_data(
    session: Session,
    *,
    principal: Principal,
    seed: int = 42,
) -> OperationalSeedResult:
    """Seed realistic leads, approvals, usage events, and audit logs (idempotent)."""
    lead_repo = LeadRepository(session)
    approval_repo = ApprovalRequestRepository(session)
    usage_repo = UsageEventRepository(session)
    audit_repo = AuditLogRepository(session)

    if lead_repo.count_for_org(principal.organization_id) > 0:
        logger.info(
            "operational_seed_skipped",
            organization_id=principal.organization_id,
            reason="leads already present",
        )
        return OperationalSeedResult(
            leads_created=0,
            approvals_created=0,
            usage_events_created=0,
            audit_logs_created=0,
            skipped=True,
        )

    leads_created = 0
    for row in CURATED_DEMO_LEADS:
        lead_repo.create(
            Lead(
                id=new_id("led"),
                organization_id=principal.organization_id,
                name=row["name"],
                company=row["company"],
                email=row["email"],
                status=row["status"],
                source=row["source"],
                urgency=row["urgency"],
                intent=row["intent"],
                pain_point=row["pain_point"],
                summary=row["summary"],
                recommended_next_action=row["recommended_next_action"],
                created_by=principal.user_id,
            )
        )
        leads_created += 1

    approvals_created = _insert_curated_approvals(
        approval_repo,
        principal=principal,
    )

    usage_created = 0
    for item in generate_usage_events(
        40,
        seed=seed,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
    ):
        usage_repo.create(
            UsageEvent(
                id=new_id("use"),
                organization_id=principal.organization_id,
                user_id=item["user_id"],
                feature=item["feature"],
                model=item["model"],
                provider="openai" if not item["fallback_used"] else "fallback",
                input_tokens=item["input_tokens"],
                output_tokens=item["output_tokens"],
                estimated_cost=item["estimated_cost"],
                fallback_used=item["fallback_used"],
                tool_calls=item["tool_calls"],
                latency_ms=item["latency_ms"],
                event_metadata={"demo_seed": True},
                created_at=item["created_at"],
            )
        )
        usage_created += 1

    audit_created = 0
    for item in generate_audit_logs(
        25,
        seed=seed,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
    ):
        audit_repo.create(
            AuditLog(
                id=new_id("aud"),
                organization_id=principal.organization_id,
                user_id=item["user_id"],
                action=item["action"],
                resource_type=item["resource_type"],
                resource_id=item["resource_id"],
                detail=item["detail"],
                ip_address=item["ip_address"],
                created_at=item["created_at"],
            )
        )
        audit_created += 1

    session.commit()
    logger.info(
        "operational_seed_complete",
        organization_id=principal.organization_id,
        leads_created=leads_created,
        approvals_created=approvals_created,
        usage_events_created=usage_created,
        audit_logs_created=audit_created,
    )
    return OperationalSeedResult(
        leads_created=leads_created,
        approvals_created=approvals_created,
        usage_events_created=usage_created,
        audit_logs_created=audit_created,
        skipped=False,
    )


def seed_knowledge_base(
    session: Session,
    *,
    principal: Principal,
    settings: Settings,
    embeddings: EmbeddingsProvider | None = None,
    vector: VectorProvider | None = None,
    docs_dir: Path | None = None,
) -> SeedResult:
    """Ingest all NovaEdge markdown docs into the principal's organization.
    
    If documents already exist but vectors are missing (e.g., after switching
    embedding providers), this will automatically reindex all documents.
    """
    directory = docs_dir or NOVAEDGE_DOCS_DIR
    if not directory.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {directory}")

    embeddings = embeddings or get_embeddings_provider(settings)
    vector = vector or get_vector_provider(settings)
    
    # Log provider configuration for debugging
    from onepilot.providers.embeddings.openai_embeddings import OpenAIEmbeddingsProvider
    from onepilot.providers.embeddings.fallback_embeddings import FallbackEmbeddingsProvider
    from onepilot.providers.llm.openai_provider import OpenAILLMProvider
    from onepilot.providers.llm.fallback_provider import FallbackLLMProvider
    
    embeddings_provider_name = "openai" if isinstance(embeddings, OpenAIEmbeddingsProvider) else "fallback"
    embeddings_model = getattr(embeddings, "model", getattr(embeddings, "_default_model", "unknown"))
    
    logger.info(
        "seed_start",
        organization_id=principal.organization_id,
        embedding_provider=embeddings_provider_name,
        embedding_model=embeddings_model,
        embedding_dimension=embeddings.dimension,
        qdrant_collection=document_service.collection_name(principal.organization_id),
    )

    existing = {
        doc.filename
        for doc in DocumentRepository(session).list_for_org(
            principal.organization_id, offset=0, limit=500
        )
    }
    
    # Check if we need to reindex (documents exist but vectors are missing)
    doc_repo = DocumentRepository(session)
    chunk_repo = DocumentChunkRepository(session)
    existing_doc_count = doc_repo.count_for_org(principal.organization_id)
    needs_reindex = False
    
    if existing_doc_count > 0 and len(existing) > 0:
        # Count existing chunks
        total_chunk_count = sum(
            len(list(chunk_repo.list_by_document(doc.id, organization_id=principal.organization_id)))
            for doc in doc_repo.list_for_org(principal.organization_id, offset=0, limit=500)
        )
        
        # Ensure the collection exists before testing search
        collection = document_service.collection_name(principal.organization_id)
        vector.ensure_collection(collection, embeddings.dimension)
        
        logger.info(
            "seed_reindex_check",
            organization_id=principal.organization_id,
            embedding_provider=embeddings_provider_name,
            embedding_dimension=embeddings.dimension,
            vector_provider=type(vector).__name__,
            document_count=existing_doc_count,
            chunk_count=total_chunk_count,
        )
        
        # Test if vector search returns results
        try:
            from onepilot.services import rag_service
            test_outcome = rag_service.search(
                session,
                principal=principal,
                query="test query",
                top_k=1,
                settings=settings,
                embeddings=embeddings,
                vector=vector,
                enforce_quota=False,
            )
            test_search_result_count = len(test_outcome.hits)
            
            logger.info(
                "seed_reindex_test_search",
                organization_id=principal.organization_id,
                search_result_count=test_search_result_count,
                document_count=existing_doc_count,
                chunk_count=total_chunk_count,
            )
            
            if test_search_result_count == 0:
                logger.warning(
                    "seed_reindex_required",
                    reason="Documents exist in Postgres but vector search returns 0 results",
                    organization_id=principal.organization_id,
                    document_count=existing_doc_count,
                    chunk_count=total_chunk_count,
                    embedding_dimension=embeddings.dimension,
                )
                needs_reindex = True
        except Exception:
            logger.exception("seed_reindex_check_failed")
            needs_reindex = True
    
    # Reindex if needed (e.g., after provider change)
    reindex_upserts = 0
    if needs_reindex:
        logger.info(
            "seed_reindexing",
            organization_id=principal.organization_id,
            document_count=existing_doc_count,
        )
        reindex_upserts = document_service.reindex_organization_documents(
            session,
            principal=principal,
            settings=settings,
            embeddings=embeddings,
            vector=vector,
        )
        logger.info(
            "seed_reindex_complete",
            organization_id=principal.organization_id,
            vector_upsert_count=reindex_upserts,
        )

    created = 0
    skipped = 0
    total_chunks = 0
    total_vector_upserts = reindex_upserts
    for path in sorted(directory.glob("*.md")):
        if path.name in existing:
            skipped += 1
            continue
        content = path.read_bytes()
        try:
            upload_result = document_service.upload_document(
                session,
                principal=principal,
                filename=path.name,
                content_type="text/markdown",
                content=content,
                source="demo_seed",
                settings=settings,
                embeddings=embeddings,
                vector=vector,
                enforce_quota=False,
            )
            created += 1
            total_chunks += upload_result.chunk_count
            total_vector_upserts += upload_result.vector_upsert_count
        except Exception:
            # Undo the failed document's flush so the session is clean for the
            # next document.  Previously committed documents are unaffected.
            session.rollback()
            logger.exception("demo_seed_failed", filename=path.name)

    total_documents_in_db = doc_repo.count_for_org(principal.organization_id)
    
    # Count total chunks across all documents
    all_docs = doc_repo.list_for_org(principal.organization_id, offset=0, limit=500)
    final_chunk_count = sum(
        len(list(chunk_repo.list_by_document(doc.id, organization_id=principal.organization_id)))
        for doc in all_docs
    )
    
    # Ensure the collection exists with correct dimension before verification
    collection = document_service.collection_name(principal.organization_id)
    vector.ensure_collection(collection, embeddings.dimension)
    
    logger.info(
        "seed_verification_start",
        organization_id=principal.organization_id,
        embedding_provider=embeddings_provider_name,
        embedding_dimension=embeddings.dimension,
        vector_provider=type(vector).__name__,
        document_count=total_documents_in_db,
        chunk_count=final_chunk_count,
        total_vector_upserts=total_vector_upserts,
    )
    
    # Final verification: check that search returns results
    search_result_count = 0
    try:
        from onepilot.services import rag_service
        verify_outcome = rag_service.search(
            session,
            principal=principal,
            query="services integrations support",
            top_k=5,
            settings=settings,
            embeddings=embeddings,
            vector=vector,
            enforce_quota=False,
        )
        search_result_count = len(verify_outcome.hits)
        
        logger.info(
            "seed_verification_search_complete",
            organization_id=principal.organization_id,
            search_result_count=search_result_count,
            document_count=total_documents_in_db,
            chunk_count=final_chunk_count,
        )
    except Exception:
        logger.exception(
            "seed_verification_search_failed",
            organization_id=principal.organization_id,
            document_count=total_documents_in_db,
            chunk_count=final_chunk_count,
        )
    
    logger.info(
        "demo_seed_complete",
        organization_id=principal.organization_id,
        embedding_provider=embeddings_provider_name,
        embedding_model=embeddings_model,
        embedding_dimension=embeddings.dimension,
        created=created,
        skipped=skipped,
        reindexed=needs_reindex,
        total_documents=total_documents_in_db,
        total_chunks=total_chunks,
        total_vector_upserts=total_vector_upserts,
        search_result_count=search_result_count,
    )
    
    # Fail fast if verification shows problems
    if total_documents_in_db == 0:
        raise RuntimeError("Seed verification failed: document_count is 0")
    if total_chunks == 0 and created > 0:
        raise RuntimeError("Seed verification failed: chunk_count is 0 but documents were created")
    if total_vector_upserts == 0 and (created > 0 or needs_reindex):
        raise RuntimeError("Seed verification failed: vector_upsert_count is 0 but documents were created or reindexed")
    if search_result_count == 0 and total_documents_in_db > 0:
        raise RuntimeError(
            f"Seed verification failed: knowledge search returns 0 results but {total_documents_in_db} documents exist. "
            f"This indicates a vector index mismatch. Embedding dimension: {embeddings.dimension}"
        )
    
    return SeedResult(
        documents_created=created,
        documents_skipped=skipped,
        total_documents=total_documents_in_db,
        total_chunks=total_chunks,
        vector_upsert_count=total_vector_upserts,
    )
