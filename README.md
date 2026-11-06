# MindVault AI frontend

React, TypeScript, Vite, Tailwind CSS and React Router. Implemented screens: Creator Content Check, Reviewer Queue, Reviewer Detail and Revision Journey, using the shared application shell.

## Run locally

Use Node.js 22.12+ and npm. Node 22.13.1 was used for this change.

```sh
npm ci
npm run dev
```

Open the Local URL printed by Vite (normally http://127.0.0.1:5173). Refresh and direct navigation to `/content-checks` work under Vite. Static production hosting must rewrite application paths to `index.html`.

The Reviewer Queue is at `/approvals` and uses the same sidebar and header.

Reviewer Detail is at `/approvals/:submissionId`; submission links navigate to this route.

Revision Journey is at `/content/:contentId/history`. Content IDs may be Creator draft IDs (such as `CHK-9042`) or submission IDs (such as `REV-2024-884`). The history adapter resolves them using existing queue data, then loads the existing review history.

```sh
npm run typecheck
npm run build
npm test
npm run verify
```

`verify` runs TypeScript, a production build and mock unit tests, saving an immutable timestamped manifest and individual logs in `reports/`. It records service call counts, external-service cost, cache state and live-validation status. Agent billing is unavailable and recorded as unknown. Dependency downloads are setup activity, not product service calls.

Some restricted Windows environments deny esbuild child processes (`spawn EPERM`); those build/test commands need an execution environment that allows local compiler processes.

## Design source

The final approved references are in `design_reference/` (an underscore, rather than `design-reference/`). All five HTML exports in `design_reference/html/` and all five PNGs in `design_reference/screenshots/` were inspected. No separate design-system documentation was supplied. The four application HTML exports share the same color tokens; the login export uses a separate slate/blue sign-in treatment. The references remain unchanged.

`design_reference/html/contentcheck.html` is the source for this page's layout and tokens. Its matching screenshot is `design_reference/screenshots/contentcheck.png`. Layout uses the HTML's CSS dimensions: 256px sidebar, 56px header, 384px desktop inspector, 64px horizontal editor gutters, 48px canvas padding, 24px headline, 15px reading text and compact 11–12px controls. The screenshots appear to use larger raster scales (the Content Check sidebar is 320 image pixels versus 256 CSS pixels); they are not treated as literal CSS sizes. Inter and JetBrains Mono remain bundled locally. Lucide supplies equivalent icons.

Reconciliation corrected the extra action/demo rows, header hierarchy, sidebar navigation spacing and active state, approval counter, brand mark, metadata truncation, pill controls, inspector proportions, canvas spacing, text emphasis, underlined claims, price highlight, finding card and bottom action bar. Page actions render into the shared header through `ShellHeader`; demo state controls are under **Profile and demo controls**. The edit action is the pencil beside the draft filename. The Guidelines button opens the existing sample source disclosure.

Responsive adaptations wrap metadata and actions at narrower widths. Mobile navigation retains its native dialog with Escape support, a focus trap and focus restoration; the inspector becomes an inline section. The references do not include mobile screenshots. Visual reconciliation is based on the supplied HTML and screenshots; browser rendering and pixel-diff verification have not been completed because the available Windows browser was blocked by Computer Use URL-policy enforcement in the earlier session.

Deliberate demo differences: engine status and saved-state text identify session-only mocks instead of claiming a live engine or autosave; both submission buttons remain guarded; Quick Fix still requires a recheck; Ctrl/Cmd + S still saves the draft, so its hint says "save". Initials stand in for the export's remote/broken profile image. No source PDF was supplied, so the source disclosure labels the excerpt as a sample. These do not imply real compliance validation.

The Reviewer Queue follows `design_reference/html/reiviewerapprovalpage.html` and `design_reference/screenshots/reviwerqueue.png`, preserving their original filenames. Its overview metrics, segmented controls, search/filter rows, submission table, pagination and policy callout reuse the approved tokens. Queue styles are scoped in `reviewer-queue.css` to preserve the existing Content Check layout. The full table scrolls horizontally so all status/action columns remain accessible on smaller screens.

The queue defaults to **All Submissions** to display the design's mixed-status example rows honestly; the static export selected Pending while also showing approved and changes-requested rows. All four status controls filter the actual records. Initial fixtures contain 19 submissions: 3 pending, 2 changes requested and 14 approved. Tab counts and urgent counts derive from records. Sprint totals also include explicitly mocked historical metrics. The linked Aura item uses the Content Check fixture's creator, Priyanshi Roy, so ownership is consistent across both screens.

Reviewer Detail follows `design_reference/html/reviewerdetail.html` and `design_reference/screenshots/reviewerdetail.png`: submitted document, creator bar, creative cards and audit thread on the left; ledger summary and decision card on the right; evidence drawer and sticky decision footer. Colors and typography reuse existing tokens. `SourceEvidence` is shared with the original Content Check inspector. The reference's hash, legal-binding notice and verification guarantees are replaced with explicit snapshot-specific demo language. Revision labels derive from actual session records, beginning at v1; they are not hardcoded to the export's v2.3.

Creative cards retain reference metadata, but the image files are not included locally and no remote artwork has been fetched. They show unavailable-file placeholders. Queue fixtures that originally contained only a title now receive fictional copy once at session initialization; this seeded copy becomes their exact submitted snapshot. Creator submissions always preserve their actual submitted text.

## Demo workflow

1. Load `/content-checks`. The sample starts with one ₹799 price conflict.
2. Open or close the Inspector; click the price to reopen it. Expand document specs, sample claims or source rules with keyboard-accessible disclosure controls.
3. Apply Quick Fix (or Ctrl/Cmd + Enter). The sample price changes to ₹999.
4. Recheck. Then Submit for Approval becomes available in both action bars. Successful submission writes a snapshot to the shared in-memory Reviewer Queue and shows a **View Reviewer Queue** link. It contacts no reviewer.
5. Edit draft text or targeting to invalidate the previous result. Recheck again before submitting. Use Save Draft or Ctrl/Cmd + S for a simulated session save.
6. Open the avatar (**Profile and demo controls**) and use **Preview state** for loading transitions, Default, Empty and Error. Changing this selector reloads the current screen and discards unsubmitted edits. Leaving Content Check discards unsaved edits; returning restores the latest submitted snapshot if one exists. A full page reload resets the entire in-memory session. There is no automatic or durable save.

## Reviewer Queue workflow

1. Open **Approvals** (`/approvals`). Search by title, reference ID, Creator draft ID or submitter; Ctrl/Cmd + K focuses search. Combine status, brand, channel and severity filters. Reset clears filters and sorting while retaining the chosen page size.
2. Sort by newest, oldest or conflict level. Pagination follows the filtered dataset, and filter changes return to page 1. Filters, sorting, page size and the selected preview are reflected in the URL and work with browser navigation.
3. Open a title or row action to navigate to **Reviewer Detail** for that submission. The return link preserves queue filters. Older `?submission=...` preview URLs remain supported as read-only previews.
4. The Aura submission links to **Open existing Findings & Evidence**, reusing the Content Check inspector for the current Creator working copy. Reviewer Detail's audit ledger inspects evidence attached to the selected submitted revision; those snapshots may differ from a subsequently edited Creator working copy. Both views share source-excerpt rendering and mock reference data.
5. Select individual rows or the current page. **Export Audit Log** downloads selected submissions across pages, or every filtered submission when nothing is selected, as an explicitly labeled demo CSV. **Queue Settings** changes page size and clears selection. **View Dual-Sign Policy** opens sample guidance; it grants no overrides or publishing permissions.
6. Use the profile's Preview state selector to exercise Loading, Empty and Error states. Empty/error previews do not delete shared session data. Retry repeats the selected scenario; Return to Default restores the session queue.

The Content Check service validates the latest recheck before recording a submission. Submitting changed content creates a new revision under the same queue item instead of duplicating the item. A repeated identical pending submission is idempotent. An unchanged completed revision cannot be reopened by resubmission; the Creator must edit the working copy first. The sidebar approval badge derives from this same store. Browser tabs and full page reloads start independent sessions.

## Reviewer Detail workflow and state

1. Open a submission in Approvals. Metadata includes creator, brand, targeting, submitted time, revision number and review status. The submitted marketing copy is read-only.
2. Open **Audit Ledger**, the rule breakdown or an inline claim to inspect simulated findings, severities, explanations, brand rules and source excerpts. These are fixture associations, not real AI analysis or compliance results.
3. **Approve Revision** opens a confirmation naming the captured revision ID and headline. Cancel leaves state unchanged. Confirm records the decision against that exact current revision. Sample blockers prevent approval; request a corrected Creator revision instead.
4. **Request Changes** requires a non-whitespace reviewer comment. The comment and decision are stored together, and the queue status/summary update immediately in shared memory. Approval comments are optional. Completed reviews disable both decision actions.
5. Use **Submitted revision** to inspect earlier snapshots. Only the latest pending revision can receive a decision. The audit thread shows stored submission/decision events. **Revision Journey** opens the roadmap; **Compare Diff** opens its comparison when an earlier version is available.
6. Creator edits operate on a separate working copy. Submitting changed copy creates a new pending revision. Prior approved content, metadata, evidence and reviewer comments remain preserved. Superseded pending revisions cannot be decided. Approvals never carry over to newer revisions.
7. The profile's Preview state selector exercises loading, empty and error states without deleting records. Failed decisions preserve the entered comment for retry. A stale confirmation cannot approve a newer revision; refresh/current-revision controls recover from conflicts.

Campaign rejection and dual-sign dispatch remain disabled. No signatures, cryptographic verification, regulatory guarantees or actual publishing permissions are produced. The reviewer identity is explicitly a demo fixture, not authentication.

## Revision Journey

The visual references are `design_reference/html/revisionhistory.html` and `design_reference/screenshots/revishionhistory.png`. The page reuses the approved horizontal connected roadmap, event inspector, side-by-side red/green comparison, sidebar and existing tokens. No separate hardcoded timeline or history store was added.

- Open the history icon beside the Content Check filename or **Revision Journey** in Reviewer Detail. Unsaved Creator edits are excluded; the page reads preserved submissions only.
- Click or keyboard-activate milestones to inspect revision, actor/source, comments, timestamps and associated sample finding evidence. Left/right/Home/End keys move roadmap focus. Selected events and comparison versions are reflected in the URL.
- The history model supports draft creation, AI check, finding detection, revision creation, recheck, submission, approval and changes requested. Recorded events retain their exact IDs, revision IDs, comments, actors and timestamps. Existing records contain submissions and decisions; creation/check/finding steps are derived from saved snapshots where a corresponding recorded event is absent. Those steps are explicitly labeled **At submission** and identify that their independent action times were not recorded. An empty journal remains an empty history, even if versions exist.
- **Compare V1 ↔ V2** selects the first two versions. The selectors can compare any two preserved versions. Changed headline/introduction/promotion fields show word/whitespace additions and removals; targeting-only changes are shown separately. Unchanged copy is omitted from the focused diff, with links to the exact full versions. Comparisons preserve original text, whitespace and Unicode; large edits use a bounded comparison fallback.
- Approval milestones and version badges identify the exact approved revision. A later pending revision does not inherit an earlier approval. Viewing/comparing history never edits a snapshot or decision.
- Missing content IDs, empty journals, missing events, unavailable snapshots, single versions, identical selections and service failures have explicit states and recovery controls. Profile Preview state offers Empty history and Error without deleting session data.

The journey uses a read-only `RevisionJourneyService` composed from the existing queue and reviewer-detail adapters. A real adapter can implement the same interface with canonical content-to-submission lookup and recorded workflow events. Derived mock milestones do not claim real AI analysis, independently measured timings or regulatory verification.

No real authentication, backend, API, AI model, database or compliance evaluation exists here. All sample claim statuses are illustrative. The mock recheck only looks for the fixture string `₹799`; removing it is not evidence of real compliance. Service failures remain errors and never become `UNVERIFIABLE` or another verdict. No calibration, thresholds, train/validation/test datasets or real compliance results are involved.

## Architecture

- `src/types/content-check.ts`: UI-facing interfaces and replaceable service contract.
- `src/mocks/`: typed sample content and metadata options.
- `src/services/`: asynchronous in-memory mock adapter and submission guards.
- `src/features/content-check/`: page, inspector and workflow state hook.
- `src/types/reviewer-queue.ts`: submission, filter and replaceable queue-service interfaces.
- `src/features/reviewer-queue/`: queue page, table, read-only preview, pure queries, state hook and scoped styling.
- `src/services/mock-session-store.ts`: shared in-memory submission snapshots; `mock-reviewer-queue-service.ts` exposes the queue through its service contract.
- `src/types/reviewer-detail.ts`: immutable revision, decision, history-event, evidence and detail-service contracts.
- `src/features/reviewer-detail/`: document, revision-specific audit ledger, decision UI, async state and scoped styling.
- `src/services/mock-reviewer-detail-service.ts`: replaceable mock detail adapter; the shared store enforces current-revision, pending-status and comment guards atomically.
- `src/features/revision-journey/`: roadmap, event inspector, comparison, bounded text diff, pure view-model derivation and read-only async state.
- `src/services/revision-journey-service.ts`: composes existing adapters for content lookup and immutable review-history reads; `src/types/revision-journey.ts` defines its replaceable contract.
- `src/components/`: shared shell, navigation, buttons, badges, error boundary and state panel.
- `src/styles.css`: Stitch-derived tokens, Tailwind theme and responsive component styles.

`App.tsx` injects Content Check, queue and review-detail adapters. All default mock adapters share the same in-memory session store. Tests inject adapter factories constructed with the same isolated store. Future API adapters implement `ContentCheckService`, `ReviewerQueueService` and `ReviewerDetailService`; components contain no network calls.

Integration assumptions for the backend teammate: decisions must atomically validate the supplied submission ID, expected revision ID and pending status; derive the reviewer identity/authorization from real authentication; preserve immutable content/evidence/asset revisions; store decision comments and history events; and invalidate the queue snapshot after successful decisions. Human-readable mock revision IDs are not cryptographic hashes. The client guards support the demo but do not replace server-side concurrency, permissions, persistence or validation.

## Validation boundaries

`npm test` runs local unit tests and React Testing Library interactions in jsdom. Queue coverage includes search, combined filters, sorting, pagination, preview opening/closing, selection/export, settings, empty/error states and the Creator-to-Reviewer handoff. Service tests cover snapshot isolation, failed/stale submissions, re-submission deduplication and session preservation. The four original Content Check tests remain unchanged.

Reviewer Detail tests cover opening the corresponding route from the queue, source evidence, explicit approval confirmation, the approved revision ID, required comments, decision failures and retries, immediate queue updates, repeated/concurrent/stale decision rejection, approved-snapshot isolation, new pending revisions after edits, viewing old approved revisions, and stale confirmation dismissal. Existing queue tests were adapted to the new primary navigation while retaining legacy preview coverage.

Revision Journey tests cover recorded versus derived milestones, all supported event kinds, empty journals, exact price/whitespace diffs, large comparisons, milestone selection, keyboard focus movement, V1/V2 and targeting comparisons, exact approval attribution, navigation from both workspaces, missing content/versions/events and history/error previews. Existing store models and fixtures are reused; history rendering is checked for non-mutation of approved snapshots.

jsdom tests polyfill native dialog methods and CSV-download APIs; they do not validate browser rendering, responsive appearance, native focus trapping/restoration, image loading or actual downloaded files. Full browser/end-to-end and backend integration testing is deferred to the user after merging. Passing automated tests does not make this feature fully verified. Future real-service tests must use the separate `*.live.test.ts` marker; the default configuration excludes them. No live service checks have run.

Remaining steps: additional Creator screens, demo login and role switching. No Login or other new screens were implemented in the Revision Journey step. Sidebar destinations other than Content Checks and Approvals display a pending-screen message. Real authentication must remain distinct from eventual demo session controls.
