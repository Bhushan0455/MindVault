import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createMockSessionStore } from './mock-session-store';
import { createMockReviewerQueueService } from './mock-reviewer-queue-service';
import { createMockContentCheckService, simulateCheck } from './mock-content-check-service';
import { mockContentCheck } from '../mocks/content-check';

describe('Creator to Reviewer handoff (in-memory services only)', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('publishes the exact checked snapshot, updates the existing row and preserves it across route loads', async () => {
    const store = createMockSessionStore();
    const creator = createMockContentCheckService(store);
    const reviewer = createMockReviewerQueueService(store);
    const listener = vi.fn();
    const unsubscribe = reviewer.subscribe(listener);
    const draft = { ...mockContentCheck.draft, title: 'Creator edited launch', channel: 'Instagram Story', language: 'Hindi (IN)', promotion: 'Introductory price ₹999. Limited sample offer.' };
    const submitted = creator.submit(draft, simulateCheck(draft), 'default');
    await vi.runAllTimersAsync(); await submitted;
    const pendingLoad = reviewer.load('default');
    await vi.runAllTimersAsync();
    const records = await pendingLoad;
    expect(records).toHaveLength(19);
    const row = records.find((item) => item.sourceDraftId === draft.id)!;
    expect(row).toMatchObject({ id: 'REV-2024-884', title: draft.title, channel: draft.channel, status: 'pending', severity: 'none', origin: 'creator-demo', draft });
    expect(row.submittedBy.name).toBe(mockContentCheck.creator);
    expect(listener).toHaveBeenCalledOnce();
    draft.promotion = 'Changed after submission';
    expect(row.draft?.promotion).toBe('Introductory price ₹999. Limited sample offer.');
    const contentLoad = creator.load('default'); await vi.runAllTimersAsync();
    expect((await contentLoad)?.draft.promotion).toBe(row.draft?.promotion);
    const repeated = creator.submit(row.draft!, simulateCheck(row.draft!), 'default'); await vi.runAllTimersAsync(); await repeated;
    expect(store.getSnapshot().filter((item) => item.sourceDraftId === draft.id)).toHaveLength(1);
    unsubscribe();
  });

  it('does not enqueue failed, unresolved or stale submissions', async () => {
    const store = createMockSessionStore([]);
    const creator = createMockContentCheckService(store);
    const fixed = { ...mockContentCheck.draft, promotion: '₹999' };
    const stale = simulateCheck(fixed);
    const failed = expect(creator.submit(fixed, stale, 'error')).rejects.toThrow('simulated service'); await vi.runAllTimersAsync(); await failed;
    const blocked = expect(creator.submit(mockContentCheck.draft, simulateCheck(mockContentCheck.draft), 'default')).rejects.toThrow('Resolve'); await vi.runAllTimersAsync(); await blocked;
    const changed = expect(creator.submit({ ...fixed, title: 'Changed' }, stale, 'default')).rejects.toThrow('Recheck'); await vi.runAllTimersAsync(); await changed;
    expect(store.getSnapshot()).toEqual([]);
  });

  it('preserves session data through empty/error previews and inserts new draft IDs', async () => {
    const store = createMockSessionStore([]);
    const reviewer = createMockReviewerQueueService(store);
    const creator = createMockContentCheckService(store);
    const draft = { ...mockContentCheck.draft, id: 'CHK-NEW', promotion: 'Sample ₹999' };
    const submitted = creator.submit(draft, simulateCheck(draft), 'default'); await vi.runAllTimersAsync(); await submitted;
    const empty = reviewer.load('empty'); await vi.runAllTimersAsync(); expect(await empty).toEqual([]);
    const failed = expect(reviewer.load('error')).rejects.toThrow('simulated queue service'); await vi.runAllTimersAsync(); await failed;
    expect(store.getSnapshot()).toHaveLength(1);
    const loaded = reviewer.load('default'); await vi.runAllTimersAsync(); const result = await loaded;
    expect(result[0].draft).toEqual(draft);
    result[0].draft!.title = 'Mutated response';
    expect(store.getSnapshot()[0].draft?.title).toBe(draft.title);
  });
});
