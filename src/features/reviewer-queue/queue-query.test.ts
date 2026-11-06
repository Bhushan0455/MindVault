import { describe, expect, it } from 'vitest';
import { createMockSubmissions, mockQueueHistory } from '../../mocks/reviewer-queue';
import { defaultQueueFilters, filterQueue, paginateQueue, queueCsv, queueMetrics, readQueueFilters } from './queue-query';

const now = new Date('2026-11-06T12:00:00Z').getTime();
const submissions = createMockSubmissions(now);

describe('Reviewer Queue queries (local mock data only)', () => {
  it('derives the tab counts and metrics from the records', () => {
    expect(queueMetrics(submissions, now, mockQueueHistory)).toMatchObject({ pending: 3, urgent: 1, changes: 2, approved: 14, all: 19, approvedToday: 14, approvalDelta: 4, reviewed: 89 });
    expect(queueMetrics([], now)).toMatchObject({ all: 0, pending: 0, approved: 0, reviewed: 0 });
  });

  it('searches titles, IDs, Creator draft IDs and submitters without case sensitivity', () => {
    for (const search of ['  MONSOON  ', 'rev-2024-885', 'alex chen']) {
      expect(filterQueue(submissions, { ...defaultQueueFilters, search }).some((item) => item.id === 'REV-2024-885')).toBe(true);
    }
    expect(filterQueue(submissions, { ...defaultQueueFilters, search: 'CHK-9042' }).map((item) => item.id)).toEqual(['REV-2024-884']);
    expect(filterQueue(submissions, { ...defaultQueueFilters, search: 'absent term' })).toEqual([]);
  });

  it('combines status, brand, channel and severity with AND semantics', () => {
    const result = filterQueue(submissions, { ...defaultQueueFilters, status: 'changes-requested', brand: 'Solace Home', channel: 'Website', severity: 'advisory' });
    expect(result.map((item) => item.id)).toEqual(['REV-2024-866']);
    expect(filterQueue(submissions, { ...defaultQueueFilters, status: 'approved', severity: 'blocker' })).toEqual([]);
  });

  it('sorts by time or severity without mutating the source', () => {
    const original = submissions.map((item) => item.id);
    expect(filterQueue(submissions, defaultQueueFilters)[0].id).toBe('REV-2024-884');
    expect(filterQueue(submissions, { ...defaultQueueFilters, sort: 'oldest' })[0].id).toBe('REV-2024-849');
    expect(filterQueue(submissions, { ...defaultQueueFilters, sort: 'severity' })[0].severity).toBe('blocker');
    expect(submissions.map((item) => item.id)).toEqual(original);
  });

  it('validates URL options and clamps pages after filtering', () => {
    expect(readQueueFilters(new URLSearchParams('status=invalid&severity=bad&sort=bad&page=-2&size=999'))).toEqual(defaultQueueFilters);
    expect(paginateQueue(submissions, { ...defaultQueueFilters, page: 999 })).toMatchObject({ page: 4, pages: 4, start: 16, end: 19 });
    expect(paginateQueue([], { ...defaultQueueFilters, page: 5 })).toMatchObject({ page: 1, start: 0, end: 0, rows: [] });
  });

  it('exports labeled simulated data and escapes edited content safely', () => {
    const record = { ...submissions[0], title: '=SUM(1,2)', summary: 'Quote "this", please\nnext line' };
    const csv = queueCsv([record]);
    expect(csv).toContain('"\'=SUM(1,2)"');
    expect(csv).toContain('"Quote ""this"", please\nnext line"');
    expect(csv).toContain('"Simulated"');
  });
});
