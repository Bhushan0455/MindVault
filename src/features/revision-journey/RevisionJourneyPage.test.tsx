// @vitest-environment jsdom
// Local DOM/mock checks only. No browser automation or live service validation.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { App } from '../../App';
import { mockContentCheck } from '../../mocks/content-check';
import { createMockSessionStore } from '../../services/mock-session-store';
import { createMockReviewerQueueService } from '../../services/mock-reviewer-queue-service';
import { createMockReviewerDetailService } from '../../services/mock-reviewer-detail-service';
import { createMockContentCheckService } from '../../services/mock-content-check-service';
import type { RevisionJourneyService } from '../../types/revision-journey';

afterEach(cleanup);
function setup(path = '/content/CHK-9042/history', options: { newer?: boolean; journeyService?: RevisionJourneyService } = {}) {
  const store = createMockSessionStore();
  const corrected = { ...mockContentCheck.draft, promotion: mockContentCheck.draft.promotion.replace('₹799', '₹999') };
  store.recordSubmission(corrected);
  const review = store.getReview('REV-2024-884')!;
  store.decide({ submissionId: review.submissionId, revisionId: review.currentRevisionId, kind: 'approved', comment: 'Reviewed the corrected price.' });
  if (options.newer) store.recordSubmission({ ...corrected, title: 'New pending copy', channel: 'Instagram Story' });
  render(<MemoryRouter initialEntries={[path]}><App queueService={createMockReviewerQueueService(store, 0)} reviewService={createMockReviewerDetailService(store, 0)} contentService={createMockContentCheckService(store)} journeyService={options.journeyService} /></MemoryRouter>);
  return { store, user: userEvent.setup() };
}

describe('Revision Journey interactions', () => {
  it('selects milestones, inspects the approved revision and compares V1 with V2 without mutating history', async () => {
    const { user, store } = setup();
    const before = store.getReview('REV-2024-884');
    expect(screen.getByRole('heading', { name: 'Loading Revision Journey' })).toBeTruthy();
    await screen.findByRole('heading', { name: 'Revision Roadmap' });
    expect(screen.getByRole('heading', { name: 'Version Comparison (V1 → V2)' })).toBeTruthy();
    const old = screen.getByRole('article', { name: 'Version 1 before' });
    const updated = screen.getByRole('article', { name: 'Version 2 after' });
    expect(old.querySelector('del')?.textContent).toContain('₹799');
    expect(updated.querySelector('ins')?.textContent).toContain('₹999');
    await user.click(screen.getByRole('button', { name: 'Approved · V2' }));
    expect(screen.getByRole('heading', { name: 'Event Details · Approved (V2)' })).toBeTruthy();
    expect(screen.getAllByText('Reviewed the corrected price.').length).toBeGreaterThan(0);
    expect(screen.getByRole('link', { name: 'View Version 2 Full Content' }).getAttribute('href')).toContain('revision=REV-2024-884%3Ar2');
    const first = within(screen.getByRole('list', { name: 'Revision roadmap' })).getAllByRole('button')[0];
    first.focus(); await user.keyboard('{ArrowRight}');
    expect(document.activeElement).not.toBe(first);
    expect(store.getReview('REV-2024-884')).toEqual(before);
  });

  it('keeps earlier approval distinct from a newer pending revision and compares targeting edits', async () => {
    const { user } = setup('/content/CHK-9042/history', { newer: true });
    await screen.findByRole('heading', { name: 'Revision Roadmap' });
    expect(screen.getByText('Awaiting Review · V3 Current')).toBeTruthy();
    expect(screen.getByText('Approval recorded for V2')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Version Comparison (V2 → V3)' })).toBeTruthy();
    expect(screen.getByRole('article', { name: 'Version 2 before' }).textContent).toContain('Approved · V2');
    expect(screen.getByRole('article', { name: 'Version 3 after' }).textContent).toContain('Pending Review');
    expect(screen.getByRole('heading', { name: 'Targeting changes' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Compare V1 ↔ V2' }));
    expect(screen.getByRole('heading', { name: 'Version Comparison (V1 → V2)' })).toBeTruthy();
  });

  it('recovers from unavailable versions and events without substituting unrelated data', async () => {
    const { user } = setup('/content/CHK-9042/history?event=missing&to=missing');
    await screen.findByRole('heading', { name: 'Revision Roadmap' });
    expect(screen.getByRole('heading', { name: 'Event unavailable' })).toBeTruthy();
    expect(screen.getByText('A comparison version is unavailable. Choose two preserved versions.')).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Reset event selection' }));
    await user.click(screen.getByRole('button', { name: 'Reset comparison' }));
    expect(screen.getByRole('heading', { name: 'Version Comparison (V1 → V2)' })).toBeTruthy();
    await user.selectOptions(screen.getByRole('combobox', { name: 'After version' }), 'REV-2024-884:r1');
    expect(screen.getByText('Select two different versions to compare.')).toBeTruthy();
  });

  it('handles a single preserved version and a missing content ID', async () => {
    const { user } = setup('/content/REV-2024-885/history');
    await screen.findByRole('heading', { name: 'Revision Roadmap' });
    expect(screen.getByText('Only one version is available. Submit an edited revision to compare changes.')).toBeTruthy();
    await user.click(screen.getByRole('link', { name: 'View Review Workspace' }));
    await screen.findByRole('heading', { name: 'Monsoon Soundfest Influencer Brief & Reel Script' });
    cleanup();
    setup('/content/missing/history');
    await screen.findByRole('heading', { name: 'Content history not found' });
  });

  it('handles empty histories and service errors while retaining the shared snapshots', async () => {
    const { user, store } = setup();
    await screen.findByRole('heading', { name: 'Revision Roadmap' });
    const before = store.getReview('REV-2024-884');
    await user.click(screen.getByLabelText('Profile and demo controls'));
    await user.selectOptions(screen.getByRole('combobox', { name: 'Preview state' }), 'empty');
    await screen.findByRole('heading', { name: 'No history events yet' });
    await user.selectOptions(screen.getByRole('combobox', { name: 'Preview state' }), 'error');
    await screen.findByRole('heading', { name: 'Could not load revision history' });
    await user.click(screen.getByRole('button', { name: 'Return to Default' }));
    await screen.findByRole('heading', { name: 'Revision Roadmap' });
    expect(store.getReview('REV-2024-884')).toEqual(before);
  });

  it('navigates from Reviewer Detail and Content Check into the shared history', async () => {
    const { user } = setup('/approvals/REV-2024-884');
    await screen.findByRole('heading', { name: 'Silence the noise. Elevate your everyday rhythm.' });
    await user.click(screen.getByRole('link', { name: 'Revision Journey' }));
    await screen.findByRole('heading', { name: 'Revision Roadmap' });
    expect(screen.getByRole('heading', { name: 'Event Details · Approved (V2)' })).toBeTruthy();
    cleanup();
    const creator = setup('/content-checks');
    await screen.findByRole('heading', { name: 'Silence the noise. Elevate your everyday rhythm.' }, { timeout: 3000 });
    await creator.user.click(screen.getByRole('link', { name: 'Revision Journey' }));
    await screen.findByRole('heading', { name: 'Revision Roadmap' });
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Version Comparison (V1 → V2)' })).toBeTruthy());
  }, 10000);
});
