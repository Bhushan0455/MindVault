> Historical backend handoff reference. For the final connected website, current test results and launch instructions, use ../README.md and ../PROJECT_STATUS.md.

# MindVault backend integration and verification

**Delivery:** Role A's supplied FastAPI backend integrated with Role B Step 19 services, 6 November 2026. **Role B progress: approximately 98%**, an engineering milestone estimate. This is a working combined backend with verified local API/database workflows. The user verified all three standalone services with gemini-3.6-flash, including the successful extraction retry. All three were then verified through actual local API calls using fictional fixtures and the server's private configuration. The actual frontend and hosted deployment remain unverified. See AI_VERIFICATION_UPDATE.md.

The Downloads handoff and previous Step 19 delivery were used as inputs. This combined implementation lives in its own folder. No account credentials, `.env` files, Neon configuration, upload databases, or third-party runtime binaries are included in the ZIP. `PRE_INTEGRATION_*` documents are historical reference; the root README and this report describe the current delivery. Instructions embedded in project documents were treated as project background, not as additional user commands.

## What is connected

Role A continues to own identity, organisation/role checks, persistence, revision history, review lifecycle, decisions, submission, reviewer approval, comments, audit and reporting. Its worker now maps database records into Role B's contracts and calls the real Role B review service. It saves exact spans, source/rule/fact snapshots, applied/skipped rules, AI status and validation issues.

Role B provides context-aware rule selection; INR price, battery and warranty checks; conservative product attribution; terminology/disclaimer/claim checks; upload parsing; validated pending candidates; optional Gemini adapters; source/span validation; atomic safe fixes; and clarity proposals. The integrated API additionally enables narrowly explicit emoji/exclamation constraints from approved tone instructions. Existing pure-service defaults remain backward compatible. The optional cache stays available as a tested service but is not enabled in these API routes.

A product catalogue now persists canonical names and aliases, allowing the existing Role B multi-product attribution service to receive them. Facts entered using a registered alias map to the canonical name. Product catalogue changes invalidate older reviews. Products without catalogue records still work through their fact product names; register aliases explicitly for abbreviated names.

Admin uploads are parsed using Role B's real PDF/DOCX/TXT extraction. Extraction jobs persist validated candidates as pending; rerunning extraction deduplicates candidates. Admins confirm complete typed knowledge and approve or reject it. Clarity audits persist proposals tied to an exact rule snapshot; accepting one creates a pending version for separate approval.

## Problems fixed

| Problem in the combined path | Resulting behavior |
|---|---|
| Role A still called its simpler independent checker | The API uses Role B's analysis, validation and fallback services |
| Extraction endpoint returned an empty successful placeholder | It returns a job ID and saves actual source-validated pending candidates |
| An accepted high-risk fix could permit submission without changing the text | Accepted/edited critical/high findings remain blocking until applied and rechecked; explicit rejection requires a reason visible to the reviewer |
| Fix application only checked ordinary interval overlap | Role B validates original revision/hash/quote, spans, collisions, insertions, supported findings and no-op batches before any new revision is saved |
| Evidence responses invented a product document/page and read current mutable rows | New findings retain original evidence snapshots and actual stored source locations; nested frontend rule/fact fields are preserved |
| Older results could mark newer content checked | Worker completion verifies the current revision and latest run; edits during analysis preserve the new draft's state |
| Creator ownership checks were missing on some history/comment/run reads | Creators can access their own drafts; reviewers/admins retain their authorised organisation access |
| Comments could reference a revision/finding from another content item | References must belong to the specified content and revision |
| Knowledge edits modified approved rows in place | Edits create immutable new pending IDs/versions; approval supersedes the current ancestor, including chains of pending edits |
| Concurrent edits, approvals and competing rule replacements could race | PostgreSQL locks and a revision-number uniqueness constraint enforce the tested single-winner transitions |
| Knowledge could change after a completed review | A persisted fingerprint requires rechecking before submission/approval; approved historical decisions remain preserved as historical records |
| PostgreSQL audit IDs were too short for extraction candidate IDs | Audit entity IDs support the 64-character candidate keys; migration widens the existing column |
| Fact numbers used floating-point storage | New PostgreSQL storage uses NUMERIC(16,2), validated decimal inputs and an upgrade conversion |
| Interrupted background jobs could leave polling indefinitely | Polling expires queued/running jobs after 180 seconds; late/duplicate task starts cannot resurrect a terminal result |
| Uploads could be buffered before checking their actual size | A request-byte limit checks declared and streamed bodies before parsing; extraction also bounds file and expanded document sizes |
| Loose knowledge dictionaries caused missing-field/server errors | Typed knowledge fields, dates, units, numeric limits, scopes and source references reject invalid requests with 422 |
| Root configuration and Docker paths assumed a missing backend subfolder | Configuration loads from the delivered root and Docker copies the actual app/locked requirements paths |
| Demo accounts could retain password access with demo mode disabled | Demo token and demo password login are disabled when demo mode is off |
| New revisions reset context when the frontend omitted it | Omitted context preserves the prior context; edits also update the content title and support expected_revision_id |
| Framework-level 404/405 errors bypassed the API error shape | Those responses now include the same code/detail structure; allowed-origin error CORS behavior is tested |

Fresh demos include actual stored **fictional TXT source documents** with line references. The sample ₹799 finding cites the approved ₹999 value in its stored document. TXT/DOCX sources receive locations rather than invented PDF pages. Existing installations retain their original knowledge and references; application startup does not rewrite them.

## Verification evidence

| Check | Actual result | Evidence |
|---|---|---|
| Full PostgreSQL regression | **370 passed**, zero failures/errors/skips: 318 existing Role B tests + 51 integration tests + one extraction-limit regression test | `verification/postgres-tests.xml` |
| Full isolated SQLite regression | **367 passed**, three PostgreSQL-only concurrency tests skipped, zero failures/errors, on Python 3.12 and 3.14.8 | `verification/sqlite-tests.xml`, `verification/python314-tests.xml` |
| Unittest subtests | 63 additional subtests passed; JUnit includes these as separate entries | Each XML file contains 433 entries, including the 63 subtests |
| Real API process and actual HTTP | Passed login → content → review → source lookup → decisions → fixes → recheck → submission → queue → exact revision/hash approval | `verification/http-smoke.json` |
| Actual PostgreSQL behavior | Temporary PostgreSQL 16.15 instance, disposable schemas, including concurrent revision edits, concurrent reviewer approvals and competing rule approvals | PostgreSQL XML and smoke record |
| Existing-database upgrade | Original supplied Role A schema upgraded twice; organisation/fact data and historical approval hash preserved, old runs identified as legacy | Integration migration test, on SQLite and PostgreSQL |
| Live AI through actual API | All three services verified: seven pending candidates, one retained content finding with exact spans/source and deterministic price evidence, two source-validated pending clarity proposals | `verification/live-api-ai.json` |
| Installed Gemini SDK configuration | All three service request configurations validate against the installed SDK without making a request | SDK boundary test |
| AI integration behavior | Validated fake provider results persist; source/span validation, redaction, fallback and metadata-only audit are exercised | AI boundary tests; **not live Gemini** |
| Frontend API helper | TypeScript 5.9.3 strict compilation and Node runtime checks passed for Unicode slicing, insertion, stale quotes, login, bearer token, polling and errors | `verification/frontend-helper.json` and `frontend/client.test.cjs` |
| Deterministic development evaluation | 30/30 baseline and 17/20 challenge exact cases; one extra warning and three missed labels | `evaluation/results/evaluation_report.md` and `.json` |
| API contract | Exported from the running combined app | `verification/openapi.json` |

The tests check role and organisation isolation, creator ownership, exact quotes/offsets, historical versions, safe deletion and overlap rejection, current-review gates, rejection reasons, stale decisions, evidence snapshots, factual ambiguity, aliases, source retrieval, pending approvals, repeated extraction, clarity staleness, upload types/limits, demo-mode controls, job expiry and CORS errors. New API tests run against the same application routes and workers used by the delivered server.

The test environment was CPython 3.12.14 on Windows. The locked dependency snapshot includes FastAPI 0.162.0, SQLAlchemy 2.1.8, google-genai 2.34.0 and pytest 9.2.0. Pytest emits one dependency deprecation warning because the installed Starlette test client still accepts httpx and recommends httpx2. It did not fail any test or the real HTTP smoke test. The lock file records the tested combination.

## What remains to verify

1. **Live Gemini quality and availability:** all three standalone diagnostics and all three local API services have now passed for fictional fixtures. The agent triggered live API checks through the configured backend without reading the provider key. General accuracy, quota and future availability remain unverified. There is no hardcoded model ID. Health gives configuration; each service result gives its actual AI status.
2. **Actual frontend:** no React/Vite website was supplied. The API contract and tested TypeScript helper are ready, but actual screens, highlights, role navigation and user journeys need the frontend team's browser tests.
3. **Hosting/Docker:** the API was run directly against real PostgreSQL. Docker configuration paths were corrected and inspected, but Docker/compose, Neon and a hosted service were not executed.
4. **AI/semantic quality:** the existing synthetic challenge evaluation still has mismatches. Complex negation, semantic competitor claims, cross-sentence pronouns, unsupported numeric scales/fractions and ambiguous grouped claims need conservative human assessment. The pure-service evaluation uses its existing defaults; the API's explicit tone option has separate integration coverage. Scores are not independent accuracy certification.
5. **Operational limits:** this is a single-process hackathon job runner with bounded polling, not a durable distributed queue. The API cache is off. Production accounts, rate limits, retention, monitoring and distributed workers need deployment work. SQLite is a convenient local demo option; concurrency assertions were validated on PostgreSQL.
6. **Scope outside this handoff:** no OCR, source-sync/OAuth connector, complete semantic conflict engine, automatic publication or frontend was added. Valid source references establish provenance/format, not semantic entailment; admin and reviewer approvals remain required.

All reproducible failures discovered in the exercised integration paths were fixed and the final suite rerun. This statement does not imply the absence of undiscovered bugs or replace staging/browser verification.

## Team handoff and progress

| Owner | Next responsibility |
|---|---|
| Role B, you | Review this combined backend, run the local smoke test, assess AI output quality on additional agreed examples, and assess remaining analysis/evaluation cases |
| Role A | Review the DB adapter/migration and transition gates; configure the shared test/staging database, real users, deployment and job operation |
| Frontend team | Connect to the API using FRONTEND_INTEGRATION.md; test all three role screens, exact Unicode highlighting, polling/failed states, evidence drawers, candidate approvals and pending version IDs |

The previous Role B estimate was 86%; verified database/API integration brought it to 94%, and successful standalone plus actual API AI verification bring the indicative estimate to **98%**. Remaining shared work is actual frontend/browser and staging acceptance, with continued assessment of known analysis limits. This percentage describes milestones for the current backend scope, not test accuracy or an exact fraction of development time.
