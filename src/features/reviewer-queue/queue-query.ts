import type { QueueFilters, QueueHistory, QueueSeverity, QueueStatus, QueueSubmission } from '../../types/reviewer-queue';

export const defaultQueueFilters: QueueFilters = { status: 'all', search: '', brand: '', channel: '', severity: 'all', sort: 'newest', page: 1, pageSize: 5 };
const statuses: readonly string[] = ['pending', 'changes-requested', 'approved'];
const severities: readonly string[] = ['blocker', 'warning', 'advisory', 'none'];
const severityOrder: Record<QueueSeverity, number> = { blocker: 0, warning: 1, advisory: 2, none: 3 };

export function readQueueFilters(params: URLSearchParams): QueueFilters {
  const status = params.get('status') ?? 'all';
  const severity = params.get('severity') ?? 'all';
  const sort = params.get('sort');
  const page = Number(params.get('page') ?? 1);
  const pageSize = Number(params.get('size') ?? 5);
  return {
    status: statuses.includes(status) ? status as QueueStatus : 'all',
    search: params.get('q') ?? '', brand: params.get('brand') ?? '', channel: params.get('channel') ?? '',
    severity: severities.includes(severity) ? severity as QueueSeverity : 'all',
    sort: sort === 'oldest' || sort === 'severity' ? sort : 'newest',
    page: Number.isSafeInteger(page) && page > 0 ? page : 1,
    pageSize: pageSize === 10 || pageSize === 20 ? pageSize : 5,
  };
}

export function filterQueue(records: readonly QueueSubmission[], filters: QueueFilters): QueueSubmission[] {
  const search = filters.search.trim().toLocaleLowerCase();
  return records.filter((item) => {
    const haystack = [item.title, item.id, item.sourceDraftId, item.campaign, item.submittedBy.name].join(' ').toLocaleLowerCase();
    return (filters.status === 'all' || item.status === filters.status)
      && (!filters.brand || item.brand === filters.brand)
      && (!filters.channel || item.channel === filters.channel)
      && (filters.severity === 'all' || item.severity === filters.severity)
      && (!search || haystack.includes(search));
  }).sort((a, b) => {
    if (filters.sort === 'severity') return severityOrder[a.severity] - severityOrder[b.severity] || b.submittedAt - a.submittedAt || a.id.localeCompare(b.id);
    return (filters.sort === 'oldest' ? a.submittedAt - b.submittedAt : b.submittedAt - a.submittedAt) || a.id.localeCompare(b.id);
  });
}

export function paginateQueue(records: readonly QueueSubmission[], filters: QueueFilters) {
  const pages = Math.max(1, Math.ceil(records.length / filters.pageSize));
  const page = Math.min(filters.page, pages);
  const offset = (page - 1) * filters.pageSize;
  return { page, pages, rows: records.slice(offset, offset + filters.pageSize), start: records.length ? offset + 1 : 0, end: Math.min(offset + filters.pageSize, records.length) };
}

export function queueMetrics(records: readonly QueueSubmission[], now = Date.now(), history: QueueHistory = { reviewedBeforeVisibleQueue: 0, approvedYesterday: 0 }) {
  const approved = records.filter((item) => item.status === 'approved');
  const approvedToday = approved.filter((item) => item.approvedAt !== undefined && new Date(item.approvedAt).toDateString() === new Date(now).toDateString()).length;
  const pending = records.filter((item) => item.status === 'pending').length;
  const changes = records.filter((item) => item.status === 'changes-requested').length;
  return { pending, changes, approved: approved.length, all: records.length, urgent: records.filter((item) => item.status === 'pending' && item.severity === 'blocker').length, approvedToday, approvalDelta: records.length ? approvedToday - history.approvedYesterday : 0, reviewed: records.length ? history.reviewedBeforeVisibleQueue + approved.length + changes : 0 };
}

export function queueCsv(records: readonly QueueSubmission[]): string {
  const escape = (value: string) => {
    const safe = /^[=+@\-\t\r]/.test(value) ? `'${value}` : value;
    return `"${safe.replaceAll('"', '""')}"`;
  };
  const rows = records.map((item) => [item.id, item.title, item.brand, item.submittedBy.name, item.channel, item.region, item.statusLabel, item.summary, new Date(item.submittedAt).toISOString(), 'Simulated']);
  return [['Reference ID', 'Content title', 'Brand', 'Submitted by', 'Channel', 'Region', 'Status', 'Summary', 'Submitted at', 'Data type'], ...rows].map((row) => row.map(escape).join(',')).join('\r\n');
}
