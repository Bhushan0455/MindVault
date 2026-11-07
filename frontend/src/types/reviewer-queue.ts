import type { ContentDraft, DemoScenario } from './content-check';

export type QueueStatus = 'pending' | 'changes-requested' | 'approved';
export type QueueSeverity = 'blocker' | 'warning' | 'advisory' | 'none';
export type QueueSort = 'newest' | 'oldest' | 'severity';

export interface QueueSubmission {
  id: string;
  sourceDraftId?: string;
  contentCheckPath?: string;
  revisionId?: string;
  title: string;
  campaign: string;
  assetDescription: string;
  brand: string;
  submittedBy: { name: string; team: string; initials: string };
  channel: string;
  region: string;
  submittedAt: number;
  approvedAt?: number;
  status: QueueStatus;
  severity: QueueSeverity;
  statusLabel: string;
  summary: string;
  draft?: ContentDraft;
  origin: 'stitch-fixture' | 'creator-demo' | 'api';
  simulated: boolean;
}

export interface QueueFilters {
  status: QueueStatus | 'all';
  search: string;
  brand: string;
  channel: string;
  severity: QueueSeverity | 'all';
  sort: QueueSort;
  page: number;
  pageSize: 5 | 10 | 20;
}

export interface ReviewerQueueService {
  mode?:'api';
  load(scenario: DemoScenario): Promise<readonly QueueSubmission[]>;
  subscribe(listener: () => void): () => void;
  getHistory(): QueueHistory;
  // A stable snapshot between mutations, suitable for useSyncExternalStore.
  getSnapshot(): readonly QueueSubmission[];
}

export interface QueueHistory {
  reviewedBeforeVisibleQueue: number;
  approvedYesterday: number;
}
