# Team acceptance walkthrough

Run on localhost. Demo data is intentional and labelled. These manual acceptance steps remain to be completed by the team; automated results are in `verification/`.

1. Open8010, sign in using admin/creator/reviewer shortcuts, verify each role's visible navigation and a refresh/deep link. Check narrow mobile and desktop layouts, keyboard focus and dialogs.
2. As admin, create a separate brand and real team accounts. Upload your agreed PDF/DOCX/TXT. Compare displayed source text and locations against the original document. Scanned/image-only PDF is outside OCR scope.
3. Extract knowledge. Inspect the reported AI/fallback method. Verify every retained candidate's meaning, market, scope, validity dates and citation before approval. Reject incorrect candidates; manually add omissions. Repeat extraction when Google is available if it returned503.
4. Add aliases, version a rule/fact, and confirm a pending replacement does not become active before approval. Audit ambiguous rules and review a proposed pending rewrite.
5. As creator, choose that brand/product/context and enter a deliberately wrong price plus a policy violation. Verify source-backed findings and a clean supported value. Wrong market/product/date and missing evidence must not be treated as a clean result.
6. Accept/edit fixes. Confirm acceptance alone does not submit; apply them, inspect the new revision, and wait for its recheck. Test rejection with a reason. Submit the intended saved version.
7. As reviewer, inspect the actual submitted copy, sources, decisions and comments. Request changes with a comment; creator edits/rechecks/resubmits. Approve the exact corrected version.
8. Edit an approved item again. Confirm the new draft is unapproved, the old approval retains its text/hash, and the approved queue row opens its original approved revision. Compare both versions in history.
9. Check saved state after refresh/sign-out/sign-in, permissions for another creator, and clear feedback when the backend/provider is unavailable. Test two tabs saving different revisions: the stale tab must preserve its text and report a conflict.
10. Record actual document-review errors and expected results with Backend B. Passing a small AI smoke test is not an accuracy evaluation. Only after acceptance, prepare hosted database, HTTPS, named accounts, demo-disabled configuration and deployment smoke checks.

Browser automation was stopped with Escape during this task. Browser visual/layout checks have not been certified; component tests and real API/asset requests were completed separately.
