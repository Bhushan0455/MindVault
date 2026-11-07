import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, Date, DateTime, ForeignKey, Integer, Float, Numeric, LargeBinary, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class Organisation(Base):
    __tablename__ = "organisations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))

class Brand(Base):
    __tablename__ = "brands"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(120))

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    brand_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(255))
    file_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    text: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    content_hash: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Rule(Base):
    requires_claim_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    supersedes_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    __tablename__ = "rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    brand_id: Mapped[str] = mapped_column(String(36))
    code: Mapped[str] = mapped_column(String(40), index=True)
    instruction: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), default="claims")
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    scope_channel: Mapped[list] = mapped_column(JSON, default=list)
    scope_audience: Mapped[list] = mapped_column(JSON, default=list)
    scope_region: Mapped[list] = mapped_column(JSON, default=list)
    scope_content_type: Mapped[list] = mapped_column(JSON, default=list)
    scope_campaign: Mapped[list] = mapped_column(JSON, default=list)
    authority: Mapped[str] = mapped_column(String(30), default="core")
    overrideable: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    forbidden_terms: Mapped[list] = mapped_column(JSON, default=list)
    preferred_terms: Mapped[dict] = mapped_column(JSON, default=dict)
    required_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_from: Mapped[Date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="approved")
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

class Fact(Base):
    qualifier: Mapped[str] = mapped_column(String(20), default="exact")
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    supersedes_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    __tablename__ = "facts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    brand_id: Mapped[str] = mapped_column(String(36))
    product: Mapped[str] = mapped_column(String(120))
    attribute: Mapped[str] = mapped_column(String(40))
    value_text: Mapped[str] = mapped_column(String(255))
    value_num: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    market: Mapped[str] = mapped_column(String(20), default="IN")
    valid_from: Mapped[Date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="approved")
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_location: Mapped[str | None] = mapped_column(String(100), nullable=True)

class Content(Base):
    __tablename__ = "content_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    brand_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(255))
    created_by: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    current_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    latest_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

class Revision(Base):
    title: Mapped[str | None] = mapped_column(String(255),nullable=True)
    __tablename__ = "content_revisions"
    __table_args__ = (UniqueConstraint("content_id", "number", name="uq_revision_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    content_id: Mapped[str] = mapped_column(String(36), index=True)
    number: Mapped[int] = mapped_column(Integer)
    body_text: Mapped[str] = mapped_column(Text)
    body_hash: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    context: Mapped[dict] = mapped_column(JSON)

class ReviewRun(Base):
    knowledge_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_status: Mapped[str] = mapped_column(String(40), default="not_requested")
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    __tablename__ = "review_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    revision_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    progress_step: Mapped[str] = mapped_column(String(30), default="intake")
    applied_rules: Mapped[list] = mapped_column(JSON, default=list)
    skipped: Mapped[list] = mapped_column(JSON, default=list)
    ai_used: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Finding(Base):
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    review_run_id: Mapped[str] = mapped_column(String(36), index=True)
    revision_id: Mapped[str] = mapped_column(String(36), index=True)
    origin: Mapped[str] = mapped_column(String(20), default="deterministic")
    category: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=1)
    verdict: Mapped[str] = mapped_column(String(30))
    span_start: Mapped[int] = mapped_column(Integer)
    span_end: Mapped[int] = mapped_column(Integer)
    quoted_text: Mapped[str] = mapped_column(Text)
    rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    fact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    content_id: Mapped[str] = mapped_column(String(36), index=True)
    revision_id: Mapped[str] = mapped_column(String(36))
    body_hash: Mapped[str] = mapped_column(String(64))
    reviewer_id: Mapped[str] = mapped_column(String(36))
    decision: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    content_id: Mapped[str] = mapped_column(String(36), index=True)
    revision_id: Mapped[str] = mapped_column(String(36))
    finding_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_id: Mapped[str] = mapped_column(String(36))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KnowledgeCandidate(Base):
    __tablename__ = "knowledge_candidates"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    brand_id: Mapped[str] = mapped_column(String(36))
    document_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(20))
    data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    knowledge_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ProductCatalog(Base):
    __tablename__ = 'product_catalog'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    org_id: Mapped[str] = mapped_column(String(36),index=True)
    brand_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(120))
    aliases: Mapped[list] = mapped_column(JSON,default=list)


class ServiceJob(Base):
    __tablename__ = "service_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    brand_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="done")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
