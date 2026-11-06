# MindVault Role B evaluation report

Assistant-authored synthetic labels; independent human review still required.

This evaluates the deterministic-only service on a small synthetic development dataset. It is not live Gemini evaluation, independent validation or a general accuracy claim.

Exact category + verdict + quoted text multiset; supported/info findings excluded from issue scoring.

| Group | Cases | Exact cases | Matched issues | Extra warnings | Missed labels | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All | 50 | 47 | 30 | 1 | 3 | 96.8% | 90.9% |
| baseline | 30 | 30 | 21 | 0 | 0 | 100.0% | 100.0% |
| challenge | 20 | 17 | 9 | 1 | 3 | 90.0% | 75.0% |

Invalid returned spans: 0. Missing evidence on conclusive findings: 0.

Precision counts matched issue labels divided by all emitted issue warnings. Recall counts matched labels divided by expected issue labels. A wrong verdict or quote can count as both an extra warning and a missed label. needs_review is a warning class, not a confirmed violation. Blank disclaimers represent end insertions.

Supported facts are excluded from issue scoring. The evidence check verifies presence, not semantic correctness or that a cited claim is actually substantiated. Case/issue coverage is limited; review every mismatch before changing the engine or labels.

## Case mismatches

### C06 (challenge)

Beat 200 is totally awesome!

The explicit formal/no-exclamation investor rule applies; deterministic services do not yet enforce tone.

Missed: `[{"category": "tone", "verdict": "violation", "quote": "totally awesome!", "count": 1}]`

Unexpected: `[]`

### C07 (challenge)

Beat 200 outperforms every competitor.

A comparative meaning is present without an approved claim-evidence record; its phrasing is outside the lexicon.

Missed: `[{"category": "claims", "verdict": "unsupported", "quote": "outperforms every competitor", "count": 1}]`

Unexpected: `[]`

### C14 (challenge)

Air 100 at ₹1499. It has battery life up to 50 hours.

A human reads it as Air 100, while the selected product is Beat 200. The engine deliberately does not resolve cross-sentence pronouns.

Missed: `[{"category": "battery_life", "verdict": "violation", "quote": "up to 50 hours", "count": 1}]`

Unexpected: `[{"category": "battery_life", "verdict": "needs_review", "quote": "up to 50 hours", "count": 1}]`

## Next actions

Have a teammate review the labels against the fictional policies. Prioritise negation, ordinary uses of superlative keywords, unit phrasing and product-attribution errors. Keep challenge labels visible. Add real user examples only with permission and appropriate privacy handling. Evaluate live AI separately and identify its model/version and usage status.
