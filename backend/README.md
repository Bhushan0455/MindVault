# MindVault: integrated Role A + Role B backend

This is the combined backend. Role A's authentication, database, revisions, approvals, comments and audit routes now call Role B's tested analysis services. Work from **this folder**, which contains `app/`, `requirements-lock.txt` and this README. There is no additional `backend/` directory inside it.

Verified on 6 November 2026 with CPython 3.12 and the user's Python 3.14 environment, PostgreSQL 16.15 and isolated SQLite databases. The detailed results and remaining limits are in [INTEGRATION_REPORT.md](INTEGRATION_REPORT.md). Role B progress is approximately **98%**, a milestone estimate. All three AI services now pass through the running API using fictional fixtures. The actual frontend and hosted deployment still need acceptance tests. See [AI_VERIFICATION_UPDATE.md](AI_VERIFICATION_UPDATE.md).

## Start a local demo in PowerShell

Open a terminal in this folder. These commands create a private environment and a fresh local demo database; PostgreSQL installation is optional for this first run.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m scripts.configure_local
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The tested Python versions are 3.12 and the user's 3.14 environment. If you have several Python versions, use `py -3.12 -m venv .venv` to match the Docker version. The user's Python 3.14 environment also passed the SQLite regression suite.

Open [the API documentation](http://localhost:8000/docs). Local React/Vite may use `VITE_API_BASE_URL=http://localhost:8000/api`. Login through `POST /api/auth/demo?role=admin`, `creator` or `reviewer`; use the returned token as `Authorization: Bearer <token>`.

The configuration helper generates a random JWT secret, enables fictional demo accounts, and creates `.env` only if none exists. Local data is stored in `mindvault_local.sqlite`. Normal startup never rewrites existing demo knowledge. Never copy a teammate's `.env.local` or database credentials into this folder unintentionally: `.env.local` overrides `.env`; explicit process environment variables override both.

In another terminal, run the fictional journey against your local demo:

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke http://127.0.0.1:8000
```

This creates a fictional draft, applies safe fixes, rechecks it, records explicit risk acknowledgements, submits it and approves that exact revision using the demo reviewer. It checks the stored source too. It requires demo mode and a loopback address.

## Use PostgreSQL

Set `DATABASE_URL` in your own `.env` to your local/test PostgreSQL or Neon connection string. Both `postgres://` and `postgresql://` are normalized to the psycopg driver. Keep your JWT secret and `DEMO_MODE=true` for an isolated demo. To use the included Docker setup, first generate `.env` with the configuration helper, then run `docker compose up --build`. Compose overrides `DATABASE_URL` to its own PostgreSQL service. Docker itself was unavailable here, so the image and compose deployment were not executed; the same API was tested directly against PostgreSQL.

**For an existing Role A database**, make a database backup or use a test copy first. Configure that copy's URL, then run:

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate_role_a
```

This additive upgrade preserves documents, content, revisions, approvals and audit rows; adds snapshots, qualifiers, jobs and candidates; widens audit IDs; converts PostgreSQL fact values to `NUMERIC(16,2)`; and adds unique revision numbers. It refuses duplicate revision numbers. Existing review runs without historical evidence snapshots become `legacy` and require a fresh review before applying fixes or submitting. Historical approval rows remain preserved. Existing source references are not replaced by invented document links. The exact supplied demo CLAIM-01 instruction is mapped to the explicit claim-evidence flag. Other custom claim rules require admin review of that flag. Run migrations with the old server stopped; then start this API. Startup detects missing integration columns and reports the migration command.

## How the connected workflow works

1. Admin uploads PDF, DOCX or TXT. Text extraction preserves actual PDF pages, DOCX paragraphs/table cells, and TXT lines.
2. Admin requests extraction, polls its job, reviews pending candidates, and confirms market, dates, scope and other required fields before approving knowledge.
3. Creator saves content and context, requests a review, and polls the review run. Context selection, prices, battery life, warranty, terminology, disclaimers and claim evidence use Role B services. Admins can manage a product catalogue and aliases through `/api/products`; aliases preserve attribution in multi-product drafts. Facts entered with an alias are stored under the canonical name. The API also enables narrow explicit emoji/exclamation constraints from applicable approved tone rules.
4. Findings contain exact original-text spans, source snapshots and rule/fact versions. Creator decisions are saved separately from text changes. Accepting a fix does not modify the draft or unblock an unchanged high-risk finding.
5. Applying accepted/edited fixes creates revision N+1 atomically and starts its review. Overlap, stale spans, insertion collisions and stale hashes reject the entire batch. Empty edited text means deletion.
6. Submit requires a completed review of the current revision and no unresolved critical/high findings. A creator may explicitly reject a finding with a reason; the reviewer sees those risk decisions. Accepted/edited high-risk fixes must be applied and rechecked.
7. Reviewer approval binds the exact revision ID and body hash. Later edits create a new unapproved draft. If knowledge changes after review, submission/approval requires another review. The knowledge fingerprint is conservative: even a new pending item for that brand requires rechecking.

Rules and facts are versioned. `PATCH` creates a **new pending row with a new ID**, preserving the old approved row until the replacement is approved. Approving a replacement supersedes its approved ancestor. Competing versions cannot both supersede the same current version. Clarity rewrites also create pending versions; their proposed numbers/criteria require human review.

## Frontend handoff

Use [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md), [frontend/mindvault-client.ts](frontend/mindvault-client.ts), and the exported [OpenAPI contract](verification/openapi.json). Core Role A routes and nested `rule`/`fact` responses remain available. New routes, intentional validation changes and Unicode offset conversion are documented there. No frontend application was included in the handoff, so browser layouts, highlighting and website-to-API integration have not been tested.

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pytest tests integration_tests -q
.\.venv\Scripts\python.exe -m evaluation.run_evaluation
```

API tests always create a disposable SQLite database, ignoring your normal `DATABASE_URL`. To exercise PostgreSQL transactions, point the **test variable** below to an isolated local test server whose user may create schemas. The tests create and drop a random schema, preserving other schemas.

```powershell
$env:MINDVAULT_TEST_POSTGRES_DSN="postgresql+psycopg://test_user:password@127.0.0.1:5432/test_database?connect_timeout=5"
.\.venv\Scripts\python.exe -m pytest tests integration_tests -q
Remove-Item Env:MINDVAULT_TEST_POSTGRES_DSN
```

The PostgreSQL run passed 370 tests (318 existing + 51 integration + one extraction-limit regression test). SQLite runs on Python 3.12 and 3.14 passed 367 with three PostgreSQL concurrency tests skipped. Pytest additionally records 63 unittest subtests. The synthetic evaluation remains 30/30 baseline and 17/20 challenge exact matches; this is development evidence, not independent accuracy validation.

## Optional Gemini

Set `GEMINI_API_KEY`, an account-accessible `GEMINI_MODEL`, and `ENABLE_SEMANTIC=true` privately on the server, then restart. No model is hardcoded. This enables all three adapters: content review, knowledge extraction, and clarity. Configuration is loaded from `.env` for the transport adapters too. The key is never returned to the browser.

Deterministic checks remain available when Gemini fails. UI notices must show `ai_used`, `ai_status`, `issues` and extraction `method`. Provider metadata is audited; raw prompts, response bodies and exception text are not persisted in AI audit events. The optional service cache is independently tested but not enabled in these API routes.

The schema adjustment was confirmed by the user's live extraction retry: five pending candidates, zero validation issues. All three services were subsequently verified through the local running API: seven pending extraction candidates, one retained AI content finding alongside the deterministic price check, and two pending AI clarity proposals. The HTTP client did not read the Gemini key; the API used its own private configuration. See AI_VERIFICATION_UPDATE.md and verification/live-api-ai.json. These are fixture-level smoke checks, not independent quality certification. Health now reports ai_verification_scope=per_service_result instead of the misleading hardcoded live_ai_verified=false field. Restart the server once to load that health response change.

## Deployment boundary

Background tasks run in this API process. Use one API worker for the hackathon build. Polling marks interrupted queued/running jobs failed after 180 seconds, and timed-out jobs cannot later replace their terminal result. This is not a durable distributed queue: retries create a new run/job. Extraction candidates are deduplicated by source-derived IDs.

For a public service, provision real users, disable demo mode, use PostgreSQL and HTTPS, restrict origins, add operational rate limits/monitoring and a durable job worker. Demo password login is disabled when demo mode is off. Production hosting, an actual browser UI, OAuth/source-sync connectors, OCR, full semantic rule conflict resolution and publication integrations are outside this delivery. Citation validation establishes provenance and format; admins/reviewers still assess meaning and correctness.
