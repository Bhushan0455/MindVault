import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Check, CheckCircle2, ChevronDown, FileText, History, Instagram, Languages, LoaderCircle, LockKeyhole, MapPin, PanelLeft, Pencil, RefreshCw, Send, ShieldCheck, SlidersHorizontal, Users } from 'lucide-react';
import { Badge, Button, StatePanel } from '../../components/ui';
import { ShellHeader } from '../../components/ShellHeader';
import { metadataOptions, mockProductName } from '../../mocks/content-check';
import type { ContentCheckService, DemoScenario } from '../../types/content-check';
import { useContentCheck } from './useContentCheck';
import { Inspector } from './Inspector';
import { DraftText } from './DraftText';

export function ContentCheckPage({ service }: { service: ContentCheckService }) {
  const state = useContentCheck(service);
  const { data, draft, result, busy, loading, error, notice, stale, submitted, saved, canSubmit, edit, run, quickFix } = state;
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [editing, setEditing] = useState(false);
  const inspectorToggle = useRef<HTMLButtonElement>(null);
  const conflict = !!result?.findings.length;
  const hasOriginalPrice = !!data && !!draft?.promotion.includes(data.finding.original);
  const draftText = draft ? `${draft.title} ${draft.introduction} ${draft.promotion}` : '';

  useEffect(() => {
    function shortcuts(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey) || !draft || busy || submitted) return;
      if (event.key === 'Enter' && hasOriginalPrice) { event.preventDefault(); quickFix(); }
      if (event.key.toLowerCase() === 's') { event.preventDefault(); void run('save'); }
    }
    window.addEventListener('keydown', shortcuts);
    return () => window.removeEventListener('keydown', shortcuts);
  }, [draft, busy, submitted, hasOriginalPrice, quickFix, run]);

  function closeInspector() { setInspectorOpen(false); inspectorToggle.current?.focus(); }
  function changeScenario(value: DemoScenario) { setEditing(false); state.setScenario(value); }
  const submitButton = <Button variant="primary" className="submit-button" disabled={!canSubmit || !!busy || loading} onClick={() => void run('submit')} title={stale ? 'Recheck your latest edits first' : conflict ? 'Resolve the sample conflict and recheck first' : undefined}>
    {busy === 'submit' ? <LoaderCircle size={15} className="animate-spin" /> : submitted ? <Check size={15} /> : canSubmit ? <Send size={15} /> : <LockKeyhole size={15} />}{submitted ? 'Submitted (Demo)' : 'Submit for Approval'}
  </Button>;

  return <div className="content-check-page">
    <ShellHeader demoControls={<section className="demo-toolbar" aria-label="Demo controls"><p>All content and findings are simulated. No real services are connected.</p><label>Preview state<select value={state.scenario} disabled={!!busy} onChange={(event) => changeScenario(event.target.value as DemoScenario)}><option value="default">Default</option><option value="empty">Empty</option><option value="error">Error</option></select></label></section>}>
      <div className="check-header-context"><nav aria-label="Breadcrumb" className="breadcrumb"><span>Content Checks</span><span className="breadcrumb-divider">/</span><span className="font-mono" title="REV-2024-884: Aura Sound ANC Launch Post">REV-2024-884: Aura Sound ANC Launch Post</span></nav><div className="document-context"><span>Aura Audio</span><span>India (IN)</span><span>Instagram Paid</span></div><div className="header-review-badge"><Badge tone={stale ? 'neutral' : conflict ? 'danger' : 'success'}><span className={`status-dot ${conflict && !stale ? 'danger' : ''}`} />{loading ? 'Loading demo…' : !data ? 'Demo workspace' : submitted ? 'Submitted · Demo' : stale ? 'Recheck needed' : conflict ? 'Needs Review (1 Discrepancy)' : 'Ready for Demo Review'}</Badge></div></div>
      <div className="header-actions action-group"><Button onClick={() => void run('recheck')} disabled={!!busy || submitted || loading || !draft}>{busy === 'recheck' ? <LoaderCircle size={15} className="animate-spin" /> : <RefreshCw size={15} />}Recheck with MindVault</Button>{submitButton}</div>
    </ShellHeader>
    {loading ? <StatePanel title="Loading content check" loading>Preparing the sample draft and findings…</StatePanel> : !data || !draft || !result ? error ? <StatePanel title="Could not load the demo" retry={state.retry}><p role="alert">{error}</p><Button onClick={() => changeScenario('default')}>Return to Default</Button></StatePanel> : <StatePanel title="No content checks yet"><p>There are no sample drafts in the empty state.</p><Button variant="primary" onClick={() => changeScenario('default')}><FileText size={14} />Load sample content</Button></StatePanel> : <>
      <section className="document-metadata" aria-labelledby="campaign-title"><div className="campaign-identity"><div className="campaign-icon"><ShieldCheck size={18} /></div><div className="campaign-text"><div className="campaign-title-row"><h1 id="campaign-title" title={data.campaign}>{data.campaign}</h1>{!stale && conflict && <Badge tone="danger">1 Blocker</Badge>}</div><p className="campaign-caption" title={`${draft.id} · Created by ${data.creator} (Growth Marketing) · Rulebook: ${data.rulebook} (Sample)`}><code>{draft.id}</code><span>•</span><span>Created by <strong>{data.creator}</strong> (Growth Marketing)</span><span>•</span><span><RefreshCw size={13} />Rulebook: {data.rulebook} (Sample)</span></p></div></div>
        <fieldset className="metadata-selectors" disabled={!!busy || submitted}><legend className="sr-only">Content targeting</legend>{([
          ['channel', 'Channel', Instagram], ['audience', 'Audience', Users], ['region', 'Region', MapPin], ['language', 'Language', Languages],
        ] as const).map(([field, label, Icon]) => <label className="metadata-select" key={field}><Icon size={14} /><span className="sr-only">{label}</span><select value={draft[field]} onChange={(event) => edit(field, event.target.value)}>{metadataOptions[field].map((option) => <option key={option}>{option}</option>)}</select><ChevronDown size={14} aria-hidden="true" /></label>)}</fieldset>
      </section>
      <div className="page-messages"><div role="status" aria-live="polite">{notice && <div className="notice"><CheckCircle2 size={16} /><span>{notice}</span>{submitted && <Link className="button button-secondary" to={`/approvals?status=pending&q=${encodeURIComponent(draft.id)}`}>View Reviewer Queue</Link>}</div>}</div>{error && <div role="alert" className="error-message">{error}<Button onClick={() => void run('recheck')} disabled={!!busy}>Retry recheck</Button></div>}</div>
      <div className="editor-workspace" aria-busy={!!busy}>
        <section className="editor-area" aria-label="Content draft"><div className="editor-container">
          <div className="editor-toolbar"><div className="file-label"><code>CONTENT_BODY.md</code><span>•</span><span>Primary Feed Caption</span><Button variant="ghost" className="edit-draft-button" onClick={() => setEditing((value) => !value)} disabled={!!busy || submitted} aria-label={editing ? 'Done editing draft' : 'Edit draft'} title={editing ? 'Done editing' : 'Edit draft'}>{editing ? <Check size={14} /> : <Pencil size={14} />}</Button><Link className="button button-ghost edit-draft-button" to={`/content/${encodeURIComponent(draft.id)}/history`} aria-label="Revision Journey" title="View preserved submission history. Unsaved edits are not included."><History size={14} /></Link></div><div className="toolbar-controls">
            <details className="toolbar-popover"><summary><SlidersHorizontal size={13} />Document Specs (3)<ChevronDown size={12} /></summary><div className="popover-content"><strong>Metadata &amp; Spec Sheet</strong><dl><dt>Words</dt><dd>{draftText.trim().split(/\s+/).length}</dd><dt>Characters</dt><dd>{draftText.length.toLocaleString()}</dd><dt>Channel limit</dt><dd>2,200 characters</dd><dt>Asset (sample)</dt><dd>AST-803 (4:5)</dd></dl></div></details>
            <details className="toolbar-popover"><summary><span className="status-dot" />Verified Claims ({stale ? 'Recheck needed' : `${conflict ? 2 : 3}/3 Passed`})<ChevronDown size={12} /></summary><div className="popover-content claims-popover"><strong>Sample claims from design</strong><p className="demo-note">Illustrative statuses, not verified by a real service.</p>{data.claims.map((claim) => <div className="sample-claim" key={claim.label}><span><Check size={14} />{claim.label}</span><small>Matched {claim.source} (mock)</small></div>)}</div></details>
            <button ref={inspectorToggle} className="inspector-toggle" aria-expanded={inspectorOpen} aria-controls="inspector-panel" onClick={() => setInspectorOpen((open) => !open)}><PanelLeft size={14} /><span>Inspector Panel</span></button>
          </div></div>
          <article className="draft-canvas">
            {editing ? <fieldset className="draft-fields" disabled={!!busy}><legend className="sr-only">Edit draft content</legend><label>Headline<textarea value={draft.title} onChange={(event) => edit('title', event.target.value)} rows={2} /></label><label>Introduction<textarea value={draft.introduction} onChange={(event) => edit('introduction', event.target.value)} rows={7} /></label><label>Promotion<textarea value={draft.promotion} onChange={(event) => edit('promotion', event.target.value)} rows={5} /></label></fieldset> : <div className="draft-copy">
              <h2>{draft.title}</h2><p><DraftText text={draft.introduction} highlights={[{ text: mockProductName, kind: 'product' }, ...data.claims.map((claim) => ({ text: claim.label, source: claim.source, kind: 'claim' as const }))]} /></p><p>{draft.promotion.split(/(₹799|₹999)/g).map((part, index) => /^(₹799|₹999)$/.test(part) ? <button key={index} className={`inline-price ${part === '₹999' ? 'corrected' : ''}`} onClick={() => setInspectorOpen(true)} aria-label={`Inspect sample price ${part}`}><span className={`status-dot ${part === '₹799' ? 'danger' : ''}`} />{part}<ArrowRight size={14} /></button> : <span key={index}>{part}</span>)}</p>
            </div>}
            <div className="canvas-hint"><span>Click the price tag to review the sample discrepancy or press Ctrl/⌘ + Enter to Quick Fix.</span><span>Ctrl/⌘ + S to save</span></div>
          </article>
        </div></section>
        {inspectorOpen && <Inspector data={data} conflict={conflict} stale={stale} busy={!!busy} canFix={hasOriginalPrice} submitted={submitted} onClose={closeInspector} onFix={quickFix} onRecheck={() => void run('recheck')} onUndo={() => edit('promotion', draft.promotion.replaceAll(data.finding.replacement, data.finding.original))} />}
      </div>
      <footer className="bottom-action-bar"><span className="save-status"><span className="status-dot" />{busy === 'save' ? 'Saving…' : saved ? 'Saved in this session' : 'Demo draft · Session only'}</span><div className="action-group"><Button disabled={!!busy} onClick={() => void run('save')}>{busy === 'save' && <LoaderCircle size={14} className="animate-spin" />}Save Draft</Button>{submitButton}</div></footer>
    </>}
  </div>;
}
