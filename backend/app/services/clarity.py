"""Step 10: narrow, deterministic clarity screening of current rule versions.

Advisory proposals only. No AI calls, rule mutations or automatic approval.
Cross-rule contradictions, duplicates and visual inspection are not implemented.
"""

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import re

from .contracts import Rule, Source


@dataclass(frozen=True)
class ClarityFinding:
    id: str
    rule_id: str
    rule_code: str
    rule_version: int
    rule_snapshot_hash: str
    kind: str
    excerpt: str  # slice of current rule instruction, not a claimed document quote
    span_start: int
    span_end: int
    why_it_matters: str
    suggested_rewrite: str  # full proposed instruction, preserving other sentences
    example_good: str
    example_bad: str
    assumptions: tuple[str, ...]
    requires_completion: bool
    source: Source
    method: str = field(default="deterministic", init=False)
    status: str = field(default="pending", init=False)


@dataclass(frozen=True)
class ClarityResult:
    findings: tuple[ClarityFinding, ...]
    checked_rule_ids: tuple[str, ...]
    issues: tuple[str, ...]
    method: str = field(default="deterministic", init=False)


def rule_snapshot_hash(rule: Rule) -> str:
    """Includes scope, status, source and structured fields, not only instruction."""
    data = json.dumps(asdict(rule), sort_keys=True, default=str, ensure_ascii=False)
    return sha256(data.encode("utf-8")).hexdigest()


def proposal_is_current(rule: Rule, proposal: ClarityFinding) -> bool:
    """Role A must additionally authenticate and atomically check/save its version."""
    return (rule.id == proposal.rule_id and rule.code == proposal.rule_code
            and rule.version == proposal.rule_version and rule_snapshot_hash(rule) == proposal.rule_snapshot_hash)


_SUBJECT = re.compile(r"\b(headlines?|titles?|captions?|sentences?|paragraphs?|copy)\b", re.I)
_LENGTH = re.compile(r"\b(short|brief|concise|lengthy|too long)\b", re.I)
_MEASURE = re.compile(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:words?|characters?|lines?|sentences?)\b", re.I)
_VISUAL = re.compile(r"\b(?:use|choose|select)\s+(?:an?\s+)?(?:attractive|appealing|nice|eye-catching)\s+(?:visuals?|images?|graphics?)\b", re.I)
_CONDITIONAL = re.compile(r"\b(?:where appropriate|when appropriate|as needed|if necessary)\b", re.I)


def _length_proposal(subject):
    subject = subject.casefold()
    if subject.startswith("paragraph"):
        return ("Paragraphs must contain no more than 3 sentences.",
                "Clear sound matters. Explore the product details.",
                "One sentence. A second sentence. A third sentence. A fourth sentence.",
                "The 3-sentence limit is an illustrative proposal, not an approved or extracted threshold.")
    if subject.startswith("sentence"):
        return ("Sentences must contain no more than 20 words.",
                "Explore headphones designed for everyday listening.",
                "This example sentence deliberately keeps adding unnecessary words so that its final length exceeds the proposed twenty word maximum for a sentence.",
                "The 20-word limit is illustrative; an admin must choose a suitable threshold.")
    if subject == "copy":
        return ("Copy must contain no more than 60 words.",
                "Explore Veyra Beat 200 and review its approved specifications.",
                "A draft containing 61 words would fail this proposed limit (described example).",
                "The 60-word limit is illustrative; define the applicable channel/content type before approval.")
    noun = "Headlines" if subject.startswith("headline") else "Titles" if subject.startswith("title") else "Captions"
    return (f"{noun} must contain no more than 8 words.",
            "Discover clear sound for everyday listening",
            "Discover our new headphones and explore all their features in great detail today",
            "The 8-word limit is illustrative; an admin must approve or replace it. It is not in the source rule.")


def audit_clarity(rules: list[Rule], *, org_id: str, brand_id: str) -> ClarityResult:
    """Audit extracted/pending/approved rules without deciding brand policy.

    Approved future/expired-dated rules may also need clearer wording, so this
    audit intentionally does not filter by publication date. Role A controls
    authenticated admin access and loads the desired current document versions.
    """
    if not org_id.strip() or not brand_id.strip():
        raise ValueError("Authenticated organisation and selected brand are required.")
    if len(rules) > 500: raise ValueError("Audit at most 500 rule records per batch.")
    findings, checked, issues, seen = [], [], [], set()
    for rule in sorted(rules, key=lambda r: (r.code, r.version, r.id)):
        if rule.org_id != org_id or rule.brand_id != brand_id: continue
        if rule.status not in ("extracted", "pending", "approved"):
            issues.append(f"Skipped {rule.code} v{rule.version}: status={rule.status}.")
            continue
        if rule.id in seen: raise ValueError("Rule IDs must be unique in one clarity audit.")
        seen.add(rule.id)
        if not rule.instruction.strip() or len(rule.instruction)>20000:
            issues.append(f"Skipped {rule.code}: empty or oversized instruction.")
            continue
        checked.append(rule.id)
        snapshot = rule_snapshot_hash(rule)
        def emit(kind, match, why, rewrite, good, bad, assumptions, requires_completion=False):
            start,end=match.span()
            # Sentences are matched in the original instruction to retain offsets.
            original=rule.instruction[start:end]
            while original and original[0].isspace(): start+=1; original=original[1:]
            while original and original[-1].isspace(): end-=1; original=original[:-1]
            identity=f"{org_id}|{brand_id}|{rule.id}|{snapshot}|{kind}|{start}|{end}"
            findings.append(ClarityFinding(sha256(identity.encode()).hexdigest(), rule.id, rule.code, rule.version,
                snapshot, kind, original, start, end, why,
                rule.instruction[:start]+rewrite+rule.instruction[end:], good, bad,
                tuple(assumptions), requires_completion, rule.source))
        for match in re.finditer(r"[^.!?\n]+[.!?]?", rule.instruction):
            sentence = match.group()
            # This first heuristic avoids reversing negative instructions.
            if re.search(r"\b(?:not|never|avoid)\b", sentence, re.I): continue
            subject = _SUBJECT.search(sentence)
            if subject and _LENGTH.search(sentence) and not _MEASURE.search(sentence):
                rewrite,good,bad,assumption = _length_proposal(subject.group())
                emit("missing_threshold",match,"Reviewers cannot consistently decide whether the text is short enough without a measurable limit.",
                     rewrite,good,bad,(assumption,"Proposed examples are illustrative, not approved brand content. Review qualifiers and exceptions before adopting this rewrite."))
            elif _VISUAL.search(sentence):
                emit("undefined_term", match,"Attractive or appealing does not specify which visual features a reviewer should accept.",
                    "For [channel/content type], define accepted visual criteria: [composition], [colour palette], [logo placement] and [contrast standard]. Link an accepted and a rejected example.",
                    "Illustrative good case: a visual matching the admin-approved checklist and accepted example.",
                    "Illustrative bad case: a visual that violates an explicitly documented checklist criterion.",
                    ("The bracketed criteria and asset examples must be supplied by the admin; no visual was inspected.",), True)
            elif _CONDITIONAL.search(sentence) and not any(getattr(rule.scope, dimension) for dimension in ("channel","audience","region","content_type","campaign")):
                # Preserve the original requirement until an admin defines its condition.
                emit("scope_gap", match,"The condition is unspecified and there is no structured scope to show when the rule applies.",
                    sentence.strip()+" Applies when: [admin-defined channel, audience, region, content type or explicit trigger].",
                    "Illustrative good case: the trigger is explicit and the draft satisfies the requirement when that trigger matches.",
                    "Illustrative bad case: two reviewers cannot agree whether an unspecified trigger applies.",
                    ("The trigger is unknown. Complete the bracketed condition and reconcile the original conditional wording before approval.",), True)
    issues.append("Advisory rule-based screening only. No contradictions, duplicates or actual visuals were checked; no finding does not prove clarity.")
    return ClarityResult(tuple(findings),tuple(checked),tuple(issues))
