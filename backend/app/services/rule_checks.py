"""Step 3: selected-rule terminology, disclaimer and claim checks, without AI."""

import re

from .context import resolve_rules
from .contracts import ClaimEvidence, Finding, ReviewContext, Rule, RuleCheckResult
from .numbers import iter_prices

# A lexicon is a screening tool, not a semantic judgement. The exclusions below
# handle narrow literal contexts only; complex negation/paraphrases still need review.
_SUPERLATIVES = (
    "number one", "better than", "guaranteed", "unbeatable", "cheapest",
    "fastest", "leading", "best", "only", "100%", "#1",
)
_CLAIM_PATTERN = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(term).replace(r"\ ", r"\s+") for term in _SUPERLATIVES)
    + r")(?!\w)", re.IGNORECASE,
)


def _phrase(term: str):
    """Case-insensitive whole-phrase matching; whitespace may vary."""
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(part) for part in term.split())
                      + r"(?!\w)", re.IGNORECASE)


def _finding(rule: Rule, *, category: str, start: int, end: int, text: str,
             explanation: str, fix: str | None = None, verdict: str = "violation",
             confidence: float = 1.0, evidence: ClaimEvidence | None = None) -> Finding:
    return Finding(
        origin="deterministic", category=category,
        severity="info" if verdict == "supported" else rule.severity,
        confidence=confidence, verdict=verdict, span_start=start, span_end=end,
        quoted_text=text[start:end], explanation=explanation, suggested_fix=fix,
        fact_id=evidence.id if evidence else None,
        fact_version=evidence.version if evidence else None,
        source=evidence.source if evidence else rule.source,
        rule_id=rule.id, rule_code=rule.code, rule_version=rule.version,
    )


def _terminology(text: str, rule: Rule) -> list[Finding]:
    replacements = {term.strip().casefold(): replacement for term, replacement in rule.preferred_terms
                    if term.strip()}
    # Preferred mappings are also enforceable; no duplicate entry is needed in forbidden_terms.
    terms = {term.strip().casefold(): term.strip() for term in
             (*rule.forbidden_terms, *(pair[0] for pair in rule.preferred_terms)) if term.strip()}
    candidates = []
    for key, term in terms.items():
        for match in _phrase(term).finditer(text):
            if _policy_term_mention(text, match.start(), match.end()):
                continue
            candidates.append((match.start(), match.end(), key))
    # Prefer a longer forbidden phrase over a shorter overlapping term in this rule.
    candidates.sort(key=lambda item: (-(item[1] - item[0]), item[0], item[2]))
    selected = []
    for start, end, key in candidates:
        if any(start < b and end > a for a, b, _ in selected):
            continue
        selected.append((start, end, key))
    return [_finding(rule, category="terminology", start=a, end=b, text=text,
            explanation=f"'{text[a:b]}' is disallowed by {rule.code}: {rule.instruction}",
            fix=replacements.get(key)) for a, b, key in sorted(selected)]


def _disclaimer(text: str, rule: Rule) -> list[Finding]:
    required = rule.required_text
    if not required or not required.strip() or _phrase(required).search(text):
        return []
    # Zero-length span: the fix is an INSERTION, not a replacement of the draft.
    prefix = "\n" if text and not text[-1].isspace() else ""
    return [_finding(rule, category="disclaimer", start=len(text), end=len(text), text=text,
            explanation=f"Required text '{required}' is missing ({rule.code}).",
            fix=prefix + required.strip())]


def _sentence(text: str, start: int, end: int) -> str:
    # Conservative sentence boundaries; decimal points between digits stay inside.
    boundaries = list(re.finditer(r"(?<!\d)\.|\.(?!\d)|[!?\n]", text))
    left = max((m.end() for m in boundaries if m.end() <= start), default=0)
    right = min((m.start() for m in boundaries if m.start() >= end), default=len(text))
    return text[left:right].strip()


def _normalise_claim(text: str) -> str:
    return " ".join(text.strip().rstrip(".!?").split()).casefold()


def _local_context(text, start, end):
    boundaries=list(re.finditer(r"[.!?;\n]",text))
    left=max((m.end() for m in boundaries if m.end()<=start),default=0)
    right=min((m.start() for m in boundaries if m.start()>=end),default=len(text))
    return text[left:start],text[end:right]


def _policy_term_mention(text, start, end):
    """Only explicit discussion of a prohibited word, not ordinary quoted ads."""
    before,after=_local_context(text,start,end)
    return bool(re.search(r"\b(?:word|term)\s+['\"‘“]?$",before,re.I)
        and re.match(r"['\"’”]?\s+is\s+(?:forbidden|disallowed|banned|not allowed|not permitted)\b",after,re.I)
        and re.search(r"\b(?:terminology|policy|guidelines?|guide)\b",after,re.I))


def _literal_nonclaim(text, match):
    """Return true for bounded non-promotional uses, not arbitrary negation.

    Never suppress every marker merely because 'not' occurs in the sentence.
    Not-only, double negation and later positive claims remain screened.
    """
    before,after=_local_context(text,match.start(),match.end())
    marker=" ".join(match.group().split()).casefold()
    if marker=="best" and re.match(r"\s+practices?\b",after,re.I):
        return True
    if marker=="only":
        following=text[match.end():]
        price=next(iter_prices(following),None)
        if price is not None and not following[:price.start].strip():
            # Price validity is still checked separately, even for a wrong price.
            return True
    if marker=="100%" and re.search(r"\b(?:set|adjust|turn)\b[^.!?;\n]{0,45}\bvolume\b\s*(?:level\s*)?(?:to|at)?\s*$",before,re.I):
        return True
    negated = re.search(r"\b(?:not|isn't|isn’t|aren't|aren’t|wasn't|wasn’t|weren't|weren’t)\s+(?:the\s+)?$",before,re.I)
    if negated and marker in ("best","fastest","cheapest","leading","number one","#1","unbeatable","guaranteed"):
        preceding=before[:negated.start()]
        if not re.search(r"\b(?:not|never|isn't|isn’t|aren't|aren’t)\s*$",preceding,re.I):
            return True
    return False


def _claims(text: str, context: ReviewContext, rule: Rule,
            evidence: list[ClaimEvidence]) -> list[Finding]:
    findings = []
    for match in _CLAIM_PATTERN.finditer(text):
        if _literal_nonclaim(text,match):
            continue
        sentence = _normalise_claim(_sentence(text, match.start(), match.end()))
        matching = [e for e in evidence if _normalise_claim(e.claim_text) == sentence]
        # Stable evidence reference when several approved sources support the same wording.
        fact = min(matching, key=lambda e: (e.id, e.version)) if matching else None
        if fact:
            explanation = (f"The sentence containing '{match.group()}' matches approved claim wording "
                           f"({fact.source.document_title}, {fact.source.location}).")
            verdict = "supported"
        else:
            explanation = (f"'{match.group()}' is a potential superlative, comparison or guarantee. "
                           "This claim is not substantiated in the approved sources supplied for this "
                           "product, market and date. Rewrite it or ask a reviewer to verify evidence. "
                           "This is a lexicon-based warning, not a claim that the statement is false.")
            verdict = "unsupported"
        findings.append(_finding(rule, category="claims", start=match.start(), end=match.end(),
            text=text, explanation=explanation, verdict=verdict, confidence=1.0 if fact else 0.8,
            evidence=fact))
    return findings


def check_rules(text: str, context: ReviewContext, rules: list[Rule],
                evidence: list[ClaimEvidence], *, org_id: str, brand_id: str,
                explicit_tone: bool = False) -> RuleCheckResult:
    """Resolve context before checking; callers never pass an unverified applied list.

    Backend A still authenticates and scopes all queries. Evidence must explicitly
    approve the same sentence, product, market and publication date. A battery
    fact cannot substantiate 'best'. No findings means only that these limited
    detectors found nothing; it never means automatic content approval.
    """
    resolution = resolve_rules(context, rules, org_id=org_id, brand_id=brand_id)
    active_evidence = [e for e in evidence if e.org_id == org_id and e.brand_id == brand_id
        and e.status == "approved" and e.product.strip().casefold() == context.product.strip().casefold()
        and bool(context.product.strip()) and e.market.strip().casefold() == context.market.strip().casefold()
        and (e.valid_from is None or e.valid_from <= context.publication_date)
        and (e.valid_to is None or context.publication_date <= e.valid_to)]
    findings = []
    for item in resolution.applied:
        rule = item.rule
        findings.extend(_terminology(text, rule))
        findings.extend(_disclaimer(text, rule))
        if explicit_tone: findings.extend(_explicit_tone(text, rule))
        if rule.requires_claim_evidence:
            findings.extend(_claims(text, context, rule, active_evidence))
    # Rule-authority order is preserved. Conflicting rules stay separate for a
    # human; a future fix applier must reject overlapping/colliding replacements.
    return RuleCheckResult(resolution, tuple(findings))


def _explicit_tone(text, rule):
    """Only explicit, narrow text constraints from an applicable approved rule.

    Emoji counts use Unicode code points, as in Role A's original checker;
    this is not grapheme/visual emoji counting or a semantic tone judgement.
    """
    if rule.category != 'tone': return []
    out=[]
    cap=re.search(r'\bno more than (\d+|one|two|three) emojis\b',rule.instruction,re.I)
    if cap:
        token=cap[1].casefold()
        maximum={'one':1,'two':2,'three':3}.get(token)
        if maximum is None: maximum=int(token)
        for match in list(re.finditer(r'[\U0001F300-\U0001FAFF]',text))[maximum:]:
            out.append(_finding(rule,category='tone',start=match.start(),end=match.end(),text=text,
                explanation=f'{rule.code} permits no more than {maximum} emoji code points.'))
    if re.search(r'\bno exclamation marks\b',rule.instruction,re.I):
        for match in re.finditer('!',text):
            out.append(_finding(rule,category='tone',start=match.start(),end=match.end(),text=text,
                explanation=f'{rule.code} explicitly prohibits exclamation marks.'))
    return out
