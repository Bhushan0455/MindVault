import { createMockSubmissions } from '../mocks/reviewer-queue';
import { mockContentCheck } from '../mocks/content-check';
import type { ContentDraft } from '../types/content-check';
import type { QueueSubmission } from '../types/reviewer-queue';
import type { ReviewDecision, ReviewDecisionRequest, ReviewHistoryEvent, SubmissionReview, SubmittedRevision } from '../types/reviewer-detail';
import { createReviewFindings, mockReviewerName, reviewAssetsFor, seedReviewDraft } from '../mocks/reviewer-detail';

function freezeTree<T>(value: T): T {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(freezeTree);
    Object.freeze(value);
  }
  return value;
}

function sameContent(a: Readonly<ContentDraft>, b: Readonly<ContentDraft>) {
  return (Object.keys(a) as (keyof ContentDraft)[]).every((key) => a[key] === b[key]);
}

function revisionFor(item: QueueSubmission, number: number): SubmittedRevision {
  const draft = seedReviewDraft(item);
  return freezeTree({ id: `${item.id}:r${number}`, submissionId: item.id, number, submittedAt: item.submittedAt, snapshot: { title: item.title, campaign: item.campaign, brand: item.brand, contentCheckPath: item.contentCheckPath, creator: structuredClone(item.submittedBy), content: draft, assets: reviewAssetsFor(item) }, findings: createReviewFindings(item, draft), status: item.status });
}

function submittedEvent(revision: SubmittedRevision): ReviewHistoryEvent {
  return { id: `${revision.id}:submitted`, submissionId: revision.submissionId, revisionId: revision.id, revisionNumber: revision.number, kind: 'submitted', actor: revision.snapshot.creator.name, at: revision.submittedAt, comment: 'Submitted demo snapshot for review.' };
}

export function createMockSessionStore(initial = createMockSubmissions()) {
  const reviews = new Map<string, SubmissionReview>();
  let records: readonly QueueSubmission[] = freezeTree(structuredClone(initial).map((item) => {
    let revision = revisionFor(item, 1);
    const events = [submittedEvent(revision)];
    if (item.status !== 'pending') {
      const decision: ReviewDecision = { id: `${revision.id}:decision`, submissionId: item.id, revisionId: revision.id, kind: item.status, reviewer: mockReviewerName, comment: item.status === 'changes-requested' ? item.summary : 'Sample approval supplied with the queue fixture.', decidedAt: item.approvedAt ?? item.submittedAt };
      revision = freezeTree({ ...revision, decision });
      events.push({ id: decision.id, submissionId: item.id, revisionId: revision.id, revisionNumber: 1, kind: decision.kind, actor: decision.reviewer, at: decision.decidedAt, comment: decision.comment });
    }
    reviews.set(item.id, freezeTree({ submissionId: item.id, currentRevisionId: revision.id, revisions: [revision], events }));
    return { ...item, revisionId: revision.id, draft: structuredClone(revision.snapshot.content) };
  }));
  const listeners = new Set<() => void>();
  return {
    getSnapshot: () => records,
    getReview(id: string): SubmissionReview | null { const review = reviews.get(id); return review ? structuredClone(review) : null; },
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    getCreatorDraft(id: string): ContentDraft | undefined {
      const draft = records.find((item) => item.sourceDraftId === id && item.origin === 'creator-demo')?.draft;
      return draft ? structuredClone(draft) : undefined;
    },
    recordSubmission(draft: ContentDraft, now = Date.now()) {
      const existing = records.find((item) => item.sourceDraftId === draft.id);
      const review = existing ? reviews.get(existing.id) : undefined;
      const previous = review?.revisions.find((revision) => revision.id === review.currentRevisionId);
      if (previous && sameContent(previous.snapshot.content, draft)) {
        if (previous.status === 'pending') return;
        throw new Error('This revision has already completed review. Edit the working copy before submitting a new revision.');
      }
      const submission: QueueSubmission = {
        id: existing?.id ?? `SUB-${draft.id}`, sourceDraftId: draft.id, contentCheckPath: '/content-checks',
        title: draft.title, campaign: mockContentCheck.campaign, assetDescription: 'Submitted draft snapshot',
        brand: 'Aura Audio', submittedBy: { name: mockContentCheck.creator, team: 'Growth Mktg', initials: 'PR' },
        channel: draft.channel, region: draft.region, submittedAt: now,
        status: 'pending', severity: 'none', statusLabel: 'Ready for Review',
        summary: 'Creator submitted a rechecked demo draft. Awaiting reviewer sign-off; no real compliance assessment.',
        draft: structuredClone(draft), origin: 'creator-demo', simulated: true,
      };
      const revision = revisionFor(submission, (previous?.number ?? 0) + 1);
      const severity = revision.findings.some((item) => item.severity === 'blocker') ? 'blocker' : revision.findings.some((item) => item.severity === 'advisory') ? 'advisory' : 'none';
      reviews.set(submission.id, freezeTree({ submissionId: submission.id, currentRevisionId: revision.id, revisions: [...(review?.revisions ?? []).map((item) => item.status === 'pending' ? { ...item, status: 'superseded' as const } : item), revision], events: [...(review?.events ?? []), submittedEvent(revision)] }));
      records = freezeTree([{ ...submission, revisionId: revision.id, severity }, ...records.filter((item) => item.sourceDraftId !== draft.id)]);
      listeners.forEach((listener) => listener());
    },
    decide(request: ReviewDecisionRequest, now = Date.now()): SubmissionReview {
      const review = reviews.get(request.submissionId);
      if (!review) throw new Error('Submission not found. Return to the queue and select an available item.');
      if (review.currentRevisionId !== request.revisionId) throw new Error('A newer revision was submitted. Reload the current revision before deciding.');
      const revision = review.revisions.find((item) => item.id === request.revisionId)!;
      if (revision.status !== 'pending' || revision.decision) throw new Error('This revision has already completed review. Repeated decisions are not allowed.');
      if (request.kind !== 'approved' && request.kind !== 'changes-requested') throw new Error('Unknown review decision.');
      const comment = request.comment.trim();
      if (request.kind === 'changes-requested' && !comment) throw new Error('Enter a reviewer comment before requesting changes.');
      if (request.kind === 'approved' && revision.findings.some((item) => item.severity === 'blocker')) throw new Error('Resolve the sample blocker in a new Creator revision before approval.');
      const decision: ReviewDecision = { id: `${revision.id}:decision`, submissionId: request.submissionId, revisionId: revision.id, kind: request.kind, comment, reviewer: mockReviewerName, decidedAt: now };
      const decidedRevision = freezeTree({ ...revision, status: decision.kind, decision });
      const nextReview: SubmissionReview = freezeTree({ ...review, revisions: review.revisions.map((item) => item.id === revision.id ? decidedRevision : item), events: [...review.events, { id: decision.id, submissionId: request.submissionId, revisionId: revision.id, revisionNumber: revision.number, kind: decision.kind, actor: decision.reviewer, at: now, comment }] });
      reviews.set(request.submissionId, nextReview);
      records = freezeTree(records.map((item) => item.id !== request.submissionId ? item : { ...item, status: decision.kind, statusLabel: decision.kind === 'approved' ? 'Approved' : 'Changes Requested', summary: comment || 'Demo reviewer approved this specific revision snapshot.', approvedAt: decision.kind === 'approved' ? now : undefined }));
      listeners.forEach((listener) => listener());
      return structuredClone(nextReview);
    },
  };
}

export type MockSessionStore = ReturnType<typeof createMockSessionStore>;
export const mockSessionStore = createMockSessionStore();
