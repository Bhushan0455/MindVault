# MindVault Role B integration handoff

Role B supplies analysis services. Role A supplies the authenticated application,
database, endpoints, background jobs, saved decisions, approvals and deployment.
These files are a standalone Python module package, not a complete API server.

## Start here

Copy `app/services/` modules into the backend repository after reviewing existing
file names. Merge `contracts.py` deliberately; do not overwrite your SQLAlchemy
models or existing services blindly. These dataclasses are service inputs/outputs,
not a replacement database schema. Map DB records into them at the boundary.

From the supplied `backend` directory:

```powershell
py -m pip install -r requirements.txt
py -m unittest discover -s tests -v
py -m evaluation.run_evaluation
```

The current development check is 318 passing unit tests. The separate synthetic
evaluation contains 50 cases and deliberately exposes shortcomings. The team
originally planned Python 3.12 deployment; the user ran earlier tests on 3.14.
Agree on and test the deployment version instead of assuming compatibility.

## Services to call

| Task | Entry point | Output |
| --- | --- | --- |
| Read uploaded document | extraction.extract_document(filename, bytes) | Marked text, ordered blocks, source locations, original-byte hash and warnings |
| Propose knowledge | knowledge_extract.extract_candidates(document, org_id, brand_id, document_id) | Pending candidates and rejected-item issues |
| Review content | ai_review.run_review(text, context, products, rules, numeric_facts, claim_evidence, org_id, brand_id, generator, cache) | Deterministic and validated optional-AI findings, context resolution, hash, AI status and issues |
| Apply human decisions | fixes.apply_selected_fixes(text, revision_id, expected_body_hash, decisions) | Revised string/hash, applied trace, skipped decisions and changed flag |
| Audit rule clarity | ai_clarity.run_clarity_audit(rules, org_id, brand_id, generator, cache) | Pending clarity proposals, snapshot bindings, checked IDs, AI status and issues |

Most arguments after the first input are keyword-only: consult function signatures
or the working examples. Use the combined services rather than independently
repeating all low-level checks, which would create duplicate findings.

## Data mapping

- `ReviewContext`: canonical product name, market, publication_date; optional
  channel/audience/content_type/campaign. Here market also supplies region scope.
- `Product`: stable ID, organisation/brand, canonical name and aliases.
- `NumericFact`: stable ID/version, organisation/brand/product ID, price /
  battery_life / warranty, Decimal value, unit, exact/up_to qualifier, market,
  approval status, effective dates and retained Source.
- `ClaimEvidence`: explicit approved claim wording with product, market, source,
  dates and version. Generic battery evidence must not substantiate "best".
- `Rule`: stable ID/code/version, instruction/source, approval status, structured
  scope, authority/priority and structured check fields. Rule prose alone does
  not activate a detector. Map forbidden_terms, preferred_terms, required_text
  and requires_claim_evidence as appropriate.
- `Source`: document ID/title, honest location and excerpt. DOCX uses paragraph/
  table references, not invented page numbers.
- `Finding`: service result with origin, category, severity, confidence, verdict,
  original-text span/quote, explanation, optional replacement and evidence/version.
  Add your finding/run/revision IDs, decision state and actor metadata on saving.

Convert Decimal/date/dataclass values through your existing JSON response schemas.
Keep the frontend's agreed response shapes; these internal dataclasses are not
the final nested API schemas. Convert DB arrays to tuples for RuleScope. Map UI
accept/edit/reject actions to persisted accepted/edited/rejected decisions.

## First integration target

1. Load a creator's current revision, its context and scoped approved knowledge.
2. Create a review-run record bound to revision ID and hash; return the run ID.
3. In a bounded worker, call `run_review(..., generator=None)` first.
4. Persist every finding, including supported/info evidence dependencies, plus
   applied/skipped rule snapshots and AI status. Do not mark a newer revision
   checked if the user edited while the run was executing.
5. Expose results/progress through your existing polling endpoint. Show evidence,
   missing-AI notices and needs_review items without calling them approved.
6. Persist creator decisions. Load those saved records into FixDecision, call
   apply_selected_fixes and atomically verify the base revision/hash before
   creating revision N+1. Preserve N; reset state; queue the new review.
7. Enforce your submit gate and reviewer role checks. Approval binds the exact
   revision/hash, with immutable approval history and stale-decision rejection.

No analysis service grants permissions or performs the final save transaction.
Org/brand guards are additional checks, not authentication. Never let a browser
choose another tenant's records or supply an authoritative reviewed-body hash.

## Source and text details

Draft/finding offsets are Python Unicode code points, start-inclusive/end-exclusive.
React strings use UTF-16 positions: convert appropriately (e.g. Array.from-based
slicing) and test leading emojis. Extraction offsets are into extracted marked
document text, not into draft text or binary files. Do not mix these coordinate
systems. A missing disclaimer is an end insertion with an empty quote.

Accepted fixes replace exactly one span; edited_text="" explicitly deletes.
None means no replacement was supplied. The helper rejects overlaps, stale
spans and competing insertions, including insertion/replacement boundaries.
There is no partial batch application on conflict. Recheck after every new text
revision; safe replacement is not proof of grammar or compliance.

Extracted candidates and clarity rewrites are pending. Admin review must complete
market, scope, dates, product mapping, authority and criteria before approval.
An empty field is not permission to silently broaden applicability. Clarity
limits such as 8 words are proposals, not facts extracted from the guidelines.
Use proposal_is_current and an atomic version check before saving a rewrite.

## Optional AI integration

Install requirements-ai.txt and configure GEMINI_API_KEY and GEMINI_MODEL privately
on the server. The key never belongs in React. Use GeminiContentGenerator for
content review, GeminiClarityGenerator for clarity, and GeminiKnowledgeGenerator
for knowledge extraction. All model IDs are environment-configured.

Live Gemini is NOT verified. An earlier account request reported an old model
unavailable and recommended a newer one. Do not claim model/SDK availability from
unit tests. Verify account/model access and quotas using fictional samples, and
lock the successful SDK/model configuration for submission. Tests use provider
fakes only at the boundary; production paths never substitute mock AI output.

Persist metadata-only adapter.events, not keys or draft content. Keep AI notices:
not_requested, unavailable, input_limit, no_rules (clarity), completed and
validated_with_issues. ai_used=true can reflect a cached provider response, not
new network activity. A valid citation does not prove semantic correctness.

ReviewCache is optional, in-memory, bounded and contains protected excerpts.
Backend A decides worker ownership, concurrency, retention and deployment privacy.
All parsing/model calls are blocking: use bounded workers and enforce request,
memory and time limits. Interrupted jobs must not leave frontend polling forever.

## Evaluation evidence and known gaps

`evaluation/cases.json` has 30 baseline and 20 challenge cases. Labels are
assistant-authored synthetic development labels, not independently validated.
`evaluation/results/evaluation_report.md` and `.json` record actual output.

Current Step 16 deterministic-only result: 30/30 baseline exact matches; 17/20 challenge
exact matches. Challenges produced 1 extra warning and 3 missed labels.
Step 15 previously had 15/20 challenge matches, 4 extra warnings and 4 missed labels.
Step 14 previously had 11/20 challenge matches and 8 missed labels.
Step 13 previously had 5/20 challenge matches and 10 extra warnings. Labels were not changed.
Read case rationales and disagreements. Zero invalid spans/missing conclusive
source fields is a presence check, not proof of source entailment or real accuracy.

Important gaps: complex negated/ordinary superlative wording, unsupported number
scales/fractions, cross-sentence pronouns, grouped/complex multi-product claims,
ambiguous duration subjects, and tone without real AI. Clear independent product+
number clauses are now split; direct shipping durations are excluded from spec checks.
The dataset scores non-supported issues by exact category/verdict/quote multiset;
it does not score supported-claim correctness or independently evaluate AI.

## Integration acceptance checklist

- Public demo: INR 799 versus approved INR 999 with a genuine source.
- Same path works with the AI key missing and a clear limitation notice.
- Pending/rejected and foreign knowledge cannot influence the current review.
- Exact revision/hash survives save, finding decisions, fixes and approval.
- Manual edits and new fixes create a new unapproved revision.
- Org/role isolation and stale approval checks are enforced through the API.
- Source locations, emojis, insertion findings and error states render correctly.
- Admin approval completes candidates and creates immutable knowledge versions.
- Live AI, evaluation shortcomings and simulation labels are disclosed honestly.

## Not delivered by Role B

No FastAPI routers, JWT system, SQLAlchemy persistence, production upload endpoint,
queue scheduler, approval endpoint, frontend, hosting configuration, source-sync
connector, complete conflict engine or automatic publication. These modules
support integration with Role A's app; they do not replace that application.
