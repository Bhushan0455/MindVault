> Original project introduction, preserved from main before the final integration. Current setup and status are in the root README and PROJECT_STATUS.

# MindVault AI

**Check it before the world sees it.**

MindVault AI is a pre-publication brand-governance platform for organisations. Content goes in, it is checked against the organisation's approved guidelines, facts and terms, every issue is explained with its evidence, and a **human makes the final decision**.

Built by **Team Phantoms** (SIES Graduate School of Technology) for the Inkloom AI brand-governance hackathon, Round 2.

| | |
|---|---|
| Live app | `[TO FILL: frontend URL]` |
| API docs | `[TO FILL: backend URL]/docs` |
| Repository | `[TO FILL: GitHub URL]` |

> The demo uses **fictional data only** (brand "Veyra Audio"). Do not enter real confidential content.

---

## Try it in 3 minutes (judge path)

No signup is needed. Open the live app and use the demo buttons.

1. Click **Try as Admin** → open **Knowledge**. The sample guideline and fact sheet are already loaded. You can also upload the sample guideline and approve the extracted rules.
2. Click **Try as Creator** → **New content** → **Use sample draft A** (a headphones ad priced at ₹799) → **Check content**.
3. Open the findings. The ₹799 price is flagged against the approved ₹999 with its source document and page. Accept the suggested fix → **Apply accepted fixes** → the re-check comes back clean → **Submit for review**.
4. Click **Try as Reviewer** → open the item in the queue → **Approve**. The approval is bound to the exact revision you reviewed.
5. Open **History** to see the revision diff, the approval record and the audit log.

If the app has been idle it may take up to a minute to wake up (free hosting).

---

## What it does

- **Knowledge repository.** Upload guideline and fact documents (PDF, DOCX, TXT). AI proposes rules and facts with their source page. Nothing becomes active until a person approves it.
- **Context-aware review.** Each draft is checked with its context (brand, product, channel, audience, region, content type, campaign, date). Only the rules that apply are used, and the app shows which rules applied or were skipped and why.
- **Evidence-backed findings.** Each finding has a category, severity, a separate confidence value, the exact quoted text, the rule or fact it relies on (with source and page), a plain explanation and a suggested fix. Unverifiable claims are labelled "not substantiated in the approved sources", never "false". There is no opaque compliance score.
- **Human decisions.** Creators accept, edit or reject each finding. Reviewers approve or request changes on a specific revision. Approvals are immutable.
- **Audit trail.** Revisions, diffs, decisions and AI calls are recorded.

### The three improvements we named in Round 1

1. **Zero-migration onboarding with governed updates.** Start by uploading documents; no migration project. A simulated connected source detects changed documents and proposes rule or fact updates for approval. *(Round 3: real Google Drive connector and automatic re-review when an approved fact changes.)*
2. **Context-Aware Brand Brain.** Rules are scoped by channel, audience, region and more, and ordered by authority. The same text gets different results on Instagram and in an investor deck.
3. **Guideline Clarity Auditor.** Finds vague or incomplete rules (for example "Headlines should be short"), explains why they cause inconsistent decisions and proposes clearer wording and examples.

### Feature status

See [FEATURES.md](./FEATURES.md) for the honest, current status of every feature (Done / Partial / Simulated / Not started).

---

## How a review works

```mermaid
flowchart LR
  A[Draft + context] --> B[Resolve applicable rules]
  B --> C[Deterministic checks<br/>facts, prices, terms,<br/>required text, superlatives]
  C --> D[Gemini analysis<br/>tone, claim meaning,<br/>terminology]
  D --> E[Validator<br/>quote exists, cited IDs exist,<br/>low confidence -> needs review]
  E --> F[Findings with evidence]
  F --> G[Creator decides] --> H[Reviewer approves exact revision]
```

Deterministic checks run first and do not need AI. If Gemini is unavailable or rate-limited, the review still completes with rule-based findings and the UI says so.

## Architecture

```mermaid
flowchart TB
  U[Browser] --> FE[Frontend<br/>React + TypeScript + Tailwind]
  FE -- REST + JWT --> API[FastAPI backend]
  API --> DB[(PostgreSQL)]
  API -- redacted prompts --> G[Google Gemini API]
  API --> BG[Background tasks<br/>extraction, review runs]
```

- **Frontend:** React, TypeScript, Tailwind CSS (deployed separately). Talks to the backend only through `src/lib/api.ts`.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL. A modular monolith with background tasks.
- **AI:** Google Gemini API via the `google-genai` SDK, with schema-constrained JSON output, temperature 0, retries, caching and a validator on every AI finding.
- **Documents:** PyMuPDF (PDF), python-docx (DOCX).
- **Security:** JWT auth with roles (admin, creator, reviewer); every query is scoped to the user's organisation from the token.

## Repository layout

```
backend/    FastAPI app, models, services (extraction, checks, review engine, validator), tests
frontend/   React app
seed/       Script that generates the fictional demo guideline (PDF) and fact sheet (DOCX)
scripts/    smoke.py - end-to-end check against any deployed URL
```

---

## Run locally

Requirements: Python 3.12, Node 20+, PostgreSQL (or Docker).

### 1. Database
```bash
docker compose up -d db        # or use any Postgres, e.g. a free Neon/Supabase project
```

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env                                # then edit values
uvicorn app.main:app --reload --port 8000
```
The first start creates the tables and loads the demo data. Open http://localhost:8000/docs.

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env     # VITE_API_BASE_URL=http://localhost:8000/api , VITE_USE_MOCK=false
npm run dev
```

### Environment variables

Backend (`.env`):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | e.g. `postgresql+psycopg://user:pass@host:5432/db` (add `?sslmode=require` for hosted databases) |
| `JWT_SECRET` | Long random string |
| `GEMINI_API_KEY` | From Google AI Studio. Optional: without it the app runs rule-based only |
| `GEMINI_MODEL` | A current Gemini model id from the Google AI docs |
| `DEMO_MODE` | `true` enables one-click demo logins |
| `ALLOWED_ORIGINS` | Comma-separated frontend URLs for CORS |
| `MAX_UPLOAD_MB` | Upload limit (default 5) |

Frontend (`.env`):

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend base URL, for example `https://your-api.onrender.com/api` |
| `VITE_USE_MOCK` | `true` uses built-in fictional mock data; must be `false` in production |

Never commit secrets. `.env` is git-ignored.

## Tests

```bash
cd backend && pytest                       # unit tests: checks, validator, context resolution, workflow rules, org isolation
python scripts/smoke.py https://your-api   # full demo path on a deployed backend
```

## Deployment

- **Backend + database:** Docker image on Render (or Railway/Fly) with a managed PostgreSQL (Neon or Supabase, used only as Postgres). Set the environment variables above.
- **Frontend:** deployed as a standalone site with `VITE_API_BASE_URL` pointing to the backend and `VITE_USE_MOCK=false`.
- Free tiers sleep when idle; the app shows a "waking up" screen on first load.

## API overview

All endpoints are under `/api` and documented interactively at `/docs`. Main groups: auth, brands, documents, rules, facts, content and revisions, review runs, findings decisions, approvals and queue, comments, insights, audit, sources.

## Data, privacy and AI use

- Demo data is fictional. The database holds organisation data separated by `org_id`.
- Only the draft, applicable rules and relevant approved facts are sent to Gemini. Emails and phone numbers are redacted first. Each AI call is logged (purpose and model, not content).
- Gemini's free tier may use inputs to improve Google products. That is why the demo must only use fictional data.
- AI output is a suggestion. People make every final decision.
- Full list of AI tools, libraries and templates used: [DISCLOSURES.md](./DISCLOSURES.md).

## Changes from the Round 1 plan

See [CHANGES_FROM_PLAN.md](./CHANGES_FROM_PLAN.md).

## Roadmap (Round 3)

- Real read-only Google Drive connector with scheduled sync.
- Automatic re-review when an approved fact changes (₹999 → ₹1,099 flags the approved post that used ₹999, keeps its earlier approval record and leaves unaffected posts current).
- Conflict detection between rules, effective-date and exception handling.
- Semantic retrieval ranking, contradiction detection in the Clarity Auditor, image/poster checks.

## Team Phantoms

| Member | Focus |
|---|---|
| Tanish Gondhalekar | Product, documentation, submission, demo |
| Likhit Rane | Frontend and interaction design |
| Bhushan Parab | Backend, approval workflow, deployment |
| Sharanya Chakraborty | AI prompts, evidence verification, test data and evaluation |

Each member's actual contributions are listed in DISCLOSURES.md and match the commit history.

## Licence

`[TO FILL: choose a licence or state "All rights reserved - hackathon submission"]`
