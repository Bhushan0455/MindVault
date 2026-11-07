> Historical backend handoff reference. For the final connected website, current test results and launch instructions, use ../README.md and ../PROJECT_STATUS.md.

# Connect the frontend to the integrated API

Base URL: `http://localhost:8000/api`. Send `Authorization: Bearer <token>` on protected requests. `POST /auth/demo?role=creator|admin|reviewer` returns `{token,user}` in demo mode. `POST /auth/login` accepts `{email,password}`. `GET /me` returns identity. Health flags describe configuration; ai_verification_scope="per_service_result" means review/job responses describe whether AI actually ran. The former hardcoded live_ai_verified=false field has been removed; do not use health as an AI certification.

## Creator and reviewer screens

| Screen/action | Request | Important response/behavior |
|---|---|---|
| Brand selector | `GET /brands` | Organisation-scoped IDs and names |
| New draft | `POST /content` | `brand_id,title,body_text,context`; returns content/current_revision |
| Save edit | `POST /content/{id}/revisions` | Send `expected_revision_id`; creates new revision, clears latest run/approval state. Omitted context preserves previous context |
| Start check | `POST /content/{id}/review` | HTTP 202 `{run_id}` |
| Poll results | `GET /review-runs/{run_id}` | `status,progress_step,ai_used,ai_status,issues,applied_rules,skipped_rules,findings` |
| Source drawer | `GET /sources/{document_id}?location=line%201` | Actual stored source blocks and extraction offsets. Manual-source IDs have no uploaded document |
| Finding action | `POST /findings/{id}/decision` | `{action:"accept"}` / `{action:"edit",edited_text:"..."}` / `{action:"reject",note:"reason"}` |
| Apply decisions | `POST /content/{id}/apply-fixes` | `{content,run_id}`; poll new run before submitting |
| Revision history | `GET /content/{id}/revisions/{number}` | Original revision text/hash/context |
| Diff | `GET /content/{id}/diff?from=1&to=2` | Unified text diff |
| Submit | `POST /content/{id}/submit` | Current review and high-risk gate |
| Reviewer queue | `GET /queue` | Includes finding counts and explicit risk decisions |
| Approve/request changes | `POST /content/{id}/approve` or `/request-changes` | `{revision_id,comment?}`; approval stores exact revision/hash |
| Discussion | `GET/POST /content/{id}/comments` | POST `{body,revision_id?,finding_id?}`; references must belong to that content/revision |
| Admin reporting | `GET /audit`, `GET /insights` | Scoped audit and counts |

The `context` fields remain `product,channel,audience,region,content_type,campaign,publication_date`. Date is ISO `YYYY-MM-DD`; default is today's date. Unknown context/content fields now return 422 so spelling mistakes cannot silently select the wrong scope.

Poll every 1–2 seconds. Stop on `done`, `failed`, or `legacy`; show retry/recheck instructions for the latter two. Jobs expire after 180 seconds when polled; put a bounded timeout on frontend polling as well. Do not label a review approved because its findings array is empty.

Findings retain nested `rule:{id,code,version,instruction}` and `fact:{id,version,value,source_document,location,page}` when applicable. `page` is set only for an actual stored PDF page; TXT/DOCX use `location` and `source`. Price findings now use category `price`, battery `battery_life`, and warranty `warranty`; they are no longer incorrectly grouped under `claims`.

`source:{document_id,document_title,location,excerpt}` is the authoritative snapshot for the finding. Show `severity,confidence,verdict,explanation,suggested_fix` and the persisted decision separately. Supported/info findings are evidence dependencies and cannot be accepted as fixes. `suggested_fix=null` means no replacement. An edited empty string explicitly deletes a span.

## Admin knowledge and clarity screens

| Action | Request | Result |
|---|---|---|
| Upload | `POST /documents` multipart `file,brand_id,kind` | PDF/DOCX/TXT, default 5 MiB file cap, bounded request body |
| Documents | `GET /documents`, `GET /documents/{id}` | Stored metadata/text |
| Extract | `POST /documents/{id}/extract` | **202 `{job_id,status,document_id}`**, replacing the old empty placeholder |
| Extraction progress | `GET /jobs/{job_id}` | Terminal `done/failed`; result contains method, issues and candidate IDs |
| Candidate list | `GET /documents/{id}/candidates` | Pending/approved/rejected rows, original payload and precise source |
| Confirm candidate | `POST /candidates/{id}/approve` | `{knowledge:{...complete RuleIn or FactIn...}}`; confirms and approves in one transaction |
| Reject candidate | `POST /candidates/{id}/reject` | Explicit persisted rejection |
| Manual rules/facts | `GET/POST /rules`, `GET/POST /facts` | Typed fields in OpenAPI; new rows are pending |
| Product catalogue | `GET/POST /products`, `PATCH /products/{id}` | Admin creates `{brand_id,name,aliases}`; PATCH updates `{aliases}`. Scoped GET lists managed products; canonical names remain stable |
| Edit knowledge | `PATCH /rules/{id}`, `PATCH /facts/{id}` | Returns **new pending ID/version**; update frontend selected row |
| Approve/reject | `POST /rules/{id}/approve|reject`, `/facts/{id}/approve|reject` | Admin only, pending rows only |
| Clarity audit | `POST /brands/{brand_id}/clarity` | Completed persisted job with pending proposals and AI status |
| Create rewrite | `POST /clarity/{job_id}/accept` | `{proposal_id,instruction}` creates pending rule version, requiring separate approval |

Candidate approval requires a complete `knowledge` object, not just the candidate payload. Confirm `brand_id`, rule `code/instruction/category/severity/authority/scopes`, or fact `product/attribute/value_text/value_num/unit/market/qualifier/dates`. Source reference is taken from the saved candidate, not browser-supplied evidence. A missing market is rejected. Rule scope arrays and dates need explicit human assessment; empty scope arrays mean general applicability. Set `requires_claim_evidence=true` on a rule intended to enforce approved superlative claim wording.

Example numeric candidate approval:

```json
{"knowledge":{"brand_id":"<brand-id>","product":"Veyra Beat 200","attribute":"price","value_text":"₹999","value_num":999,"unit":"INR","market":"IN","qualifier":"exact","valid_from":"2026-10-01"}}
```

Supported numeric attributes/units are `price/INR`, `battery_life/hours`, and `warranty/years|months`; claim evidence uses `attribute:"claim"` with an exact approved sentence in `value_text`. Numeric amounts are stored as fixed decimal values. A new fact created separately can conflict with an existing approved fact: the checker reports ambiguity. To replace a fact intentionally, use its PATCH/version/approve lifecycle.

Clarity limits/examples are proposals rather than extracted truths. Display `assumptions` and `requires_completion`; require the admin to confirm the completed instruction. If its structured enforcement fields also change, edit those fields on the pending version before approving it. A stale or already accepted proposal returns 409.

## Offset conversion and errors

Finding offsets use Unicode code points, start inclusive/end exclusive. JavaScript indexes use UTF-16 units. Use `Array.from(text)` or the helper in `frontend/mindvault-client.ts`; a leading emoji must not shift the highlighted price. Empty quote at `start=end=text_length` represents a missing-disclaimer insertion. Source block offsets refer to extracted document text, not the draft.

Errors are `{code,detail}` with an appropriate HTTP status. Handle 401 by logging in, 403 by hiding/disabling unavailable actions, 404 as unavailable resources, 409 by refreshing the current revision/knowledge, 413 as upload/request size limits, and 422 as invalid fields. `knowledge_changed` means recheck before submitting; if already in the reviewer queue, request changes and recheck. Low/medium findings may remain open for reviewer assessment; high/critical accepted or edited fixes remain blocking until applied and reviewed. Rejecting a warning requires a reason and leaves a visible risk decision. `dismiss` is limited to supported/info findings.

This delivery provides API verification and a TypeScript helper. Actual React rendering, role navigation and website integration still require your frontend team's browser tests.
