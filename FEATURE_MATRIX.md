# Backend features exposed in the final website

The active entry uses real HTTP services. The original mock App and tests remain as regression fixtures; they are not a fallback for a failed live request.

| Workflow | Frontend integration | Backend connection |
|---|---|---|
| Identity | Login, demo roles, first-workspace setup, sign-out | `/auth/login`, `/auth/demo`, `/setup`, `/me` |
| Team | Admin creates real hashed-password accounts; role-specific navigation | `/team`; every protected API enforces organisation and roles |
| Brands | Real brand selection and separate new brands | `/brands` |
| Overview | Selected-brand counts/activity and organisation insights | `/content`, `/documents`, `/rules`, `/facts`, `/insights` |
| Library/sources | Actual stored text, document hash, uploader and exact cited location | `/documents`, `/documents/{id}`, `/sources/{id}` |
| Upload | PDF/DOCX/TXT upload with file-size/type feedback | `POST /documents` |
| Extraction | Start/poll jobs, AI/fallback labels, pending candidate review, edit/approve/reject | `/documents/{id}/extract`, `/jobs/{id}`, `/documents/{id}/candidates`, `/candidates/{id}/approve|reject` |
| Rules | Create/edit new versions, authority, severity, priority, scope, dates, terminology/disclaimer/claim settings and sources | `/rules`, PATCH, approve/reject |
| Facts | Price/battery/warranty/claim facts, product/market, units, qualifiers, dates and source | `/facts`, PATCH, approve/reject |
| Products | Canonical product names and aliases | `/products`, PATCH |
| Clarity | Actual audit, evidence, examples/assumptions, human-completed pending rewrite | `/brands/{id}/clarity`, `/clarity/{job}/accept` |
| Creator | Save/list/load drafts and new immutable revisions, context controls, explicit revision-conflict error | `/content`, `/content/{id}/revisions` with expected revision |
| Content review | Start/poll run, actual findings, Unicode-correct spans, applied/skipped rules, AI status/issues | `/content/{id}/review`, `/review-runs/{id}` |
| Finding decisions | Accept, edited replacement including deletion, rejection with reason, acknowledge supported | `/findings/{id}/decision` |
| Safe fixes | Apply accepted fixes into a new snapshot and poll recheck | `/content/{id}/apply-fixes` |
| Submission | Current-review/high-risk gate; accepted fixes remain blocking until applied | `/content/{id}/submit` |
| Queue | Actual submitted/decided snapshots, filters, CSV labelled persisted | `/submissions` (extends the original `/queue` view) |
| Reviewer | Review the selected snapshot; confirm approval or request changes with comment | `/content/{id}/approve|request-changes`, revision/hash enforced |
| History/diff | Actual immutable titles/text/context/hashes/decisions and recorded milestones; client comparison of those snapshots | `/content/{id}/history`; individual revision and unified diff API also retained |
| Discussion | Persisted per-revision comments with account names | `/content/{id}/comments` |
| Audit | Scoped event list and metadata-only AI-call records | `/audit` |
| Evaluation | Saved synthetic deterministic evaluation report, explicitly labelled | `/evaluation` |
| Runtime | Configuration/AI-enabled state and real error feedback | `/health`; actual service results determine AI use |

Language is saved as draft metadata; it is not an additional rule-scope dimension. Matching uses product/channel/audience/region/content type/campaign/publication date as supported by the backend.

Prototype-only concepts without backend support are not presented as working features: external source sync, OCR for scanned PDFs, OAuth/SSO, attached creative-asset analysis, dual-signature overrides and publishing connectors. They are optional future scope. This implementation reviews document text and draft text; ordinary source-backed review/approval is implemented.
