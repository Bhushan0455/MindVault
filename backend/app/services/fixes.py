"""Step 9: pure, all-or-nothing application of recorded human fix decisions.

No authentication, persistence, approvals or review jobs here. Backend A loads
trusted records and performs its final revision check/save in one transaction.
"""

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest

from .contracts import Finding


class FixError(ValueError):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(detail)


def body_hash(text: str) -> str:
    """SHA-256 of original UTF-8 text, without whitespace/Unicode normalisation."""
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FixDecision:
    finding_id: str
    revision_id: str
    finding: Finding
    status: str  # accepted | edited | rejected | open | dismissed
    edited_text: str | None = None  # empty string explicitly means deletion
    note: str | None = None


@dataclass(frozen=True)
class AppliedFix:
    finding_id: str
    span_start: int
    span_end: int
    quoted_text: str
    replacement: str


@dataclass(frozen=True)
class SkippedFix:
    finding_id: str
    reason: str


@dataclass(frozen=True)
class FixResult:
    base_revision_id: str
    base_body_hash: str
    body_text: str
    body_hash: str
    changed: bool
    applied: tuple[AppliedFix, ...]
    skipped: tuple[SkippedFix, ...]


def apply_selected_fixes(text: str, *, revision_id: str, expected_body_hash: str,
                         decisions: list[FixDecision]) -> FixResult:
    """Validate every edit before applying any replacement, right to left.

    The expected hash must come from the analysed revision, NOT a browser field.
    Offsets use original Python Unicode code points (start inclusive/end exclusive).
    Insertion collisions, including replacement boundaries, need human resolution.
    This function never chooses a winner or applies a partial batch on failure.
    """
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise FixError("invalid_revision", "A saved revision ID is required.")
    if not isinstance(text, str) or not isinstance(expected_body_hash, str):
        raise FixError("invalid_input", "Text and the trusted review body hash must be strings.")
    original_hash = body_hash(text)
    if (len(expected_body_hash) != 64 or any(c not in "0123456789abcdef" for c in expected_body_hash)
        or not compare_digest(original_hash, expected_body_hash)):
        raise FixError("stale_text", "Text changed since the review. Recheck before applying fixes.")
    if len(decisions) > 100:
        raise FixError("fix_limit", "At most 100 decisions can be processed in one batch.")
    edits, skipped, ids = [], [], set()
    for decision in decisions:
        if not isinstance(decision, FixDecision) or not isinstance(decision.finding_id, str) or not decision.finding_id.strip():
            raise FixError("invalid_decision", "Every decision needs a saved finding ID.")
        if decision.finding_id in ids:
            raise FixError("duplicate_finding", "A finding appears more than once in the batch.")
        ids.add(decision.finding_id)
        if decision.revision_id != revision_id:
            raise FixError("stale_revision", "A finding belongs to another revision. Recheck the current revision.")
        if decision.status not in ("accepted", "edited", "rejected", "open", "dismissed"):
            raise FixError("invalid_decision", "Unknown finding decision status.")
        if decision.status == "rejected" and (not isinstance(decision.note, str) or not decision.note.strip()):
            raise FixError("missing_reason", "Rejected findings require a reason.")
        if decision.status not in ("accepted", "edited"):
            skipped.append(SkippedFix(decision.finding_id, "Decision is " + decision.status + "; text retained."))
            continue
        finding = decision.finding
        if not isinstance(finding, Finding):
            raise FixError("invalid_finding", "Load the saved finding before applying its decision.")
        if finding.verdict == "supported":
            raise FixError("supported_finding", "A supported finding is not a correction. Use a normal manual revision edit.")
        start, end = finding.span_start, finding.span_end
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(text):
            raise FixError("invalid_span", "A finding has invalid original-text offsets.")
        if text[start:end] != finding.quoted_text:
            raise FixError("stale_span", "The finding quote does not match the original text at its saved location.")
        replacement = decision.edited_text if decision.status == "edited" else finding.suggested_fix
        if not isinstance(replacement, str):
            raise FixError("fix_unavailable", "No replacement text is available. Ask the creator to edit the finding explicitly.")
        if replacement == text[start:end]:
            skipped.append(SkippedFix(decision.finding_id, "Replacement makes no text change."))
            continue
        edits.append(AppliedFix(decision.finding_id, start, end, finding.quoted_text, replacement))
    edits.sort(key=lambda edit: (edit.span_start, edit.span_end, edit.finding_id))
    for index, left in enumerate(edits):
        for right in edits[index+1:]:
            left_insertion, right_insertion = left.span_start == left.span_end, right.span_start == right.span_end
            if left_insertion or right_insertion:
                insertion, other = (left, right) if left_insertion else (right, left)
                if other.span_start <= insertion.span_start <= other.span_end:
                    raise FixError("insertion_conflict", "Insertions overlap another edit or its boundary. Combine them explicitly before applying.")
            elif left.span_start < right.span_end and right.span_start < left.span_end:
                raise FixError("overlapping_fixes", "Selected fixes overlap. Choose or edit one correction; no changes applied.")
    if len(text) + sum(len(e.replacement) - (e.span_end-e.span_start) for e in edits) > 1_000_000:
        raise FixError("text_limit", "Revised text exceeds the one-million-character limit.")
    revised = text
    for edit in reversed(edits):
        revised = revised[:edit.span_start] + edit.replacement + revised[edit.span_end:]
    if len(revised) > 1_000_000:
        raise FixError("text_limit", "Revised text exceeds the one-million-character limit.")
    return FixResult(revision_id, original_hash, revised, body_hash(revised), revised != text,
                     tuple(edits), tuple(skipped))
