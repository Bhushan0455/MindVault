// @vitest-environment jsdom
// Local DOM interactions only; these are not live-service or browser checks.
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { App } from '../../App';
import { createMockSessionStore } from '../../services/mock-session-store';
import { createMockReviewerQueueService } from '../../services/mock-reviewer-queue-service';
import { createMockContentCheckService } from '../../services/mock-content-check-service';
import { createMockReviewerDetailService } from '../../services/mock-reviewer-detail-service';

beforeAll(() => {
  // jsdom does not implement native dialog modality/focus; browser QA remains separate.
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value() { this.setAttribute('open', ''); } });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value() { this.removeAttribute('open'); this.dispatchEvent(new Event('close')); } });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function setup(path = '/approvals') {
  const store = createMockSessionStore();
  const queueService = createMockReviewerQueueService(store, 0);
  const contentService = createMockContentCheckService(store);
  const reviewService = createMockReviewerDetailService(store, 0);
  render(<MemoryRouter initialEntries={[path]}><App queueService={queueService} contentService={contentService} reviewService={reviewService} /></MemoryRouter>);
  return { user: userEvent.setup(), store, queueService };
}

describe('Reviewer Queue interactions (local DOM with mock services)', () => {
  it('loads, searches, combines filters, resets, sorts and paginates', async () => {
    const { user } = setup();
    expect(screen.getByRole('heading', { name: 'Loading Reviewer Queue' })).toBeTruthy();
    await screen.findByRole('table');
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(6);
    const search = screen.getByRole('searchbox', { name: 'Search submissions' });
    await user.keyboard('{Control>}k{/Control}');
    expect(document.activeElement).toBe(search);
    await user.type(search, 'monsoon');
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(2);
    await user.clear(search);
    await user.selectOptions(screen.getByRole('combobox', { name: 'Brand' }), 'Solace Home');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Channel' }), 'Website');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Severity' }), 'advisory');
    expect(screen.getByRole('link', { name: 'Solace Home Warranty Landing Page Copy' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Pending 3' }));
    expect(screen.getByRole('heading', { name: 'No matching submissions' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Reset all filters' }));
    await user.selectOptions(screen.getByRole('combobox', { name: 'Sort submissions' }), 'oldest');
    expect(within(screen.getByRole('table')).getAllByRole('row')[1].textContent).toContain('REV-2024-849');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Sort submissions' }), 'severity');
    expect(within(screen.getByRole('table')).getAllByRole('row')[1].textContent).toContain('REV-2024-884');
    await user.click(screen.getByRole('button', { name: 'Next page' }));
    expect(screen.getByRole('button', { name: 'Page 2' }).getAttribute('aria-current')).toBe('page');
    await user.type(search, 'monsoon');
    expect(screen.getByRole('button', { name: 'Page 1' }).getAttribute('aria-current')).toBe('page');
  });

  it('preserves the legacy snapshot preview without losing filters', async () => {
    const { user } = setup('/approvals?status=pending&q=CHK-9042&submission=REV-2024-884');
    await screen.findByRole('table');
    const preview = await screen.findByRole('dialog', { name: 'Submission preview' });
    expect(within(preview).getByRole('region', { name: 'Submitted copy' }).textContent).toContain('₹799');
    expect(within(preview).getByRole('link', { name: 'Open existing Findings & Evidence' }).getAttribute('href')).toBe('/content-checks');
    await user.click(within(preview).getByRole('button', { name: 'Close submission preview' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Submission preview' })).toBeNull());
    expect((screen.getByRole('searchbox') as HTMLInputElement).value).toBe('CHK-9042');
    expect(screen.getByRole('button', { name: 'Pending 3' }).getAttribute('aria-pressed')).toBe('true');
  });

  it('selects the current page, exports selected rows and applies queue settings', async () => {
    const { user } = setup();
    await screen.findByRole('table');
    await user.click(screen.getByRole('checkbox', { name: 'Select all submissions on this page' }));
    expect(screen.getByText(/5 selected/)).toBeTruthy();
    await user.click(screen.getByRole('checkbox', { name: 'Select REV-2024-884' }));
    expect((screen.getByRole('checkbox', { name: 'Select all submissions on this page' }) as HTMLInputElement).indeterminate).toBe(true);
    await user.click(screen.getByRole('checkbox', { name: 'Select REV-2024-884' }));
    const createObjectURL = vi.fn(() => 'blob:queue-test');
    vi.stubGlobal('URL', class extends URL { static createObjectURL = createObjectURL; static revokeObjectURL = vi.fn(); });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    await user.type(screen.getByRole('searchbox'), 'No matches for these words');
    expect(screen.getByRole('heading', { name: 'No matching submissions' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Export Audit Log' }));
    expect(createObjectURL).toHaveBeenCalledOnce(); expect(click).toHaveBeenCalledOnce();
    expect(screen.getByText(/Exported 5 simulated submissions/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Reset all filters' }));
    await user.click(screen.getByRole('button', { name: 'Queue Settings' }));
    const settings = screen.getByRole('dialog', { name: 'Queue settings' });
    await user.selectOptions(within(settings).getByRole('combobox', { name: 'Rows per page' }), '10');
    await user.click(within(settings).getByRole('button', { name: 'Done' }));
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(11);
  });

  it('shows empty and error states without deleting the session queue', async () => {
    const { user, store } = setup();
    await screen.findByRole('table');
    await user.click(screen.getByLabelText('Profile and demo controls'));
    await user.selectOptions(screen.getByRole('combobox', { name: 'Preview state' }), 'empty');
    await screen.findByRole('heading', { name: 'No submissions yet' });
    expect(store.getSnapshot()).toHaveLength(19);
    await user.selectOptions(screen.getByRole('combobox', { name: 'Preview state' }), 'error');
    await screen.findByRole('heading', { name: 'Could not load the queue' });
    expect(screen.getByRole('alert').textContent).toContain('simulated queue service');
    await user.click(screen.getByRole('button', { name: 'Return to Default' }));
    await screen.findByRole('table');
  });

  it('hands a corrected Creator submission to the queue and reuses existing Findings & Evidence', async () => {
    const { user } = setup('/content-checks');
    await screen.findByRole('heading', { name: 'Silence the noise. Elevate your everyday rhythm.' }, { timeout: 3000 });
    expect((screen.getAllByRole('button', { name: 'Submit for Approval' })[0] as HTMLButtonElement).disabled).toBe(true);
    await user.click(screen.getByRole('button', { name: /Quick Fix \(Apply ₹999\)/ }));
    await user.click(screen.getByRole('button', { name: 'Edit draft' }));
    await user.clear(screen.getByRole('textbox', { name: 'Headline' }));
    await user.type(screen.getByRole('textbox', { name: 'Headline' }), 'Creator launch edited in this session');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Channel' }), 'Instagram Story');
    await user.click(screen.getByRole('button', { name: 'Done editing draft' }));
    await user.click(screen.getByRole('button', { name: 'Recheck with MindVault' }));
    await waitFor(() => expect((screen.getAllByRole('button', { name: 'Submit for Approval' })[0] as HTMLButtonElement).disabled).toBe(false));
    await user.click(screen.getAllByRole('button', { name: 'Submit for Approval' })[0]);
    await user.click(await screen.findByRole('link', { name: 'View Reviewer Queue' }));
    await user.click(await screen.findByRole('link', { name: 'Creator launch edited in this session' }));
    await screen.findByRole('heading', { name: 'Creator launch edited in this session' });
    const submittedCopy = screen.getByRole('region', { name: 'Exact submitted copy' });
    expect(screen.getByText('Pending Reviewer Sign-off')).toBeTruthy();
    expect(submittedCopy.textContent).toContain('₹999');
    expect(submittedCopy.textContent).not.toContain('₹799');
    await user.click(screen.getByRole('link', { name: 'Open existing Findings & Evidence' }));
    await screen.findByRole('heading', { name: 'Creator launch edited in this session' }, { timeout: 3000 });
    expect(screen.getByRole('button', { name: 'Inspect sample price ₹999' })).toBeTruthy();
  }, 10000);
});
