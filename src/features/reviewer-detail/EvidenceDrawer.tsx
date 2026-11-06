import { Modal } from '../../components/Modal';
import { Badge } from '../../components/ui';
import { SourceEvidence } from '../../components/SourceEvidence';
import type { SubmittedRevision } from '../../types/reviewer-detail';

export function EvidenceDrawer({ revision, open, selectedId, onClose }: { revision: SubmittedRevision; open: boolean; selectedId: string; onClose: () => void }) {
  return <Modal className="review-evidence-dialog" title="Verification & Audit Ledger" open={open} onClose={onClose}>
    <p className="review-demo-notice">Simulated findings for revision v{revision.number}. No real AI analysis, cryptographic verification or regulatory guarantee.</p>
    {revision.findings.map((finding) => <article key={finding.id} className={`review-finding review-finding-${finding.severity}`}>
      <header><code>#{finding.ruleId}</code><Badge tone={finding.severity === 'blocker' ? 'danger' : finding.status === 'matched' ? 'success' : 'neutral'}>{finding.status === 'matched' ? 'Sample match' : finding.severity}</Badge></header>
      <h3>{finding.title}</h3><p>{finding.explanation}</p>{finding.claim && <p className="review-claim-quote">Submitted text: <strong>{finding.claim}</strong></p>}
      <details open={selectedId === finding.id}><summary>Supporting source evidence</summary>{finding.sources.map((source, index) => <SourceEvidence key={`${source.title}-${index}`} source={source} />)}</details>
    </article>)}
  </Modal>;
}
