# MindVault AI — integrated local project

Built by **Team Phantoms**, SIES Graduate School of Technology. [Original project introduction](docs/ORIGINAL_PROJECT_README.md).

GitHub delivery includes the prebuilt frontend in `frontend/dist`. Rebuild with `npm ci` and `npm run build` when changing frontend source. The verification package manifest records the original ZIP delivery; this repository adds publication notes.

This combines the creator/reviewer React frontend, the admin prototype's workflows and the integrated Role A + Role B backend. The supplied originals are preserved outside this checkout. The admin HTML reference is retained in `design_reference/`; the active website is `frontend/src/LiveApp.tsx`.

**Full-project completion estimate: 90%. Role B backend estimate: 98%.** These are engineering estimates against the supplied hackathon scope, not percentages calculated from passing tests. Core workflows and local integration are implemented; real-document acceptance, a complete browser walkthrough and deployment remain. See `PROJECT_STATUS.md`.

## Start the website on Windows

From this folder in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\Start_MindVault.ps1
```

Open **http://127.0.0.1:8010**. The one server serves both the built React website and `/api`. Stop it with Ctrl+C. Existing backend services on port 8000 can stay running. If 8010 is occupied, use `-Port 8011` and open that port instead.

The first run needs Python 3.12 or 3.14 and internet access to install the locked Python dependencies. It creates `backend/.venv`, a private `backend/.env` and a local SQLite database. The ZIP contains the built website, so Node is only needed when changing the frontend. This workspace already has private settings; they are excluded from the shareable ZIP. Your friends' copies create their own settings and databases.

On a copy that already has an environment, install updates with:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
```

## Try the demo and then your own documents

1. Choose **Continue as admin**. Fictional Veyra starter documents, rules, facts and demo accounts are intentional, as requested. Activity counts come from stored records, and the creator/reviewer queue begins empty.
2. Open Content Checks as creator/admin. Use the explicit fictional demo-text button, then save/check, inspect sources, accept or edit fixes, apply/recheck and submit. Accepting a fix alone does not alter the draft.
3. Sign out and continue as reviewer. Open the submitted version, inspect findings and discussion, then approve that exact revision or request changes with a comment.
4. For your own-document test, create a **separate brand** from Overview first. Upload a text-based PDF, DOCX or TXT (5 MiB default), extract, review each candidate's meaning/scope/dates and approve it. Add omitted facts/rules manually. Set the corresponding brand, product, market and publication date in the draft. This keeps fictional knowledge separate from your real material.
5. Use Settings as admin to create named creator/reviewer accounts for friends. They can use ordinary email/password sign-in. Demo shortcuts remain available while `DEMO_MODE=true`.

## Connect AI privately

```powershell
.\Start_MindVault.ps1 -SetupAI
```

Enter your Gemini key at the hidden prompt and the exact model ID supported by your account. The key stays in your private `backend/.env`, never in frontend files. This account previously verified `gemini-3.6-flash`; availability can change. Restart an already-running server after configuration changes. Settings/health show configuration; each actual review/job shows whether AI completed or fallback was used.

The final live check retained AI content findings and clarity proposals. Extraction received Google HTTP503 errors and fell back; all three services passed in the prior backend fixture. See `verification/` and `PROJECT_STATUS.md`. These small checks do not establish general accuracy.

## Develop or rebuild the frontend

Use Node 22.12+ (Node24 was used here). In `frontend`:

```powershell
npm ci
npm test
npm run build
```

Restart the server after rebuilding. For live frontend development, start the backend on8010 and run `npm run dev` in `frontend`; open5174. Vite proxies `/api` to8010. No key belongs in a `VITE_` variable.

Backend tests, from `backend` with its environment active:

```powershell
python -m pytest tests integration_tests -q
```

Tests use disposable databases. PostgreSQL-only checks require `MINDVAULT_TEST_POSTGRES_DSN` pointing to a dedicated test server. The generated `backend/verification/openapi.json` documents the final API. Inherited backend documents describe the earlier handoff; the root README, feature matrix and status report describe this final integration.

## Team ownership

| Role | Responsibility now |
|---|---|
| Backend A | Runtime, database, accounts/permissions, uploads/jobs, API availability and hosted configuration |
| Backend B (you) | Deterministic checks, AI adapters/validation, context selection, source evidence, safe fixes and review accuracy |
| Frontend creator/reviewer | Draft editor, inspector, queue, exact-revision decisions, history/diffs and browser testing |
| Frontend admin | Knowledge library, upload/extraction review, rules/facts, clarity, dashboard and team/settings flows |

Do the acceptance walkthrough together using `ACCEPTANCE_CHECKLIST.md`. Keep demo mode for this local test; an externally hosted private workspace needs named accounts, `DEMO_MODE=false`, a private database, HTTPS and deployment configuration.
