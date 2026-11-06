"""Small service contracts for Role B's first integration milestone.

Backend A maps database records into these types. IDs remain strings here so
the checker does not need SQLAlchemy, FastAPI or a running database.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Source:
    document_id: str
    document_title: str
    location: str  # e.g. "page 2" or "paragraph 7"; never invent DOCX pages
    excerpt: str


@dataclass(frozen=True)
class PriceFact:
    id: str
    version: int
    product: str
    market: str
    amount: Decimal
    currency: str
    status: Literal["approved", "pending", "rejected", "expired", "superseded"]
    valid_from: date
    source: Source
    valid_to: date | None = None  # inclusive


@dataclass(frozen=True)
class ReviewContext:
    product: str  # explicitly selected product, not inferred by this milestone
    market: str
    publication_date: date
    channel: str | None = None
    audience: str | None = None
    content_type: str | None = None
    campaign: str | None = None

    # market is also the rule-scope region (e.g. IN); Backend A maps region here.


@dataclass(frozen=True)
class RuleScope:
    channel: tuple[str, ...] = ()
    audience: tuple[str, ...] = ()
    region: tuple[str, ...] = ()
    content_type: tuple[str, ...] = ()
    campaign: tuple[str, ...] = ()


@dataclass(frozen=True)
class Rule:
    id: str
    org_id: str
    brand_id: str
    code: str
    version: int
    instruction: str
    source: Source
    status: Literal["extracted", "pending", "approved", "rejected", "superseded"] = "pending"
    authority: Literal["non_overridable", "core", "scoped", "exception"] = "core"
    priority: int = 0  # higher numbers sort first within authority/specificity
    scope: RuleScope = RuleScope()
    effective_from: date | None = None
    effective_to: date | None = None  # inclusive
    category: str = "general"
    severity: Literal["critical", "high", "medium", "low"] = "high"
    forbidden_terms: tuple[str, ...] = ()
    preferred_terms: tuple[tuple[str, str], ...] = ()  # (forbidden, preferred)
    required_text: str | None = None
    requires_claim_evidence: bool = False


@dataclass(frozen=True)
class ClaimEvidence:
    id: str
    org_id: str
    brand_id: str
    version: int
    product: str
    market: str
    claim_text: str  # exact approved sentence, not generic product evidence
    source: Source
    status: Literal["pending", "approved", "rejected", "expired", "superseded"] = "pending"
    valid_from: date | None = None
    valid_to: date | None = None  # inclusive


@dataclass(frozen=True)
class AppliedRule:
    rule: Rule
    why: str


@dataclass(frozen=True)
class SkippedRule:
    rule: Rule
    reason: str


@dataclass(frozen=True)
class RuleResolution:
    applied: tuple[AppliedRule, ...]
    skipped: tuple[SkippedRule, ...]


@dataclass(frozen=True)
class Finding:
    origin: str
    category: str
    severity: str
    confidence: float
    verdict: str
    span_start: int
    span_end: int
    quoted_text: str
    explanation: str
    suggested_fix: str | None
    fact_id: str | None
    fact_version: int | None
    source: Source | None
    rule_id: str | None = None
    rule_code: str | None = None
    rule_version: int | None = None
    product_id: str | None = None
    attribute: str | None = None
    attribution_reason: str | None = None

    # Offsets use Python Unicode code points, start inclusive, end exclusive.
    # Backend A adds finding ID, revision ID, run ID and decision status.


@dataclass(frozen=True)
class RuleCheckResult:
    resolution: RuleResolution
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class Product:
    id: str
    org_id: str
    brand_id: str
    name: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class NumericFact:
    id: str
    org_id: str
    brand_id: str
    version: int
    product_id: str
    attribute: Literal["price", "battery_life", "warranty"]
    value: Decimal
    unit: Literal["INR", "hours", "years", "months"]
    source: Source
    market: str
    status: Literal["pending", "approved", "rejected", "expired", "superseded"] = "pending"
    qualifier: Literal["exact", "up_to"] = "exact"
    valid_from: date | None = None
    valid_to: date | None = None
