import { Link } from 'react-router-dom';
import { CheckCircle2, Columns2, History } from 'lucide-react';
import { Badge, Button } from '../../components/ui';
import type { SubmittedRevision } from '../../types/reviewer-detail';
import { diffText, type TextChange } from './text-diff';

const textFields = [['title', 'Headline'], ['introduction', 'Introduction'], ['promotion', 'Promotion']] as const;
const targetingFields = [['channel', 'Channel'], ['audience', 'Audience'], ['region', 'Region'], ['language', 'Language']] as const;

function ChangedText({ changes, side }: { changes: readonly TextChange[]; side: 'before' | 'after' }) {
  return <>{changes.filter((change) => change.kind !== (side === 'before' ? 'added' : 'removed')).map((change, index) => change.kind === 'removed' ? <del key={index}>{change.text}</del> : change.kind === 'added' ? <ins key={index}>{change.text}</ins> : <span key={index}>{change.text}</span>)}</>;
}

export function VersionComparison({ revisions, beforeId, afterId, onChange, onReset }: { revisions: readonly SubmittedRevision[]; beforeId: string; afterId: string; onChange: (side: 'from' | 'to', id: string) => void; onReset: () => void }) {
  const before = revisions.find((revision) => revision.id === beforeId);
  const after = revisions.find((revision) => revision.id === afterId);
  const fields = before && after ? textFields.filter(([field]) => before.snapshot.content[field] !== after.snapshot.content[field]).map(([field, label]) => ({ field, label, changes: diffText(before.snapshot.content[field], after.snapshot.content[field]) })) : [];
  const metadata = before && after ? targetingFields.filter(([field]) => before.snapshot.content[field] !== after.snapshot.content[field]) : [];
  const count = fields.length + metadata.length;
  return <section className="journey-card journey-comparison" aria-labelledby="journey-comparison-heading" id="journey-comparison" tabIndex={-1}>
    <header className="journey-card-heading"><span className="journey-heading-icon"><Columns2 size={20} /></span><div><h2 id="journey-comparison-heading">Version Comparison{before && after ? ` (V${before.number} → V${after.number})` : ''}</h2><p>Preserved content and targeting changes</p></div><Badge>{count} {count === 1 ? 'field changed' : 'fields changed'}</Badge></header>
    <div className="journey-comparison-selectors">{([['from', 'Before version', beforeId], ['to', 'After version', afterId]] as const).map(([side, label, value]) => <label key={side}>{label}<select value={value} onChange={(event) => onChange(side, event.target.value)}><option value="">Select version</option>{value && !revisions.some((revision) => revision.id === value) && <option value={value}>Unavailable version</option>}{revisions.map((revision) => <option key={revision.id} value={revision.id}>V{revision.number} · {revision.status}</option>)}</select></label>)}</div>
    {!revisions.length ? <p className="journey-comparison-empty">No versions are available for comparison.</p> : !before || !after ? <div className="journey-comparison-empty" role="status"><p>{revisions.length < 2 ? 'Only one version is available. Submit an edited revision to compare changes.' : 'A comparison version is unavailable. Choose two preserved versions.'}</p><Button onClick={onReset}>Reset comparison</Button></div> : before.id === after.id ? <p className="journey-comparison-empty" role="status">Select two different versions to compare.</p> : <>
      {!count && <p className="journey-comparison-empty" role="status">No content or targeting changes between these versions.</p>}
      <div className="journey-diff-columns">{([['before', before], ['after', after]] as const).map(([side, revision]) => <article key={side} className={`journey-diff-panel ${side}`} aria-label={`Version ${revision.number} ${side}`}><header><span>{side === 'before' ? <History size={14} /> : <CheckCircle2 size={14} />}Draft V{revision.number}</span><Badge tone={revision.status === 'approved' ? 'success' : 'neutral'}>{revision.status === 'approved' ? `Approved · V${revision.number}` : revision.status === 'pending' ? 'Pending Review' : revision.status === 'superseded' ? 'Superseded' : 'Changes Requested'}</Badge></header><div className="journey-diff-copy">{fields.map(({ field, label, changes }) => <section key={field}><h3>{label}</h3><p><ChangedText changes={changes} side={side} /></p></section>)}{!fields.length && <p>Submitted copy is unchanged.</p>}</div><Link to={`/approvals/${encodeURIComponent(revision.submissionId)}?revision=${encodeURIComponent(revision.id)}`}>View V{revision.number} full content</Link></article>)}</div>
      {!!metadata.length && <div className="journey-targeting-diff"><h3>Targeting changes</h3>{metadata.map(([field, label]) => <p key={field}><strong>{label}: </strong><del>{before.snapshot.content[field]}</del><span aria-hidden="true"> → </span><ins>{after.snapshot.content[field]}</ins></p>)}</div>}
      <div className="journey-advisory"><CheckCircle2 size={16} /><span>Simulated findings · V{after.number}: {after.findings.filter((finding) => finding.status !== 'matched').length} sample findings need review</span><Badge>Demo only</Badge></div>
    </>}
  </section>;
}
