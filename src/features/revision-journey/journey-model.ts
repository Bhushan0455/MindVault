import type { JourneyMilestone } from '../../types/revision-journey';
import type { SubmissionReview, SubmittedRevision } from '../../types/reviewer-detail';

export const milestoneLabels: Record<JourneyMilestone['kind'], string> = {
  'draft-created': 'Draft Created', 'ai-check': 'AI Checked', 'finding-detected': 'Finding Detected',
  'revision-created': 'Draft Revised', rechecked: 'Rechecked', submitted: 'Submitted', approved: 'Approved', 'changes-requested': 'Changes Requested',
};
const phase: Record<JourneyMilestone['kind'], number> = { 'draft-created': 0, 'revision-created': 0, 'ai-check': 1, rechecked: 1, 'finding-detected': 2, submitted: 3, approved: 4, 'changes-requested': 4 };

export function buildMilestones(review: SubmissionReview): JourneyMilestone[] {
  // With no journal, do not fabricate a historical sequence from versions alone.
  if (!review.events.length) return [];
  const milestones: JourneyMilestone[] = review.events.map((event) => ({ id: event.id, revisionId: event.revisionId, revisionNumber: event.revisionNumber, kind: event.kind, actor: event.actor, comment: event.comment, occurredAt: event.at, findingId: event.findingId, source: 'recorded' }));
  for (const revision of review.revisions) {
    const recorded = review.events.filter((event) => event.revisionId === revision.id);
    const creation = revision.number === 1 ? 'draft-created' : 'revision-created';
    if (!recorded.some((event) => event.kind === creation)) milestones.push({ id: `${revision.id}:derived:${creation}`, revisionId: revision.id, revisionNumber: revision.number, kind: creation, actor: revision.snapshot.creator.name, comment: revision.number === 1 ? 'First preserved snapshot. The original draft creation time was not recorded.' : 'A new content snapshot is preserved for this revision. Its independent editing time was not recorded.', source: 'snapshot', snapshotAt: revision.submittedAt });
    if (revision.findings.length && !recorded.some((event) => event.kind === 'ai-check' || event.kind === 'rechecked')) milestones.push({ id: `${revision.id}:derived:check`, revisionId: revision.id, revisionNumber: revision.number, kind: revision.number === 1 ? 'ai-check' : 'rechecked', actor: 'Simulated findings attached to snapshot', comment: 'Derived from the simulated findings saved with this revision. An independent check timestamp is unavailable; this is not real AI analysis.', source: 'snapshot', snapshotAt: revision.submittedAt });
    if (!recorded.some((event) => event.kind === 'finding-detected')) for (const finding of revision.findings.filter((item) => item.status !== 'matched')) milestones.push({ id: `${revision.id}:derived:finding:${finding.id}`, revisionId: revision.id, revisionNumber: revision.number, kind: 'finding-detected', actor: 'Simulated findings attached to snapshot', comment: finding.explanation, findingId: finding.id, source: 'snapshot', snapshotAt: revision.submittedAt });
  }
  return milestones.sort((a, b) => a.revisionNumber - b.revisionNumber || phase[a.kind] - phase[b.kind] || (a.occurredAt ?? a.snapshotAt ?? 0) - (b.occurredAt ?? b.snapshotAt ?? 0));
}

export function defaultMilestone(milestones: readonly JourneyMilestone[]) {
  return [...milestones].reverse().find((event) => event.kind === 'revision-created') ?? milestones.at(-1);
}

export function defaultVersionPair(revisions: readonly SubmittedRevision[], selectedId?: string) {
  const sorted = [...revisions].sort((a, b) => a.number - b.number);
  const index = sorted.findIndex((revision) => revision.id === selectedId);
  if (selectedId && index < 0) return [sorted[0]?.id ?? '', selectedId];
  return index > 0 ? [sorted[index - 1]?.id ?? '', sorted[index]?.id ?? ''] : [sorted[0]?.id ?? '', sorted[1]?.id ?? ''];
}
