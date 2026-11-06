import type { DemoScenario } from './content-check';
import type { ReviewHistoryEvent, SubmissionReview } from './reviewer-detail';

export interface JourneyMilestone {
  readonly id: string;
  readonly revisionId: string;
  readonly revisionNumber: number;
  readonly kind: ReviewHistoryEvent['kind'];
  readonly actor: string;
  readonly comment: string;
  readonly source: 'recorded' | 'snapshot';
  readonly occurredAt?: number;
  readonly snapshotAt?: number;
  readonly findingId?: string;
}

export interface RevisionJourneyService {
  load(contentId: string, scenario: DemoScenario): Promise<SubmissionReview | null>;
  subscribe(listener: () => void): () => void;
}
