import { describe, expect, it } from 'vitest';
import { createMockSessionStore } from '../../services/mock-session-store';
import { mockContentCheck } from '../../mocks/content-check';
import { buildMilestones, defaultMilestone, defaultVersionPair } from './journey-model';
import { diffText } from './text-diff';

describe('Revision Journey data and comparison (local fixtures only)', () => {
  it('derives the roadmap from preserved snapshots and recorded decisions without inventing timestamps', () => {
    const store = createMockSessionStore();
    const draft = { ...mockContentCheck.draft, promotion: mockContentCheck.draft.promotion.replace('₹799', '₹999') };
    store.recordSubmission(draft);
    let review = store.getReview('REV-2024-884')!;
    store.decide({ submissionId: review.submissionId, revisionId: review.currentRevisionId, kind: 'changes-requested', comment: 'Clarify the end date.' });
    store.recordSubmission({ ...draft, title: 'Revised headline' });
    review = store.getReview('REV-2024-884')!;
    store.decide({ submissionId: review.submissionId, revisionId: review.currentRevisionId, kind: 'approved', comment: 'Approved this version.' });
    review = store.getReview('REV-2024-884')!;
    const before = structuredClone(review);
    const milestones = buildMilestones(review);
    expect(new Set(milestones.map((event) => event.kind))).toEqual(new Set(['draft-created', 'ai-check', 'finding-detected', 'revision-created', 'rechecked', 'submitted', 'changes-requested', 'approved']));
    for (const event of review.events) expect(milestones.find((item) => item.id === event.id)).toMatchObject({ source: 'recorded', occurredAt: event.at, revisionId: event.revisionId, comment: event.comment });
    expect(milestones.filter((event) => event.source === 'snapshot').every((event) => event.occurredAt === undefined && event.snapshotAt !== undefined)).toBe(true);
    expect(defaultMilestone(milestones)).toMatchObject({ kind: 'revision-created', revisionNumber: 3 });
    expect(review).toEqual(before);
  });

  it('uses recorded workflow milestones when supplied and handles an empty journal', () => {
    const store = createMockSessionStore();
    const review = store.getReview('REV-2024-884')!;
    const revision = review.revisions[0];
    const event = { id: 'recorded-check', submissionId: review.submissionId, revisionId: revision.id, revisionNumber: 1, kind: 'ai-check' as const, actor: 'Demo check', at: revision.submittedAt - 1000, comment: 'Recorded mock check' };
    const events = buildMilestones({ ...review, events: [event, ...review.events] });
    expect(events.filter((item) => item.kind === 'ai-check')).toEqual([expect.objectContaining({ id: 'recorded-check', occurredAt: event.at, source: 'recorded' })]);
    expect(buildMilestones({ ...review, events: [] })).toEqual([]);
    expect(defaultVersionPair(review.revisions, 'unavailable')).toEqual([revision.id, 'unavailable']);
    expect(defaultVersionPair([], undefined)).toEqual(['', '']);
  });

  it('highlights removed and added price/content while retaining exact whitespace and Unicode', () => {
    const before = 'Price ₹799.\n Keep  this text.';
    const after = 'Price ₹999.\n Keep  this text. Added!';
    const changes = diffText(before, after);
    expect(changes.filter((part) => part.kind !== 'added').map((part) => part.text).join('')).toBe(before);
    expect(changes.filter((part) => part.kind !== 'removed').map((part) => part.text).join('')).toBe(after);
    expect(changes.some((part) => part.kind === 'removed' && part.text.includes('₹799.'))).toBe(true);
    expect(changes.some((part) => part.kind === 'added' && part.text.includes('₹999.'))).toBe(true);
    expect(diffText('same', 'same')).toEqual([{ kind: 'equal', text: 'same' }]);
    expect(diffText('', 'new')).toEqual([{ kind: 'added', text: 'new' }]);
    expect(diffText('old', '')).toEqual([{ kind: 'removed', text: 'old' }]);
  });

  it('bounds large comparisons without losing source text', () => {
    const before = `Prefix ${'old '.repeat(700)}Suffix`;
    const after = `Prefix ${'new '.repeat(700)}Suffix`;
    const changes = diffText(before, after);
    expect(changes.filter((part) => part.kind !== 'added').map((part) => part.text).join('')).toBe(before);
    expect(changes.filter((part) => part.kind !== 'removed').map((part) => part.text).join('')).toBe(after);
  });
});
