import type { ContentDraft, DemoScenario, RuleSource } from './content-check';
import type { QueueSeverity, QueueStatus } from './reviewer-queue';

export interface ReviewFinding {
  readonly id: string;
  readonly ruleId: string;
  readonly title: string;
  readonly claim: string;
  readonly severity: QueueSeverity;
  readonly status: 'matched' | 'attention' | 'advisory';
  readonly explanation: string;
  readonly sources: readonly RuleSource[];
  readonly simulated: true;
}

export interface RevisionSnapshot {
  readonly title: string;
  readonly campaign: string;
  readonly brand: string;
  readonly contentCheckPath?: string;
  readonly creator: { readonly name: string; readonly team: string; readonly initials: string };
  readonly content: Readonly<ContentDraft>;
  readonly assets: readonly ReviewAsset[];
}

export interface ReviewAsset {
  readonly name: string;
  readonly label: string;
  readonly description: string;
  readonly previewUrl?: string;
}

export interface ReviewDecision {
  readonly id: string;
  readonly submissionId: string;
  readonly revisionId: string;
  readonly kind: 'approved' | 'changes-requested';
  readonly comment: string;
  readonly reviewer: string;
  readonly decidedAt: number;
}

export interface SubmittedRevision {
  readonly id: string;
  readonly submissionId: string;
  readonly number: number;
  readonly submittedAt: number;
  readonly snapshot: RevisionSnapshot;
  readonly findings: readonly ReviewFinding[];
  readonly status: QueueStatus | 'superseded';
  readonly decision?: ReviewDecision;
}

export interface ReviewHistoryEvent {
  readonly id: string;
  readonly submissionId: string;
  readonly revisionId: string;
  readonly revisionNumber: number;
  readonly kind: 'draft-created' | 'ai-check' | 'finding-detected' | 'revision-created' | 'rechecked' | 'submitted' | 'approved' | 'changes-requested';
  readonly findingId?: string;
  readonly actor: string;
  readonly at: number;
  readonly comment: string;
}

export interface SubmissionReview {
  readonly submissionId: string;
  readonly currentRevisionId: string;
  readonly revisions: readonly SubmittedRevision[];
  readonly events: readonly ReviewHistoryEvent[];
}

export interface ReviewDecisionRequest {
  submissionId: string;
  revisionId: string;
  kind: ReviewDecision['kind'];
  comment: string;
}

// API adapters must enforce the same revision identity and pending-state guards.
export interface ReviewerDetailService {
  load(submissionId: string, scenario: DemoScenario): Promise<SubmissionReview | null>;
  decide(request: ReviewDecisionRequest, scenario: DemoScenario): Promise<SubmissionReview>;
  subscribe(listener: () => void): () => void;
}
