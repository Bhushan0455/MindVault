import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import type { QueueSubmission } from '../../types/reviewer-queue';
import { Modal } from '../../components/Modal';
import { Badge } from '../../components/ui';

export function SubmissionPreview({ submission, open, onClose }: { submission?: QueueSubmission; open: boolean; onClose: () => void }) {
  return <Modal open={open} title="Submission preview" onClose={onClose}>
    {submission ? <>
      <div className="queue-preview-title"><code>{submission.id}</code><Badge tone={submission.status === 'approved' ? 'success' : submission.severity === 'blocker' ? 'danger' : 'neutral'}>{submission.statusLabel}</Badge></div>
      <h3 className="queue-preview-name">{submission.title}</h3>
      <dl className="queue-preview-metadata"><dt>Brand</dt><dd>{submission.brand}</dd><dt>Submitted by</dt><dd>{submission.submittedBy.name} · {submission.submittedBy.team}</dd><dt>Channel</dt><dd>{submission.channel}</dd><dt>Region</dt><dd>{submission.region}</dd><dt>Submitted</dt><dd>{new Date(submission.submittedAt).toLocaleString()}</dd><dt>Campaign</dt><dd>{submission.campaign}</dd></dl>
      <p className="queue-preview-summary">{submission.summary}</p>
      {submission.draft && <section className="queue-preview-copy" aria-label="Submitted copy"><h4>Submitted copy · Demo snapshot</h4><strong>{submission.draft.title}</strong><p>{submission.draft.introduction}</p><p>{submission.draft.promotion}</p><p className="demo-note">Audience: {submission.draft.audience} · Language: {submission.draft.language}</p></section>}
      {submission.contentCheckPath && <Link className="button button-primary" to={submission.contentCheckPath}><ExternalLink size={14} />Open existing Findings &amp; Evidence</Link>}
      <Link className="button button-secondary" to={`/approvals/${encodeURIComponent(submission.id)}`}>Open Reviewer Detail</Link>
      <p className="queue-preview-disclaimer">Read-only legacy queue preview. All statuses and evidence are simulated. Revision-specific decisions are available in Reviewer Detail.</p>
    </> : <><h3>Submission unavailable</h3><p>The selected submission is not in the current demo dataset. Close this preview to return to the queue.</p></>}
  </Modal>;
}
