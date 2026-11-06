import { describe, expect, it } from 'vitest';
import { mockContentCheck } from '../mocks/content-check';
import { assertSubmittable, mockContentCheckService, simulateCheck } from './mock-content-check-service';

describe('mock content check workflow (no real services)', () => {
  it('blocks the original price and allows the corrected, rechecked fixture', () => {
    const draft = structuredClone(mockContentCheck.draft);
    const original = simulateCheck(draft);
    expect(original.findings).toHaveLength(1);
    expect(() => assertSubmittable(draft, original)).toThrow();
    draft.promotion = draft.promotion.replace('₹799', '₹999');
    expect(() => assertSubmittable(draft, original)).toThrow('Recheck');
    const corrected = simulateCheck(draft);
    expect(corrected.simulated).toBe(true);
    expect(() => assertSubmittable(draft, corrected)).not.toThrow();
    draft.language = 'Hindi (IN)';
    expect(() => assertSubmittable(draft, corrected)).toThrow('Recheck');
  });

  it('rejects blank required content even after a mock recheck', () => {
    const draft = { ...mockContentCheck.draft, title: ' ', promotion: 'Sample ₹999' };
    expect(() => assertSubmittable(draft, simulateCheck(draft))).toThrow('Complete all');
  });

  it('returns independent fixture copies and a true empty state', async () => {
    const loaded = await mockContentCheckService.load('default');
    loaded!.draft.title = 'Changed';
    expect(mockContentCheck.draft.title).not.toBe('Changed');
    expect(await mockContentCheckService.load('empty')).toBeNull();
  });

  it('keeps service failure as an error, never a compliance verdict', async () => {
    await expect(mockContentCheckService.load('error')).rejects.toThrow('simulated service');
    await expect(mockContentCheckService.recheck(mockContentCheck.draft, 'error')).rejects.toThrow('simulated service');
    await expect(mockContentCheckService.save(mockContentCheck.draft, 'error')).rejects.toThrow('simulated service');
  });
});
