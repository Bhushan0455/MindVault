import { describe, expect, it } from 'vitest';
import { createMockSessionStore } from './mock-session-store';
import { createMockReviewerDetailService } from './mock-reviewer-detail-service';
import { mockContentCheck } from '../mocks/content-check';

function setup() {
  const store = createMockSessionStore([]);
  const draft = { ...mockContentCheck.draft, promotion: mockContentCheck.draft.promotion.replace('₹799', '₹999') };
  store.recordSubmission(draft);
  const id = store.getSnapshot()[0].id;
  const review = store.getReview(id)!;
  return { store, draft, id, revisionId: review.currentRevisionId, service: createMockReviewerDetailService(store, 0) };
}

describe('Revision-specific review decisions (mock services only)', () => {
  it('approves the exact revision and records its reviewer comment, timestamp and history event', async () => {
    const { store, id, revisionId, service } = setup();
    const before = store.getReview(id)!.revisions[0].snapshot;
    const reviewed = await service.decide({ submissionId: id, revisionId, kind: 'approved', comment: '  Copy reviewed for the demo.  ' }, 'default');
    expect(reviewed.revisions[0]).toMatchObject({ id: revisionId, status: 'approved', snapshot: before, decision: { revisionId, submissionId: id, kind: 'approved', comment: 'Copy reviewed for the demo.' } });
    expect(reviewed.revisions[0].decision?.decidedAt).toBeTypeOf('number');
    expect(reviewed.events.at(-1)).toMatchObject({ revisionId, kind: 'approved', comment: 'Copy reviewed for the demo.' });
    expect(store.getSnapshot()[0]).toMatchObject({ status: 'approved', revisionId, approvedAt: reviewed.revisions[0].decision?.decidedAt });
  });

  it('requires a trimmed comment and persists changes requested against that revision', async () => {
    const { store, id, revisionId, service } = setup();
    await expect(service.decide({ submissionId: id, revisionId, kind: 'changes-requested', comment: ' \n\t ' }, 'default')).rejects.toThrow('reviewer comment');
    expect(store.getReview(id)?.events).toHaveLength(1);
    expect(store.getSnapshot()[0].status).toBe('pending');
    const updated = await service.decide({ submissionId: id, revisionId, kind: 'changes-requested', comment: '  Add the offer end date.  ' }, 'default');
    expect(updated.revisions[0].decision).toMatchObject({ revisionId, kind: 'changes-requested', comment: 'Add the offer end date.' });
    expect(store.getSnapshot()[0]).toMatchObject({ status: 'changes-requested', summary: 'Add the offer end date.' });
  });

  it('prevents repeated or conflicting decisions, including simultaneous requests', async () => {
    const { store, id, revisionId, service } = setup();
    const results = await Promise.allSettled([
      service.decide({ submissionId: id, revisionId, kind: 'approved', comment: 'First decision' }, 'default'),
      service.decide({ submissionId: id, revisionId, kind: 'changes-requested', comment: 'Second decision' }, 'default'),
    ]);
    expect(results.filter((item) => item.status === 'fulfilled')).toHaveLength(1);
    expect(results.filter((item) => item.status === 'rejected')).toHaveLength(1);
    expect(store.getReview(id)!.events.filter((event) => event.kind !== 'submitted')).toHaveLength(1);
    await expect(service.decide({ submissionId: id, revisionId, kind: 'approved', comment: '' }, 'default')).rejects.toThrow('already completed');
  });

  it('keeps approved snapshots immutable and creates a pending revision for changed Creator content', async () => {
    const { store, id, revisionId, service, draft } = setup();
    await service.decide({ submissionId: id, revisionId, kind: 'approved', comment: 'Approved original copy' }, 'default');
    const original = store.getReview(id)!.revisions[0];
    expect(() => { store.getSnapshot()[0].draft!.title = 'Accidental direct mutation'; }).toThrow(TypeError);
    const response = await service.load(id, 'default');
    Object.assign(response!.revisions[0].snapshot.content, { title: 'Response-only mutation' });
    expect(store.getReview(id)!.revisions[0]).toEqual(original);
    const workingCopy = store.getCreatorDraft(draft.id)!;
    workingCopy.title = 'An edited next revision';
    expect(store.getReview(id)!.revisions[0]).toEqual(original);
    store.recordSubmission(workingCopy);
    const next = store.getReview(id)!;
    expect(next.revisions).toHaveLength(2);
    expect(next.revisions[0]).toEqual(original);
    expect(next.revisions[1]).toMatchObject({ number: 2, status: 'pending', snapshot: { content: workingCopy } });
    expect(next.revisions[1].decision).toBeUndefined();
    expect(store.getSnapshot()[0]).toMatchObject({ status: 'pending', revisionId: next.currentRevisionId });
    expect(store.getSnapshot()[0].approvedAt).toBeUndefined();
    expect(next.events.map((event) => event.kind)).toEqual(['submitted', 'approved', 'submitted']);
  });

  it('rejects stale confirmations and leaves a newer submitted revision undecided', async () => {
    const { store, id, revisionId, service, draft } = setup();
    store.recordSubmission({ ...draft, title: 'New revision arrived while reviewing' });
    await expect(service.decide({ submissionId: id, revisionId, kind: 'approved', comment: '' }, 'default')).rejects.toThrow('newer revision');
    const review = store.getReview(id)!;
    expect(review.revisions[0].status).toBe('superseded');
    expect(review.revisions[1].status).toBe('pending');
    expect(review.revisions.every((item) => !item.decision)).toBe(true);
  });

  it('blocks unresolved sample blockers and disallows reopening a completed unchanged snapshot', async () => {
    const store = createMockSessionStore();
    const service = createMockReviewerDetailService(store, 0);
    const review = store.getReview('REV-2024-884')!;
    await expect(service.decide({ submissionId: review.submissionId, revisionId: review.currentRevisionId, kind: 'approved', comment: '' }, 'default')).rejects.toThrow('sample blocker');
    const ready = setup();
    await ready.service.decide({ submissionId: ready.id, revisionId: ready.revisionId, kind: 'approved', comment: '' }, 'default');
    expect(() => ready.store.recordSubmission(ready.draft)).toThrow('already completed');
    expect(ready.store.getSnapshot()[0].status).toBe('approved');
  });

  it('handles unavailable records and simulated failures without writing a decision', async () => {
    const { service, store, id, revisionId } = setup();
    expect(await service.load('missing', 'default')).toBeNull();
    expect(await service.load(id, 'empty')).toBeNull();
    await expect(service.load(id, 'error')).rejects.toThrow('simulated review service');
    await expect(service.decide({ submissionId: id, revisionId, kind: 'approved', comment: 'Keep this note' }, 'error')).rejects.toThrow('could not be saved');
    expect(store.getReview(id)!.events).toHaveLength(1);
    expect(store.getSnapshot()[0].status).toBe('pending');
  });
});
