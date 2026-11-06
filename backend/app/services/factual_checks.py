"""Step 4: scoped numeric facts and conservative local product attribution.

Use this instead of check_prices when combining a review: it includes prices.
Both APIs remain available so earlier examples keep working.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from .numbers import NUMBER_PATTERN, is_partial_number, iter_prices, parse_number
from .contracts import Finding, NumericFact, Product, ReviewContext


@dataclass(frozen=True)
class _Mention:
    start: int
    end: int
    value: Decimal
    unit: str
    attribute: str
    qualifier: str = "exact"
    subject_ambiguous: bool = False


_DURATION = re.compile(
    r"(?<![\w.,+\-])(?P<qualifier>up\s+to\s+)?(?P<number>"+NUMBER_PATTERN+r")"
    r"\s*[-–]?\s*(?P<unit>hours?|hrs?|years?|months?)\b", re.IGNORECASE)
_BOUNDARY = re.compile(r"(?<!\d)\.|\.(?!\d)|[!?;\n]")


def _sentences(text):
    start = 0
    for match in _BOUNDARY.finditer(text):
        yield start, match.start()
        start = match.end()
    yield start, len(text)


def _product_mentions(text, products):
    candidates = []
    for product in products:
        for name in (product.name, *product.aliases):
            if name.strip():
                pattern = r"(?<!\w)" + r"\s+".join(re.escape(p) for p in name.split()) + r"(?!\w)"
                candidates.extend((m.start(), m.end(), product.id) for m in re.finditer(pattern, text, re.I))
    # A shorter alias inside a longer canonical name should not introduce a
    # second product. Equal spans shared by two products remain ambiguous.
    return [m for m in candidates if not any(n[0] <= m[0] and n[1] >= m[1]
            and n[1] - n[0] > m[1] - m[0] for n in candidates)]


def _number(value):
    return format(value.normalize(), "f")


def _product_clause(text, mention, start, end, names, numeric_mentions):
    """Split only explicit product+number clauses on both sides of a connector.

    'A and B at one price' is a grouped subject, not independent clauses.
    Numeric comma grouping, bare nearest-name guesses and pronouns are excluded.
    """
    local=sorted(set((x,y,p) for x,y,p in names if start<=x and y<=end))
    segments=[]
    left=start
    for separator in re.finditer(r"\b(?:and|while|whereas|but)\b\s+|,(?!\d)\s*",text[start:end],re.I):
        sep_start,sep_end=start+separator.start(),start+separator.end()
        right_names=[n for n in local if n[0]>=sep_end
                     and re.fullmatch(r"\s*(?:(?:our|the)\s+)?",text[sep_end:n[0]],re.I)]
        if not right_names:continue
        first=min(n[0] for n in right_names)
        first_names=[n for n in right_names if n[0]==first]
        if len({n[2] for n in first_names})!=1:continue
        name_end=max(n[1] for n in first_names)
        next_name=min((n[0] for n in local if n[0]>=name_end and n[2]!=first_names[0][2]),default=end)
        before_names=[n for n in local if left<=n[0] and n[1]<=sep_start]
        if len({n[2] for n in before_names})!=1:continue
        prior_end=max(n[1] for n in before_names)
        has_left_number=any(prior_end<=m.start and m.end<=sep_start for m in numeric_mentions)
        has_right_number=any(name_end<=m.start and m.end<=next_name for m in numeric_mentions)
        if has_left_number and has_right_number:
            segments.append((left,sep_start));left=sep_end
    segments.append((left,end))
    return next(((a,b) for a,b in segments if a<=mention.start and mention.end<=b),(start,end))


def _duration_subject(text,start,end,attribute):
    """Recognise direct shipping/dispatch attachments, not general grammar."""
    before=text[:start][-100:]
    after=text[end:][:70]
    transport=r"(?:ships?|shipping|delivery|delivered|dispatch(?:es|ed)?)"
    transport_before=bool(re.search(r"\b"+transport+r"\s+(?:(?:in|within|takes?|requires?|is|for)\s*)*$",before,re.I))
    transport_after=bool(re.match(r"\s*(?:of\s+|for\s+)?"+transport+r"\b",after,re.I))
    subject=r"battery(?:\s+life)?" if attribute=="battery_life" else r"warranty"
    primary_before=bool(re.search(r"\b"+subject+r"\s*(?:(?:lasts?|is|of|for|provides?|covers?|life)\s*)*$",before,re.I))
    primary_after=bool(re.match(r"\s*(?:of\s+)?"+subject+r"\b",after,re.I))
    if transport_before or transport_after:
        return "ambiguous" if primary_before or primary_after else "shipping"
    return "primary"


def _base_value(attribute, value, unit):
    if attribute == "warranty" and unit == "years":
        return value * 12
    return value


def _validate_fact(fact):
    expected = {"price": ("INR",), "battery_life": ("hours",), "warranty": ("years", "months")}
    if fact.attribute not in expected or fact.unit not in expected[fact.attribute]:
        raise ValueError(f"Invalid attribute/unit for numeric fact {fact.id}.")
    if not fact.value.is_finite() or fact.value < 0:
        raise ValueError(f"Invalid numeric value for fact {fact.id}.")
    if fact.qualifier not in ("exact", "up_to") or (fact.attribute == "price" and fact.qualifier != "exact"):
        raise ValueError(f"Invalid qualifier for fact {fact.id}.")
    if fact.valid_from and fact.valid_to and fact.valid_from > fact.valid_to:
        raise ValueError(f"Reversed dates for fact {fact.id}.")


def check_facts(text: str, context: ReviewContext, products: list[Product], facts: list[NumericFact],
                *, org_id: str, brand_id: str) -> list[Finding]:
    """Check explicit price/battery/warranty mentions against supplied knowledge.

    Backend A must authenticate, scope queries and supply a complete product
    catalogue for the brand. This guard removes foreign rows but is not auth.
    No cross-sentence pronoun resolution, discount/bundle reasoning or free-form
    claims are implemented. Empty results do not imply full content approval.
    """
    if not org_id.strip() or not brand_id.strip():
        raise ValueError("Authenticated organisation and selected brand are required.")
    products = [p for p in products if p.org_id == org_id and p.brand_id == brand_id]
    product_ids = {p.id for p in products}
    facts = [f for f in facts if f.org_id == org_id and f.brand_id == brand_id and f.product_id in product_ids
             and f.market.casefold() == context.market.casefold()]
    for f in facts:
        if f.status == "approved":
            _validate_fact(f)
    names = _product_mentions(text, products)
    all_named = {p for _, _, p in names}
    selected = {p.id for p in products if context.product.strip() and any(
        context.product.strip().casefold() == name.strip().casefold() for name in (p.name, *p.aliases))}
    sentences = list(_sentences(text))
    mentions = [_Mention(m.start, m.end, m.value, "INR", "price") for m in iter_prices(text)]
    for match in _DURATION.finditer(text):
        if is_partial_number(text,match.start()):
            continue
        a, b = next((a, b) for a, b in sentences if a <= match.start() <= b)
        unit = match.group("unit").casefold()
        attribute, canonical, marker = (("battery_life", "hours", r"\bbattery\b")
            if unit.startswith(("hour", "hr")) else ("warranty", "years" if unit.startswith("year") else "months", r"\bwarranty\b"))
        # Require a nearby subject in this sentence; shipping durations are not
        # automatically treated as battery/warranty statements.
        subjects = list(re.finditer(marker, text[a:b], re.I))
        if not any(min(abs(a+s.end()-match.start()), abs(a+s.start()-match.end())) <= 50 for s in subjects):
            continue
        subject_role=_duration_subject(text[a:b],match.start()-a,match.end()-a,attribute)
        if subject_role=="shipping":continue
        mentions.append(_Mention(match.start(), match.end(), parse_number(match.group("number")),
                                  canonical, attribute, "up_to" if match.group("qualifier") else "exact",
                                  subject_role=="ambiguous"))
    findings = []
    day = context.publication_date
    for m in sorted(mentions, key=lambda m: m.start):
        a, b = next((a, b) for a, b in sentences if a <= m.start <= b)
        original_bounds=(a,b)
        a,b=_product_clause(text,m,a,b,names,mentions)
        local = [(x, y, p) for x, y, p in names if a <= x and y <= b]
        local_ids = {p for _, _, p in local}
        nearby_ids = {p for x, y, p in local if min(abs(y-m.start), abs(x-m.end)) <= 80}
        product_id = None
        if len(local_ids) > 1:
            attribution = "Multiple products occur in this sentence; attribution needs human review."
        elif len(nearby_ids) == 1:
            product_id = next(iter(nearby_ids))
            attribution = ("Explicit independent product-and-number clause; " if (a,b)!=original_bounds else "") + "one product name/alias is within 80 characters in this clause."
        elif local_ids:
            attribution = "The product name is too far from this number (over 80 characters)."
        elif len(selected) == 1 and (not all_named or all_named == selected):
            product_id = next(iter(selected))
            attribution = "Uses the selected product; no conflicting explicit product occurs in the draft."
        elif not context.product.strip() and not all_named:
            choices = {f.product_id for f in facts if f.attribute == m.attribute and f.status == "approved"
                and (f.valid_from is None or f.valid_from <= day) and (f.valid_to is None or day <= f.valid_to)}
            if len(choices) == 1:
                product_id = next(iter(choices))
                attribution = "Only one product has an approved effective fact for this attribute and market."
            else:
                attribution = "No unambiguous product can be identified."
        else:
            attribution = "No local product name and selected-product fallback is ambiguous."
        def finding(verdict, explanation, fact=None, fix=None):
            return Finding(origin="deterministic", category=m.attribute,
                severity="info" if verdict == "supported" else "critical" if m.attribute == "price" and verdict in ("violation", "outdated") else "high",
                confidence=1.0, verdict=verdict, span_start=m.start, span_end=m.end, quoted_text=text[m.start:m.end],
                explanation=explanation, suggested_fix=fix, fact_id=fact.id if fact else None,
                fact_version=fact.version if fact else None, source=fact.source if fact else None,
                product_id=product_id, attribute=m.attribute, attribution_reason=attribution)
        if product_id is None:
            findings.append(finding("needs_review", attribution)); continue
        if m.subject_ambiguous:
            findings.append(finding("needs_review","This duration is directly attached to both a specification and shipping wording. A human must identify its subject."));continue
        relevant = [f for f in facts if f.product_id == product_id and f.attribute == m.attribute]
        active = [f for f in relevant if f.status == "approved"
                  and (f.valid_from is None or f.valid_from <= day) and (f.valid_to is None or day <= f.valid_to)]
        if len(active) != 1:
            findings.append(finding("needs_review", "Missing or conflicting approved facts for this product, attribute, market and date.")); continue
        fact = active[0]
        actual = _base_value(m.attribute, m.value, m.unit)
        approved = _base_value(fact.attribute, fact.value, fact.unit)
        display_unit = fact.unit[:-1] if fact.value == 1 and fact.unit in ("hours", "years", "months") else fact.unit
        description = ("up to " if fact.qualifier == "up_to" else "") + (
            "₹" + _number(fact.value) if m.attribute == "price" else _number(fact.value) + " " + display_unit)
        source = f"{fact.source.document_title}, {fact.source.location}"
        if actual == approved and m.qualifier == fact.qualifier:
            findings.append(finding("supported", f"Matches the approved {description} ({source}).", fact)); continue
        if fact.qualifier == "up_to" and actual <= approved:
            findings.append(finding("needs_review", f"Approved evidence says {description} ({source}). The draft changes the qualifier or maximum; this does not establish the draft's exact claim.", fact)); continue
        if actual == approved:
            findings.append(finding("needs_review", f"Value matches, but the qualifier differs from approved {description} ({source}).", fact)); continue
        historical = any(f.status in ("approved", "expired", "superseded") and f.valid_to and f.valid_to < day
                         and _base_value(f.attribute, f.value, f.unit) == actual and f.qualifier == m.qualifier for f in relevant)
        findings.append(finding("outdated" if historical else "violation",
            f"Draft value differs from approved {description} ({source})." + (" The draft matches a historical fact." if historical else ""),
            fact, description))
    return findings
