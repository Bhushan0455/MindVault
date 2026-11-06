import { Link } from 'react-router-dom';
import { Eye, FilePenLine, MessageSquare } from 'lucide-react';
import { Badge } from '../../components/ui';
import { SourceEvidence } from '../../components/SourceEvidence';
import type { JourneyMilestone } from '../../types/revision-journey';
import type { SubmittedRevision } from '../../types/reviewer-detail';
import { milestoneLabels } from './journey-model';

export function EventInspector({ event, revision, submissionId }: { event?: JourneyMilestone; revision?: SubmittedRevision; submissionId: string }) {
  const finding = revision?.findings.find((item) => item.id === event?.findingId);
  return <section className="journey-card journey-inspector" aria-labelledby="journey-event-heading">
    <header className="journey-card-heading"><span className="journey-heading-icon"><FilePenLine size={20} /></span><div><h2 id="journey-event-heading">Event Details{event ? ` · ${milestoneLabels[event.kind]} (V${event.revisionNumber})` : ''}</h2><p>{event?.source === 'snapshot' ? 'Derived from the preserved submission snapshot' : 'Recorded history event'}</p></div>{event && <Badge>Selected Node</Badge>}</header>
    {!event ? <p>Select a milestone to inspect its metadata.</p> : <>
      <dl className="journey-event-metadata"><div><dt>Version</dt><dd>V{event.revisionNumber}</dd></div><div><dt>{event.occurredAt !== undefined ? 'Date & Time' : 'Snapshot Recorded'}</dt><dd><time dateTime={new Date(event.occurredAt ?? event.snapshotAt ?? 0).toISOString()}>{new Date(event.occurredAt ?? event.snapshotAt ?? 0).toLocaleString()}</time></dd></div><div><dt>{event.source === 'recorded' ? 'Author' : 'Source / Author'}</dt><dd>{event.actor}</dd></div></dl>
      <div className="journey-event-summary"><h3>Revision Summary</h3><p>{finding?.explanation ?? event.comment}</p></div>
      {event.kind === 'approved' && <p className="journey-approval-note">Reviewer approval applies to <strong>V{event.revisionNumber}</strong> only. Snapshot: <code>{event.revisionId}</code>.</p>}
      <div className="journey-event-note"><h3><MessageSquare size={14} />{event.kind === 'approved' || event.kind === 'changes-requested' ? 'Reviewer Comment' : 'Event Note'}</h3><p>{event.comment || 'No additional comment was recorded.'}</p>{event.source === 'snapshot' && <small>This milestone has no independent event timestamp. Its position describes the snapshot workflow, not a measured action time.</small>}</div>
      {finding && <details className="journey-finding-evidence"><summary>Inspect supporting rule &amp; evidence · {finding.severity}</summary>{finding.sources.map((source, index) => <SourceEvidence key={`${source.title}-${index}`} source={source} />)}<p className="demo-note">Simulated finding, not real AI analysis.</p></details>}
      {revision ? <Link className="button button-secondary journey-full-version" to={`/approvals/${encodeURIComponent(submissionId)}?revision=${encodeURIComponent(revision.id)}`}><Eye size={16} />View Version {revision.number} Full Content</Link> : <p role="status">This event’s revision snapshot is unavailable.</p>}
    </>}
  </section>;
}
