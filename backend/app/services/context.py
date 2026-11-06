"""Select applicable approved rules without AI, SQL or implicit overrides."""

from .contracts import AppliedRule, ReviewContext, Rule, RuleResolution, SkippedRule

_AUTHORITY = {"non_overridable": 0, "core": 1, "scoped": 2, "exception": 3}
_DIMENSIONS = ("channel", "audience", "region", "content_type", "campaign")


def _normalise(value: str) -> str:
    return value.strip().casefold()


def _order(rule: Rule):
    specificity = sum(bool(getattr(rule.scope, dimension)) for dimension in _DIMENSIONS)
    return (_AUTHORITY[rule.authority], -specificity, -rule.priority, rule.code, rule.version, rule.id)


def resolve_rules(context: ReviewContext, rules: list[Rule], *, org_id: str, brand_id: str) -> RuleResolution:
    """Return applied/skipped rules and stable, human-readable explanations.

    Backend A must authenticate and scope its database query first. As a second
    guard, foreign organisation/brand rules are omitted from BOTH result lists.
    Empty scope means all values; missing context cannot match a nonempty scope.
    Scope tags are compared case-insensitively after trimming surrounding spaces.
    All dimensions must match. Order is authority, specificity, then priority.
    Ordering does not override rules or resolve conflicts: all matches survive.
    """
    if not org_id.strip() or not brand_id.strip():
        raise ValueError("An authenticated organisation and selected brand are required.")
    values = {"channel": context.channel, "audience": context.audience,
              "region": context.market, "content_type": context.content_type, "campaign": context.campaign}
    applied, skipped = [], []
    candidates = sorted((r for r in rules if r.org_id == org_id and r.brand_id == brand_id),
                        key=lambda r: (r.code, r.version, r.id))
    for rule in candidates:
        reason = None
        if rule.status != "approved":
            reason = f"Rule status is {rule.status}; only approved rules apply."
        elif rule.authority not in _AUTHORITY:
            raise ValueError(f"Unknown authority for rule {rule.code}: {rule.authority}")
        elif rule.effective_from and rule.effective_to and rule.effective_from > rule.effective_to:
            raise ValueError(f"Invalid effective-date range for rule {rule.code}.")
        elif rule.effective_from and context.publication_date < rule.effective_from:
            reason = f"Not effective until {rule.effective_from.isoformat()}."
        elif rule.effective_to and context.publication_date > rule.effective_to:
            reason = f"Expired on {rule.effective_to.isoformat()}."
        matches = []
        if reason is None:
            for dimension in _DIMENSIONS:
                allowed = getattr(rule.scope, dimension)
                if not allowed:
                    continue
                value = values[dimension]
                if value is None or not value.strip():
                    reason = f"Missing context: {dimension}; rule requires one of {list(allowed)}."
                    break
                if _normalise(value) not in {_normalise(tag) for tag in allowed}:
                    reason = f"scope_{dimension}: rule={list(allowed)}, context={value}"
                    break
                matches.append(f"{dimension}={value.strip()}")
        if reason is not None:
            skipped.append(SkippedRule(rule, reason))
        else:
            why = "Matches " + ", ".join(matches) if matches else "General rule: no scope restrictions."
            why += f" Approved and effective on {context.publication_date.isoformat()}."
            applied.append(AppliedRule(rule, why))
    applied.sort(key=lambda item: _order(item.rule))
    return RuleResolution(tuple(applied), tuple(skipped))
