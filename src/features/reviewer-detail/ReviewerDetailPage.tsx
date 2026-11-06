import { useEffect, useId, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { BadgeCheck, BookOpenCheck, CheckCircle2, ChevronDown, Clock3, Columns2, Eye, FileImage, FilePenLine, Gavel, Globe2, History, Instagram, LoaderCircle, MessagesSquare, PanelRight, SlidersHorizontal } from 'lucide-react';
import { ShellHeader } from '../../components/ShellHeader';
import { Badge, Button, StatePanel } from '../../components/ui';
import { Modal } from '../../components/Modal';
import type { DemoScenario } from '../../types/content-check';
import type { ReviewDecisionRequest, ReviewerDetailService } from '../../types/reviewer-detail';
import { useReviewerDetail } from './useReviewerDetail';
import { EvidenceDrawer } from './EvidenceDrawer';
import { RevisionCopy } from './RevisionCopy';
import './reviewer-detail.css';

export function ReviewerDetailPage({ service }: { service: ReviewerDetailService }) {
  const { submissionId = '' } = useParams();
  // A route change owns a separate form, confirmation target and async operation.
  return <DetailWorkspace key={submissionId} submissionId={submissionId} service={service} />;
}

function DetailWorkspace({ submissionId, service }: { submissionId: string; service: ReviewerDetailService }) {
  const state = useReviewerDetail(submissionId, service);
  const { data, loading, busy, error, notice, scenario, setScenario, decide, retry } = state;
  const [params, setParams] = useSearchParams();
  const revision = data?.revisions.find((item) => item.id === (params.get('revision') ?? data.currentRevisionId));
  const [comment, setComment] = useState('');
  const [validation, setValidation] = useState('');
  const [approval, setApproval] = useState<(ReviewDecisionRequest & { number: number; title: string }) | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [findingId, setFindingId] = useState('');
  const [assetIndex, setAssetIndex] = useState<number | null>(null);
  const commentRef = useRef<HTMLTextAreaElement>(null);
  const commentId = useId();
  const isCurrent = revision?.id === data?.currentRevisionId;
  const pending = !!revision && isCurrent && revision.status === 'pending';
  const blocker = revision?.findings.some((finding) => finding.severity === 'blocker');
  const canApprove = pending && !blocker && !busy && !loading;
  const returnTo = `/approvals${params.get('queue') ? `?${params.get('queue')}` : ''}`;
  const content = revision?.snapshot.content;
  const previousRevision = data?.revisions.filter((item) => revision && item.number < revision.number).sort((a, b) => a.number - b.number).at(-1);
  const journeyParams = new URLSearchParams();
  const selectedEvent = data?.events.filter((event) => event.revisionId === revision?.id).at(-1);
  if (selectedEvent) journeyParams.set('event', selectedEvent.id);
  if (previousRevision) journeyParams.set('from', previousRevision.id);
  if (revision) journeyParams.set('to', revision.id);
  const journeyHref = `/content/${encodeURIComponent(content?.id ?? submissionId)}/history?${journeyParams}`;
  const matches = revision?.findings.filter((finding) => finding.status === 'matched').length ?? 0;
  const wordCount = content ? `${content.title} ${content.introduction} ${content.promotion}`.trim().split(/\s+/).length : 0;

  useEffect(() => {
    setComment(revision?.decision?.comment ?? ''); setValidation(''); setApproval(null); setAssetIndex(null); setEvidenceOpen(false);
  }, [revision?.id, revision?.decision?.id]);

  function inspect(id = '') { setFindingId(id); setEvidenceOpen(true); }
  function selectRevision(value: string) { const next = new URLSearchParams(params); next.set('revision', value); setParams(next, { preventScrollReset: true }); }
  async function requestChanges() {
    if (!revision || !pending || busy) return;
    if (!comment.trim()) { setValidation('Enter a reviewer comment before requesting changes.'); commentRef.current?.focus(); return; }
    setValidation('');
    await decide({ submissionId, revisionId: revision.id, kind: 'changes-requested', comment });
  }
  function askApproval() {
    if (canApprove && revision) setApproval({ submissionId, revisionId: revision.id, kind: 'approved', comment: comment.trim(), number: revision.number, title: revision.snapshot.content.title });
  }
  async function confirmApproval() {
    if (!approval || busy || !canApprove || approval.revisionId !== revision?.id) return;
    if (await decide(approval)) setApproval(null);
  }
  const approveButton = <Button variant="primary" onClick={askApproval} disabled={!canApprove} title={blocker ? 'Request a corrected revision for the sample blocker before approval.' : undefined}>{busy ? <LoaderCircle size={15} className="animate-spin" /> : <BadgeCheck size={15} />}Approve Revision v{revision?.number}</Button>;
  const requestButton = <Button onClick={() => void requestChanges()} disabled={!pending || busy}><FilePenLine size={15} />Request Changes</Button>;

  return <div className="review-detail">
    <ShellHeader demoControls={<section className="demo-toolbar" aria-label="Review demo controls"><p>Decisions and findings use the shared in-memory demo session. No real authentication, AI analysis or signing service is connected.</p><label>Preview state<select disabled={busy} value={scenario} onChange={(event) => setScenario(event.target.value as DemoScenario)}><option value="default">Default</option><option value="empty">Empty</option><option value="error">Error</option></select></label></section>}><span className="sr-only">Reviewer Detail</span></ShellHeader>
    {loading ? <StatePanel title="Loading submitted revision" loading>Preparing the exact submitted snapshot and simulated findings…</StatePanel> : !data || !revision || !content ? error ? <StatePanel title="Could not load Reviewer Detail" retry={retry}><p role="alert">{error}</p><Button onClick={() => setScenario('default')}>Return to Default</Button><Link className="button button-secondary" to={returnTo}>Back to Reviewer Queue</Link></StatePanel> : <StatePanel title={data ? 'Revision not found' : 'Submission not found'}><p>{scenario === 'empty' ? 'Empty preview mode hides this record without deleting it.' : 'This submission or revision is unavailable in the current demo session.'}</p>{scenario === 'empty' && <Button onClick={() => setScenario('default')}>Return to Default</Button>}{data && <Button onClick={() => { const next = new URLSearchParams(params); next.delete('revision'); setParams(next); }}>View current revision</Button>}<Link className="button button-primary" to={returnTo}>Back to Reviewer Queue</Link></StatePanel> : <>
      <header className="review-context"><div><nav aria-label="Review breadcrumb"><Link to={returnTo}><BadgeCheck size={14} />Approvals</Link><span>/</span><code>{submissionId}</code><span>/</span><code className="review-version">Revision v{revision.number}</code></nav><div className="review-context-meta"><strong>{revision.snapshot.campaign}</strong><span><Globe2 size={14} />{content.region}</span><span><Instagram size={14} />{content.channel}</span><Badge tone={revision.status === 'approved' ? 'success' : revision.status === 'changes-requested' ? 'danger' : 'neutral'}>{revision.status === 'pending' ? 'Pending Reviewer Sign-off' : revision.status === 'superseded' ? 'Superseded · Read only' : revision.status === 'approved' ? 'Approved' : 'Changes Requested'}</Badge></div></div>
        <div className="review-toolbar"><Button onClick={() => inspect()}><BookOpenCheck size={16} />Audit Ledger<Badge>{matches}/{revision.findings.length}</Badge></Button>{previousRevision ? <Link className="button button-secondary" to={journeyHref}><Columns2 size={16} />Compare Diff</Link> : <Button disabled title="No earlier preserved version is available."><Columns2 size={16} />Compare Diff</Button>}<label className="review-version-select"><History size={15} /><span className="sr-only">Submitted revision</span><select aria-label="Submitted revision" value={revision.id} onChange={(event) => selectRevision(event.target.value)}>{data.revisions.map((item) => <option value={item.id} key={item.id}>Revision v{item.number} · {item.status}</option>)}</select></label><Link className="button button-secondary" to={journeyHref}><History size={15} />Revision Journey</Link><a className="button button-secondary" href="#review-events">Audit Logs</a></div>
      </header>
      <div className="review-feedback" role="status" aria-live="polite">{notice && <><CheckCircle2 size={16} /><span>{notice}</span><Link to={returnTo}>Back to Reviewer Queue</Link></>}</div>
      {error && !approval && <div className="review-error" role="alert">{error}<Button onClick={retry} disabled={busy}>Reload current revision</Button></div>}
      {!isCurrent && <div className="review-older-notice">Viewing a preserved earlier snapshot. Decisions apply only to the current pending revision.<Button onClick={() => selectRevision(data.currentRevisionId)}>View current revision</Button></div>}
      <div className="review-layout"><div className="review-primary">
        <article className="review-paper" aria-label="Submitted content revision"><div className="review-paper-meta"><div><code className="review-version">SUBMITTED · v{revision.number}</code><code>Asset ID: <strong>{submissionId}</strong></code></div><div className="review-reading-stats"><span>{wordCount} words</span><span><Clock3 size={13} />{Math.ceil(wordCount / 3)} sec read</span><span><BadgeCheck size={13} />{matches} sample matches</span></div><dl className="review-identity"><dt>Submission</dt><dd>{revision.snapshot.title}</dd><dt>Creator</dt><dd>{revision.snapshot.creator.name} · {revision.snapshot.creator.team}</dd><dt>Brand</dt><dd>{revision.snapshot.brand}</dd><dt>Audience</dt><dd>{content.audience}</dd><dt>Language</dt><dd>{content.language}</dd><dt>Submitted</dt><dd><time dateTime={new Date(revision.submittedAt).toISOString()}>{new Date(revision.submittedAt).toLocaleString()}</time></dd></dl></div>
          <div className="review-paper-body"><section><h2>Campaign Lead &amp; Hook</h2><h1>{content.title}</h1></section><section className="review-submitted-copy" aria-label="Exact submitted copy"><h2>Submitted Marketing Copy</h2><p><RevisionCopy text={content.introduction} revision={revision} onInspect={inspect} /></p><p><RevisionCopy text={content.promotion} revision={revision} onInspect={inspect} /></p></section></div>
        </article>
        <div className="review-creator-bar"><span className="queue-person-avatar">{revision.snapshot.creator.initials}</span><div><strong>{revision.snapshot.creator.name}</strong><p>Submitted revision v{revision.number} · Preserved content snapshot</p></div>{revision.snapshot.contentCheckPath ? <Link className="button button-secondary" to={revision.snapshot.contentCheckPath} title="Opens the current Creator working copy, which may differ from this submitted snapshot.">Open existing Findings &amp; Evidence</Link> : <code>Session snapshot</code>}</div>
        <section className="review-assets"><div className="review-section-label"><h2>Review Collateral &amp; Creative Assets</h2><code>{revision.snapshot.assets.length} Reference Files</code></div>{revision.snapshot.assets.length ? <div className="review-asset-grid">{revision.snapshot.assets.map((asset, index) => <article key={asset.name}><div className="review-asset-image">{asset.previewUrl ? <img src={asset.previewUrl} alt={asset.label} /> : <><FileImage size={38} /><p>Creative file not supplied</p></>}<code>{asset.label}</code></div><div className="review-asset-caption"><div><strong>{asset.name}</strong><small>{asset.description}</small></div><Button variant="ghost" onClick={() => setAssetIndex(index)} aria-label={`Preview ${asset.name}`}><Eye size={16} /></Button></div></article>)}</div> : <p className="review-empty-assets">No creative files were supplied for this mock submission.</p>}</section>
        <section className="review-events" id="review-events" aria-labelledby="review-events-heading"><header><h2 id="review-events-heading"><MessagesSquare size={16} />Audit Thread &amp; Exchange</h2><code>{data.events.length} events on record</code></header><div>{data.events.map((event) => <article key={event.id}><div><strong>{event.actor}</strong><code>v{event.revisionNumber} · {event.kind.replaceAll('-', ' ')}</code><time dateTime={new Date(event.at).toISOString()}>{new Date(event.at).toLocaleString()}</time></div><p>{event.comment || 'Approved without an additional reviewer comment.'}</p></article>)}</div></section>
      </div><aside className="review-rail" aria-label="Audit ledger and revision decision">
        <section className="review-ledger"><header><h2><BookOpenCheck size={18} />Audit Ledger</h2><Badge>SIMULATED</Badge></header><div><p className="review-ledger-summary"><strong>{matches} of {revision.findings.length} sample matches</strong><code>Demo rules</code></p><details><summary><SlidersHorizontal size={16} />Quick Rule Breakdown<ChevronDown size={15} /></summary><div>{revision.findings.map((finding) => <button type="button" key={finding.id} onClick={() => inspect(finding.id)}><code>#{finding.ruleId}</code><span>{finding.status === 'matched' ? 'Sample match' : finding.severity}</span></button>)}</div></details><Button onClick={() => inspect()}><PanelRight size={16} />Open Detailed Audit Ledger Panel</Button><p className="review-demo-caption">All findings are simulated. Inspect the source excerpts before making a demo decision.</p></div></section>
        <section className="review-decision"><header><h2><Gavel size={18} />Revision Decision</h2><code>REVISION: v{revision.number}</code></header><p className="review-snapshot-notice"><strong>Snapshot-specific demo decision:</strong> Approval applies only to this submitted revision. Later Creator edits require a new revision and a new review. No cryptographic verification or compliance guarantee is provided.</p>
          {revision.decision && <div className="review-completed"><strong>{revision.status === 'approved' ? 'Revision approved' : 'Changes requested'} · v{revision.number}</strong><p>{revision.decision.reviewer}</p><time dateTime={new Date(revision.decision.decidedAt).toISOString()}>{new Date(revision.decision.decidedAt).toLocaleString()}</time><p>{revision.decision.comment || 'No additional reviewer comment.'}</p></div>}
          <label htmlFor={commentId}>Reviewer Notes &amp; Required Change Instructions</label><p id={`${commentId}-hint`} className="review-comment-hint">A comment is required when requesting changes. Approval comments are optional.</p><textarea ref={commentRef} id={commentId} aria-label="Reviewer comment" aria-invalid={!!validation} aria-describedby={`${commentId}-hint${validation ? ` ${commentId}-error` : ''}`} value={comment} onChange={(event) => { setComment(event.target.value); setValidation(''); }} disabled={!pending || busy || !!approval} placeholder="Required when requesting changes or adding review notes…" rows={5} />{validation && <p id={`${commentId}-error`} className="review-validation" role="alert">{validation}</p>}
          {blocker && pending && <p className="review-validation">A sample blocker prevents approval. Request changes or submit a corrected Creator revision.</p>}
          <label className="review-dual-sign"><input type="checkbox" disabled />Dual sign-off dispatch is not connected in this demo</label><div className="review-decision-actions">{approveButton}{requestButton}<Button variant="ghost" disabled title="Campaign rejection is outside this implementation step.">Reject Campaign</Button></div>
        </section>
      </aside></div>
      <footer className="review-decision-footer"><span><span className="status-dot" />Demo Reviewer Session: {submissionId} · v{revision.number}</span><div className="action-group">{requestButton}{approveButton}</div></footer>
      <EvidenceDrawer revision={revision} open={evidenceOpen} selectedId={findingId} onClose={() => setEvidenceOpen(false)} />
      <Modal open={!!approval && approval.revisionId === revision.id && pending} title="Confirm revision approval" onClose={() => { if (!busy) setApproval(null); }}><p>Approve <strong>revision v{approval?.number}</strong> of <strong>{approval?.title}</strong>?</p><p>This records a demo approval for snapshot <code>{approval?.revisionId}</code> only. Future revisions require their own review.</p>{error && <p role="alert" className="review-validation">{error}</p>}<Button onClick={() => setApproval(null)} disabled={busy}>Cancel</Button><Button variant="primary" onClick={() => void confirmApproval()} disabled={busy || !canApprove || approval?.revisionId !== revision.id}>{busy && <LoaderCircle size={14} className="animate-spin" />}Confirm approval</Button></Modal>
      <Modal open={assetIndex !== null} title="Creative asset preview" onClose={() => setAssetIndex(null)}>{assetIndex !== null && revision.snapshot.assets[assetIndex] && <><h3>{revision.snapshot.assets[assetIndex].name}</h3><p>{revision.snapshot.assets[assetIndex].description}</p>{revision.snapshot.assets[assetIndex].previewUrl ? <img className="review-expanded-asset" src={revision.snapshot.assets[assetIndex].previewUrl} alt={revision.snapshot.assets[assetIndex].label} /> : <p>The HTML export references remote artwork, but the creative file is not included locally. No image has been fetched or verified.</p>}</>}</Modal>
    </>}
  </div>;
}
