// @vitest-environment jsdom
// DOM and in-memory service tests only. Native dialog focus/rendering is unverified.
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { App } from '../../App';
import { createMockSessionStore } from '../../services/mock-session-store';
import { createMockReviewerDetailService } from '../../services/mock-reviewer-detail-service';
import { createMockReviewerQueueService } from '../../services/mock-reviewer-queue-service';
import { createMockContentCheckService } from '../../services/mock-content-check-service';
import { mockContentCheck } from '../../mocks/content-check';

beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value() { this.setAttribute('open', ''); } });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value() { this.removeAttribute('open'); this.dispatchEvent(new Event('close')); } });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
function LocationProbe() { return <output data-testid="path">{useLocation().pathname}</output>; }

function setup(path = '/approvals/REV-2024-884', prepare?: (store: ReturnType<typeof createMockSessionStore>) => void) {
  const store = createMockSessionStore();
  store.recordSubmission({ ...mockContentCheck.draft, title: 'Submitted reviewer snapshot', promotion: mockContentCheck.draft.promotion.replace('₹799', '₹999') });
  prepare?.(store);
  const service = createMockReviewerDetailService(store, 0);
  const queueService = createMockReviewerQueueService(store, 0);
  const contentService = createMockContentCheckService(store);
  render(<MemoryRouter initialEntries={[path]}><App reviewService={service} queueService={queueService} contentService={contentService} /><LocationProbe /></MemoryRouter>);
  return { store, service, user: userEvent.setup() };
}

describe('Reviewer Detail interactions (local mock/DOM validation)', () => {
  it('opens the matching route from the queue and inspects revision-specific source evidence', async () => {
    const { user } = setup('/approvals?status=pending');
    await user.click(await screen.findByRole('link', { name: 'Submitted reviewer snapshot' }));
    await screen.findByRole('heading', { name: 'Submitted reviewer snapshot' });
    expect(screen.getByTestId('path').textContent).toBe('/approvals/REV-2024-884');
    const paper = screen.getByRole('article', { name: 'Submitted content revision' });
    expect(paper.textContent).toContain(mockContentCheck.creator);
    expect(paper.textContent).toContain(mockContentCheck.draft.audience);
    expect(paper.textContent).toContain('Aura Audio');
    const copy = screen.getByRole('region', { name: 'Exact submitted copy' });
    expect(copy.textContent).toContain('₹999'); expect(copy.textContent).not.toContain('₹799');
    await user.click(within(copy).getByRole('button', { name: 'Inspect evidence for ₹999' }));
    const drawer = screen.getByRole('dialog', { name: 'Verification & Audit Ledger' });
    expect(drawer.textContent).toContain('Simulated findings for revision v2');
    expect(drawer.textContent).toContain(mockContentCheck.source.quote);
    await user.click(within(drawer).getByRole('button', { name: 'Close verification & audit ledger' }));
    expect(screen.queryByRole('dialog', { name: 'Verification & Audit Ledger' })).toBeNull();
  });

  it('requires confirmation, approves the captured revision and updates queue status', async () => {
    const { user, store } = setup();
    await screen.findByRole('heading', { name: 'Submitted reviewer snapshot' });
    const expectedRevision = store.getReview('REV-2024-884')!.currentRevisionId;
    await user.type(screen.getByRole('textbox', { name: 'Reviewer comment' }), 'Reviewed this exact copy.');
    await user.click(screen.getAllByRole('button', { name: 'Approve Revision v2' })[0]);
    let confirmation = screen.getByRole('dialog', { name: 'Confirm revision approval' });
    expect(store.getSnapshot()[0].status).toBe('pending');
    await user.click(within(confirmation).getByRole('button', { name: 'Cancel' }));
    expect(store.getSnapshot()[0].status).toBe('pending');
    await user.click(screen.getAllByRole('button', { name: 'Approve Revision v2' })[0]);
    confirmation = screen.getByRole('dialog', { name: 'Confirm revision approval' });
    expect(confirmation.textContent).toContain(expectedRevision);
    await user.click(within(confirmation).getByRole('button', { name: 'Confirm approval' }));
    await screen.findByText('Revision approved in this demo session. The queue status has been updated.');
    expect(screen.getAllByRole('button', { name: 'Approve Revision v2' }).every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
    const revision = store.getReview('REV-2024-884')!.revisions.find((item) => item.id === expectedRevision)!;
    expect(revision.decision).toMatchObject({ revisionId: expectedRevision, kind: 'approved', comment: 'Reviewed this exact copy.' });
    await user.click(screen.getByRole('link', { name: 'Back to Reviewer Queue' }));
    const table = await screen.findByRole('table');
    const row = within(table).getByRole('link', { name: 'Submitted reviewer snapshot' }).closest('tr')!;
    expect(row.textContent).toContain('Approved');
  });

  it('rejects empty comments, then requests changes and stores the relevant comment', async () => {
    const { user, store } = setup();
    await screen.findByRole('heading', { name: 'Submitted reviewer snapshot' });
    await user.click(screen.getAllByRole('button', { name: 'Request Changes' })[0]);
    expect(screen.getByRole('alert').textContent).toContain('Enter a reviewer comment');
    expect(document.activeElement).toBe(screen.getByRole('textbox', { name: 'Reviewer comment' }));
    expect(store.getSnapshot()[0].status).toBe('pending');
    await user.type(screen.getByRole('textbox', { name: 'Reviewer comment' }), '   ');
    await user.click(screen.getAllByRole('button', { name: 'Request Changes' })[0]);
    expect(screen.getByRole('alert')).toBeTruthy();
    await user.type(screen.getByRole('textbox', { name: 'Reviewer comment' }), 'Add the offer end date.');
    await user.click(screen.getAllByRole('button', { name: 'Request Changes' })[0]);
    await screen.findByText('Changes requested. Your comment is saved with this revision and visible in the queue.');
    const review = store.getReview('REV-2024-884')!;
    expect(review.events.at(-1)).toMatchObject({ revisionId: review.currentRevisionId, kind: 'changes-requested', comment: 'Add the offer end date.' });
    expect(screen.getAllByRole('button', { name: 'Request Changes' }).every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
    await user.click(screen.getByRole('link', { name: 'Back to Reviewer Queue' }));
    const row = (await screen.findByRole('link', { name: 'Submitted reviewer snapshot' })).closest('tr')!;
    expect(row.textContent).toContain('Changes Requested'); expect(row.textContent).toContain('Add the offer end date.');
  });

  it('preserves the approved earlier revision while a changed revision awaits a new decision', async () => {
    let approvedId = '';
    const { user, store } = setup('/approvals/REV-2024-884', (session) => {
      const review = session.getReview('REV-2024-884')!; approvedId = review.currentRevisionId;
      session.decide({ submissionId: review.submissionId, revisionId: approvedId, kind: 'approved', comment: 'Original approved copy' });
      session.recordSubmission({ ...session.getCreatorDraft(mockContentCheck.draft.id)!, title: 'New copy awaiting review' });
    });
    await screen.findByRole('heading', { name: 'New copy awaiting review' });
    await user.selectOptions(screen.getByRole('combobox', { name: 'Submitted revision' }), approvedId);
    expect(screen.getByRole('heading', { name: 'Submitted reviewer snapshot' })).toBeTruthy();
    expect((screen.getByRole('textbox', { name: 'Reviewer comment' }) as HTMLTextAreaElement).disabled).toBe(true);
    expect(screen.getAllByRole('button', { name: 'Approve Revision v2' }).every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
    expect(store.getReview('REV-2024-884')!.revisions.find((item) => item.id === approvedId)).toMatchObject({ status: 'approved', snapshot: { content: { title: 'Submitted reviewer snapshot' } }, decision: { comment: 'Original approved copy' } });
    expect(store.getSnapshot()[0].status).toBe('pending');
  });

  it('preserves a reviewer comment on save failure and allows retrying the decision', async () => {
    const { user, service, store } = setup();
    await screen.findByRole('heading', { name: 'Submitted reviewer snapshot' });
    vi.spyOn(service, 'decide').mockRejectedValueOnce(new Error('Simulated decision save failed'));
    await user.type(screen.getByRole('textbox', { name: 'Reviewer comment' }), 'Keep this required comment');
    await user.click(screen.getAllByRole('button', { name: 'Request Changes' })[0]);
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Simulated decision save failed'));
    expect((screen.getByRole('textbox', { name: 'Reviewer comment' }) as HTMLTextAreaElement).value).toBe('Keep this required comment');
    expect(store.getSnapshot()[0].status).toBe('pending');
    await user.click(screen.getAllByRole('button', { name: 'Request Changes' })[0]);
    await screen.findByText('Changes requested. Your comment is saved with this revision and visible in the queue.');
  });

  it('discards an open confirmation when a newer submitted revision arrives', async () => {
    const { user, store } = setup();
    await screen.findByRole('heading', { name: 'Submitted reviewer snapshot' });
    await user.click(screen.getAllByRole('button', { name: 'Approve Revision v2' })[0]);
    expect(screen.getByRole('dialog', { name: 'Confirm revision approval' })).toBeTruthy();
    act(() => { store.recordSubmission({ ...store.getCreatorDraft(mockContentCheck.draft.id)!, title: 'Replacement revision needs a new review' }); });
    await screen.findByRole('heading', { name: 'Replacement revision needs a new review' });
    expect(screen.queryByRole('dialog', { name: 'Confirm revision approval' })).toBeNull();
    const review = store.getReview('REV-2024-884')!;
    expect(review.revisions.every((revision) => !revision.decision)).toBe(true);
    expect(review.revisions.at(-1)?.status).toBe('pending');
    expect(screen.getAllByRole('button', { name: 'Approve Revision v3' })).toHaveLength(2);
  });

  it('supports loading, empty and error previews without changing the stored revision', async () => {
    const { user, store } = setup();
    expect(screen.getByRole('heading', { name: 'Loading submitted revision' })).toBeTruthy();
    await screen.findByRole('heading', { name: 'Submitted reviewer snapshot' });
    const before = store.getReview('REV-2024-884');
    await user.click(screen.getByLabelText('Profile and demo controls'));
    await user.selectOptions(screen.getByRole('combobox', { name: 'Preview state' }), 'empty');
    await screen.findByRole('heading', { name: 'Submission not found' });
    await user.selectOptions(screen.getByRole('combobox', { name: 'Preview state' }), 'error');
    await screen.findByRole('heading', { name: 'Could not load Reviewer Detail' });
    expect(screen.getByRole('alert').textContent).toContain('simulated review service');
    await user.click(screen.getByRole('button', { name: 'Return to Default' }));
    await screen.findByRole('heading', { name: 'Submitted reviewer snapshot' });
    expect(store.getReview('REV-2024-884')).toEqual(before);
  });
});
