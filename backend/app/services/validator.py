"""Step 8: validate proposed AI findings against original text and trusted inputs.

This does not call Gemini, infer semantic truth, approve content or apply fixes.
Backend A must supply one revision and approved evidence scoped by authenticated
organisation, brand, product, market and publication date.
"""

from dataclasses import dataclass, replace
from datetime import date
import math
import re

from .context import resolve_rules
from .contracts import Finding, ReviewContext, Rule, Source


@dataclass(frozen=True)
class ReviewEvidence:
    """Trusted snapshot, mapped from existing database facts; not a new DB table."""
    id: str
    org_id: str
    brand_id: str
    version: int
    product: str
    market: str
    source: Source
    status: str = "pending"
    valid_from: date | None = None
    valid_to: date | None = None
    value_text: str = ""  # trusted approved value/claim wording supplied to analysis


@dataclass(frozen=True)
class ValidationResult:
    findings: tuple[Finding, ...]  # original deterministic findings + validated AI
    issues: tuple[str, ...]


_REQUIRED = {"category", "quoted_text", "rule_code", "fact_id", "verdict", "severity",
             "confidence", "explanation", "suggested_fix"}
_OPTIONAL = {"span_start", "span_end"}
_CATEGORIES = {"tone", "terminology", "claims", "disclaimer", "price", "battery_life", "warranty"}
_VERDICTS = {"violation", "unsupported", "outdated", "supported", "needs_review"}
_SEVERITIES = {"critical", "high", "medium", "low", "info"}


def _normalise(text):
    return " ".join(text.split())


def _locate(text, quote, start=None, end=None):
    if start is not None or end is not None:
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("invalid proposed text offsets")
        if text[start:end] == quote or _normalise(text[start:end]) == _normalise(quote):
            return start, end
        raise ValueError("proposed offsets do not match the quote")
    # Lookahead includes overlapping occurrences: 'aaa' in 'aaaa' is ambiguous.
    matches = list(re.finditer("(?=(" + re.escape(quote) + "))", text))
    if not matches:
        pattern = r"\s+".join(re.escape(part) for part in quote.split())
        matches = list(re.finditer("(?=(" + pattern + "))", text))
    if len(matches) != 1:
        raise ValueError("quote is absent or ambiguous; provide a unique quote or verified offsets")
    return matches[0].span(1)


def _overlap(a, b):
    return a.span_start < b.span_end and b.span_start < a.span_end


def _same_check(a, b):
    return (a.category, a.rule_id, a.fact_id) == (b.category, b.rule_id, b.fact_id)


def validate_ai_findings(text: str, response: dict, *, context: ReviewContext,
                         rules: list[Rule], facts: list[ReviewEvidence],
                         org_id: str, brand_id: str,
                         deterministic: tuple[Finding, ...] = ()) -> ValidationResult:
    """Never trust AI-supplied source locations, offsets or approval instructions.

    Rule allowlist comes from context resolution. Facts are re-filtered here.
    Repeated quotes need verified offsets. An unsupported citation is removed;
    no surviving citation means the finding is dropped, with an issue recorded.
    The AI's explanation and proposed replacement remain untrusted human-review
    material, even after structural validation.
    """
    if not isinstance(response, dict) or set(response) != {"findings"} or not isinstance(response["findings"], list):
        raise ValueError("Expected exactly one findings array.")
    if len(response["findings"]) > 100:
        raise ValueError("At most 100 proposed findings per validation.")
    resolution = resolve_rules(context, rules, org_id=org_id, brand_id=brand_id)
    rule_map = {}
    for item in resolution.applied:
        if item.rule.code in rule_map:
            raise ValueError("Applied rule codes must identify a single version for this review.")
        rule_map[item.rule.code] = item.rule
    fact_map = {}
    for f in facts:
        if (f.org_id != org_id or f.brand_id != brand_id or f.status != "approved"
            or not context.product.strip() or f.product.strip().casefold() != context.product.strip().casefold()
            or f.market.strip().casefold() != context.market.strip().casefold()
            or f.valid_from and context.publication_date < f.valid_from
            or f.valid_to and context.publication_date > f.valid_to):
            continue
        if f.valid_from and f.valid_to and f.valid_from > f.valid_to:
            raise ValueError("Invalid fact effective-date range.")
        if f.id in fact_map:
            raise ValueError("Fact IDs must uniquely identify supplied evidence.")
        fact_map[f.id] = f
    for f in deterministic:
        if (not isinstance(f, Finding) or f.origin != "deterministic"
            or type(f.span_start) is not int or type(f.span_end) is not int
            or not 0 <= f.span_start <= f.span_end <= len(text)
            or text[f.span_start:f.span_end] != f.quoted_text):
            raise ValueError("Deterministic findings do not belong to this text snapshot.")
    accepted, issues = [], []
    for index, item in enumerate(response["findings"]):
        try:
            if not isinstance(item, dict) or not _REQUIRED.issubset(item) or set(item) - _REQUIRED - _OPTIONAL:
                raise ValueError("missing or unexpected fields")
            if any(not isinstance(item[k], str) or not item[k].strip() or len(item[k]) > 8000
                   for k in ("category", "quoted_text", "verdict", "severity", "explanation")):
                raise ValueError("invalid required text field")
            if item["category"] not in _CATEGORIES or item["verdict"] not in _VERDICTS or item["severity"] not in _SEVERITIES:
                raise ValueError("unknown category, verdict or severity")
            confidence = item["confidence"]
            if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("confidence must be finite and between zero and one")
            for key in ("rule_code", "fact_id", "suggested_fix"):
                if item[key] is not None and (not isinstance(item[key], str) or len(item[key]) > 8000):
                    raise ValueError("invalid optional text field")
            start, end = _locate(text, item["quoted_text"], item.get("span_start"), item.get("span_end"))
            rule, fact = rule_map.get(item["rule_code"]), fact_map.get(item["fact_id"])
            if item["rule_code"] and rule is None: issues.append(f"Finding {index}: removed unknown or inapplicable rule reference.")
            if item["fact_id"] and fact is None: issues.append(f"Finding {index}: removed unknown or inapplicable fact reference.")
            if rule is None and fact is None: raise ValueError("no valid rule or fact citation survives")
            verdict, explanation, fix = item["verdict"], item["explanation"], item["suggested_fix"]
            if verdict == "supported" and fact is None:
                verdict = "needs_review"
                issues.append(f"Finding {index}: supported claim has no approved fact citation; downgraded.")
            if confidence < 0.6:
                verdict = "needs_review"
                issues.append(f"Finding {index}: low confidence; human review required.")
            if re.search(r"\b(?:false|untrue)\b", explanation, re.I):
                verdict = "needs_review"
                explanation = "The AI used an unsupported truth judgement. A human must assess this span against the cited approved knowledge."
            if verdict in ("needs_review", "supported"):
                fix = None
            severity = "info" if verdict == "supported" else item["severity"]
            if severity == "info" and verdict != "supported":
                severity = rule.severity if rule else "high"
            candidate = Finding(origin="ai", category=item["category"], severity=severity,
                confidence=float(confidence), verdict=verdict, span_start=start, span_end=end,
                quoted_text=text[start:end], explanation=explanation, suggested_fix=fix,
                fact_id=fact.id if fact else None, fact_version=fact.version if fact else None,
                source=fact.source if fact else rule.source,
                rule_id=rule.id if rule else None, rule_code=rule.code if rule else None,
                rule_version=rule.version if rule else None)
            # Same-category overlapping deterministic results are authoritative.
            # Different categories are retained: a tone issue can overlap a price.
            if any(candidate.category == d.category and _overlap(candidate, d) for d in deterministic):
                issues.append(f"Finding {index}: overlaps a deterministic check of the same category; deterministic result kept.")
                continue
            accepted.append(candidate)
        except ValueError as exc:
            issues.append(f"Finding {index}: dropped ({exc}).")
    merged = []
    for candidate in sorted(accepted, key=lambda f: (-f.confidence, f.span_start, -(f.span_end-f.span_start))):
        previous = next((p for p in merged if _same_check(p, candidate) and _overlap(p, candidate)), None)
        if previous is not None:
            if previous.verdict != candidate.verdict or previous.suggested_fix != candidate.suggested_fix:
                merged[merged.index(previous)] = replace(previous, verdict="needs_review", suggested_fix=None,
                    severity="high" if previous.severity == "info" else previous.severity,
                    explanation="Overlapping AI suggestions disagree for the same check. A human must review this span.")
            issues.append("Merged overlapping AI findings for the same category and citations.")
        else:
            merged.append(candidate)
    merged.sort(key=lambda f: (f.span_start, f.span_end, f.category, f.rule_code or "", f.fact_id or ""))
    return ValidationResult((*deterministic, *merged), tuple(issues))
