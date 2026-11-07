import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCheck, ChevronDown, ClipboardList, Download, FolderPen, Grid2X2, RotateCcw, Search, Shield, ShieldCheck, SlidersHorizontal, SortDesc, type LucideIcon } from 'lucide-react';
import { ShellHeader } from '../../components/ShellHeader';
import { Badge, Button, StatePanel } from '../../components/ui';
import { Modal } from '../../components/Modal';
import type { DemoScenario } from '../../types/content-check';
import type { ReviewerQueueService } from '../../types/reviewer-queue';
import { filterQueue, paginateQueue, queueCsv, queueMetrics, readQueueFilters } from './queue-query';
import { useReviewerQueue } from './useReviewerQueue';
import { QueueTable } from './QueueTable';
import { SubmissionPreview } from './SubmissionPreview';
import './reviewer-queue.css';

function Metric({ title, amount, detail, tone, icon: Icon }: { title: string; amount: number | string; detail: string; tone: string; icon: LucideIcon }) {
  return <div className="queue-metric"><span className={`queue-metric-icon ${tone}`}><Icon size={18} /></span><div><h2>{title}</h2><p><strong>{amount}</strong><span>{detail}</span></p></div></div>;
}

export function ReviewerQueuePage({ service }: { service: ReviewerQueueService }) {
  const live=service.mode==='api';
  const { records, loading, error, scenario, setScenario, retry } = useReviewerQueue(service);
  const [params, setParams] = useSearchParams();
  const filters = readQueueFilters(params);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [policyOpen, setPolicyOpen] = useState(false);
  const [notice, setNotice] = useState('');
  const searchInput = useRef<HTMLInputElement>(null);
  const metrics = queueMetrics(records, Date.now(), service.getHistory());
  const filtered = useMemo(() => filterQueue(records, readQueueFilters(params)), [records, params]);
  const pagination = paginateQueue(filtered, filters);
  const brands = [...new Set(records.map((item) => item.brand))].sort();
  const channels = [...new Set(records.map((item) => item.channel))].sort();
  const selectedSubmission = records.find((item) => item.id === params.get('submission'));

  function update(key: string, value: string, resetPage = true) {
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(key, value); else next.delete(key);
      if (resetPage) next.delete('page');
      return next;
    }, { replace: true, preventScrollReset: true });
    setNotice('');
  }
  function resetFilters() { setParams(filters.pageSize === 5 ? {} : { size: String(filters.pageSize) }, { replace: true, preventScrollReset: true }); setNotice(''); }
  function selection(id: string, checked: boolean) { setSelected((current) => { const next = new Set(current); if (checked) next.add(id); else next.delete(id); return next; }); }
  function selectPage(checked: boolean) { setSelected((current) => { const next = new Set(current); pagination.rows.forEach((item) => checked ? next.add(item.id) : next.delete(item.id)); return next; }); }
  function submissionHref(id: string) { const next = new URLSearchParams(params); next.delete('submission');const target=new URLSearchParams();if(next.size)target.set('queue',next.toString());if(live){const record=records.find(item=>item.id===id);if(record?.revisionId)target.set('revision',record.revisionId);}return `/approvals/${encodeURIComponent(id)}${target.size?`?${target}`:''}`; }
  function changeScenario(value: DemoScenario) { setSelected(new Set()); setNotice(''); setScenario(value); }
  function exportLog() {
    const exported = selected.size ? records.filter((item) => selected.has(item.id)) : filtered;
    const blob = new Blob(['\uFEFF', queueCsv(exported)], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = live?'mindvault-submissions.csv':'mindvault-demo-queue.csv'; document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(URL.revokeObjectURL.bind(URL, url), 1000);
    setNotice(`Exported ${exported.length} ${live?'persisted':'simulated'} submissions${selected.size ? ' selected across queue pages' : ' matching the current filters'}.`);
  }

  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && !document.querySelector('dialog[open]')) { event.preventDefault(); searchInput.current?.focus(); }
    }
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, []);

  return <div className="reviewer-queue">
    <ShellHeader demoControls={<section className="demo-toolbar" aria-label="Queue demo controls"><p>Queue data and verification statuses are simulated. No live services are connected.</p><label>Preview state<select value={scenario} onChange={(event) => changeScenario(event.target.value as DemoScenario)}><option value="default">Default</option><option value="empty">Empty</option><option value="error">Error</option></select></label></section>}><span className="sr-only">Reviewer Queue</span></ShellHeader>
    <section className="queue-overview" aria-labelledby="queue-title"><div className="queue-title-bar"><div><div className="queue-title-line"><h1 id="queue-title">Approvals</h1><Badge><span className="queue-active-dot" />{loading ? 'Loading Queue' : error ? 'Queue Unavailable' : 'Queue Active'}</Badge></div><p>Review and approve submitted marketing collateral across active brand campaigns</p></div><div className="action-group"><Button onClick={() => setSettingsOpen(true)}><SlidersHorizontal size={16} />Queue Settings</Button><Button onClick={exportLog} disabled={loading || !!error || (!selected.size && !filtered.length)}><Download size={16} />Export Audit Log</Button></div></div>
      <div className="queue-metrics" aria-busy={loading}><Metric title="Pending Review" amount={loading ? '—' : metrics.pending} detail={`${metrics.urgent} urgent`} tone="pending" icon={ClipboardList} /><Metric title="Changes Requested" amount={loading ? '—' : metrics.changes} detail="In creator loop" tone="changes" icon={FolderPen} /><Metric title="Approved Today" amount={loading ? '—' : metrics.approvedToday} detail={live?'Latest recorded approvals':`${metrics.approvalDelta >= 0 ? '+' : ''}${metrics.approvalDelta} vs yesterday (mock)`} tone="approved" icon={CheckCheck} /><Metric title="Total Reviewed" amount={loading ? '—' : metrics.reviewed} detail={live?"Current reviewed snapshots":"This sprint (mock)"} tone="total" icon={Grid2X2} /></div>
    </section>
    <section className="queue-filters" aria-label="Filter submissions"><div className="queue-filter-top"><div className="queue-segments" role="group" aria-label="Submission status">{([
      ['pending', 'Pending', metrics.pending], ['changes-requested', 'Changes Requested', metrics.changes], ['approved', 'Approved', metrics.approved], ['all', 'All Submissions', metrics.all],
    ] as const).map(([value, label, count]) => <button key={value} type="button" aria-pressed={filters.status === value} onClick={() => update('status', value)}><span>{label}</span><span className={`queue-tab-count ${value === 'pending' ? 'pending' : ''}`}>{count}</span></button>)}</div><div className="queue-engine"><span className="status-dot" />{live?'Persisted review queue':'Auto-eval Engine v4.12 · Demo'}<span className="queue-divider">|</span><code>{live?'Human reviewer decisions':'SLA: 4h target'}</code></div></div>
      <div className="queue-filter-inputs"><label className="queue-search"><Search size={17} /><span className="sr-only">Search submissions</span><input ref={searchInput} type="search" value={filters.search} placeholder="Search by content title, reference ID, or submitter..." onChange={(event) => update('q', event.target.value)} /><kbd aria-hidden="true">Ctrl/⌘ K</kbd></label><div className="queue-filter-selects">
        <label className="queue-select"><span>Brand:</span><select aria-label="Brand" value={filters.brand} onChange={(event) => update('brand', event.target.value)}><option value="">All Brands</option>{brands.map((brand) => <option key={brand}>{brand}</option>)}</select><ChevronDown size={14} /></label>
        <label className="queue-select"><span>Channel:</span><select aria-label="Channel" value={filters.channel} onChange={(event) => update('channel', event.target.value)}><option value="">All Channels</option>{channels.map((channel) => <option key={channel}>{channel}</option>)}</select><ChevronDown size={14} /></label>
        <label className="queue-select"><span>Severity:</span><select aria-label="Severity" value={filters.severity} onChange={(event) => update('severity', event.target.value)}><option value="all">All Conflict Levels</option><option value="blocker">Blockers</option><option value="warning">Warnings</option><option value="advisory">Advisories</option><option value="none">No Conflicts</option></select><ChevronDown size={14} /></label>
        <span className="queue-divider">|</span><label className="queue-select"><SortDesc size={15} /><select aria-label="Sort submissions" value={filters.sort} onChange={(event) => update('sort', event.target.value)}><option value="newest">Newest First</option><option value="oldest">Oldest First</option><option value="severity">Conflict Level</option></select><ChevronDown size={14} /></label><Button onClick={resetFilters} aria-label="Reset all filters" title="Reset Filters"><RotateCcw size={16} /></Button>
      </div></div>
    </section>
    <div className="queue-feedback" role="status" aria-live="polite">{notice}</div>
    <div className="queue-results" aria-busy={loading}>
      {loading ? <StatePanel title="Loading Reviewer Queue" loading>{live?'Loading stored submissions…':'Preparing the simulated submissions…'}</StatePanel> : error ? <StatePanel title="Could not load the queue" retry={retry}><p role="alert">{error}</p><Button onClick={() => changeScenario('default')}>Return to Default</Button></StatePanel> : !records.length ? <StatePanel title="No submissions yet"><p>{live?'Creator submissions appear here after a completed review and submission.':'Creator submissions will appear here after a successful demo submission. Empty preview mode hides session data without deleting it.'}</p>{!live&&<Button onClick={() => changeScenario('default')}>Load demo submissions</Button>}</StatePanel> : !filtered.length ? <StatePanel title="No matching submissions"><p>Try another search term or clear your filters.</p><Button onClick={resetFilters}>Clear filters</Button></StatePanel> : <QueueTable {...pagination} total={filtered.length} selected={selected} onSelect={selection} onSelectPage={selectPage} href={submissionHref} onPage={(page) => update('page', String(page), false)} />}
    </div>
    <section className="queue-policy"><div className="queue-policy-icon"><ShieldCheck size={18} /></div><div><h2>{live?'High-risk findings need an explicit resolution':'Need to override a high-risk MAP or ASCI blocker?'}</h2><p>{live?'Fix and recheck high-risk findings, or record a rejection reason for reviewer assessment. Final approval belongs to an exact saved revision.':'Content items flagged with blockers require dual-signature authorization from Legal Compliance and Marketing Director before publishing credentials are released.'}</p></div><Button onClick={() => setPolicyOpen(true)}><Shield size={16} />{live?'View approval policy':'View Dual-Sign Policy'}</Button></section>
    <SubmissionPreview submission={selectedSubmission} open={!loading && !error && params.has('submission')} onClose={() => { if (params.has('submission')) update('submission', '', false); }} />
    <Modal open={settingsOpen} title="Queue settings" onClose={() => setSettingsOpen(false)}><p>{live?'Display preferences are stored in this queue URL.':'Display preferences apply to this demo queue URL.'}</p><label className="queue-settings-field">Rows per page<select value={filters.pageSize} onChange={(event) => update('size', event.target.value)}><option value="5">5</option><option value="10">10</option><option value="20">20</option></select></label><Button onClick={() => { setSelected(new Set()); setNotice('Selection cleared.'); }}>Clear selected submissions</Button><Button variant="primary" onClick={() => setSettingsOpen(false)}>Done</Button></Modal>
    <Modal open={policyOpen} title="Dual-sign policy" onClose={() => setPolicyOpen(false)}><p>{live?'Unresolved critical/high findings must be fixed and rechecked, or explicitly rejected with a reason visible to the reviewer. Approval binds an exact revision and hash.':'This sample policy mirrors the approved Stitch callout: high-risk blockers require Legal Compliance and Marketing Director sign-off before publishing.'}</p><p className="queue-preview-disclaimer">{live?'The backend enforces roles and revision checks. External signatures and publishing connectors are not configured.':'Demo guidance only. No signatures, overrides or publishing credentials are issued by this frontend.'}</p></Modal>
  </div>;
}
