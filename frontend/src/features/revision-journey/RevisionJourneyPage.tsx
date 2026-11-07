import { useMemo } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeftRight, ExternalLink, TrendingUp } from 'lucide-react';
import { ShellHeader } from '../../components/ShellHeader';
import { Badge, Button, StatePanel } from '../../components/ui';
import type { DemoScenario } from '../../types/content-check';
import type { RevisionJourneyService, JourneyMilestone } from '../../types/revision-journey';
import { buildMilestones, defaultMilestone, defaultVersionPair } from './journey-model';
import { useRevisionJourney } from './useRevisionJourney';
import { RevisionRoadmap } from './RevisionRoadmap';
import { EventInspector } from './EventInspector';
import { VersionComparison } from './VersionComparison';
import './revision-journey.css';

export function RevisionJourneyPage({ service }: { service: RevisionJourneyService }) {
  const { contentId = '' } = useParams();
  return <JourneyWorkspace key={contentId} contentId={contentId} service={service} />;
}

function JourneyWorkspace({ contentId, service }: { contentId: string; service: RevisionJourneyService }) {
  const live=service.mode==='api';
  const { data, loading, error, scenario, setScenario, retry } = useRevisionJourney(contentId, service);
  const [params, setParams] = useSearchParams();
  const milestones = useMemo(() => data ? buildMilestones(data) : [], [data]);
  const selected = params.has('event') ? milestones.find((event) => event.id === params.get('event')) : defaultMilestone(milestones);
  const revision = data?.revisions.find((item) => item.id === selected?.revisionId);
  const current = data?.revisions.find((item) => item.id === data.currentRevisionId);
  const approvals = data?.revisions.filter((item) => item.decision?.kind === 'approved') ?? [];
  const pair = defaultVersionPair(data?.revisions ?? [], selected?.revisionId);
  function choose(event: JourneyMilestone) {
    const next = new URLSearchParams(params); next.set('event', event.id);
    const versions = defaultVersionPair(data?.revisions ?? [], event.revisionId);
    if (versions[0]) next.set('from', versions[0]); else next.delete('from');
    if (versions[1]) next.set('to', versions[1]); else next.delete('to');
    setParams(next, { replace: true, preventScrollReset: true });
  }
  function compareFirstTwo() {
    const versions = [...(data?.revisions ?? [])].sort((a, b) => a.number - b.number);
    const next = new URLSearchParams(params); next.set('from', versions[0]?.id ?? ''); next.set('to', versions[1]?.id ?? ''); setParams(next, { replace: true, preventScrollReset: true });
    document.getElementById('journey-comparison')?.focus();
  }
  function changeVersion(side: 'from' | 'to', id: string) { const next = new URLSearchParams(params); next.set(side, id); setParams(next, { replace: true, preventScrollReset: true }); }
  function resetComparison() { const next = new URLSearchParams(params); next.delete('from'); next.delete('to'); setParams(next, { replace: true, preventScrollReset: true }); }
  const selectedWorkspace = data ? `/approvals/${encodeURIComponent(data.submissionId)}${revision ? `?revision=${encodeURIComponent(revision.id)}` : ''}` : '/approvals';

  return <div className="revision-journey">
    <ShellHeader demoControls={<section className="demo-toolbar" aria-label="History demo controls"><p>History uses the existing revision snapshots and decision journal. AI checks/findings are simulated; inferred workflow steps are labeled.</p><label>Preview state<select value={scenario} onChange={(event) => setScenario(event.target.value as DemoScenario)}><option value="default">Default</option><option value="empty">Empty history</option><option value="error">Error</option></select></label></section>}><span className="sr-only">Revision Journey</span></ShellHeader>
    {loading ? <StatePanel title="Loading Revision Journey" loading>Reading preserved revisions and recorded decisions…</StatePanel> : error ? <StatePanel title="Could not load revision history" retry={retry}><p role="alert">{error}</p><Button onClick={() => setScenario('default')}>Return to Default</Button></StatePanel> : !data ? <StatePanel title="Content history not found"><p>{live?'No stored content is available for this ID and account.':'No submission matches this content ID in the current demo session.'}</p><Link className="button button-primary" to="/approvals">Back to Reviewer Queue</Link></StatePanel> : <>
      <header className="journey-context"><div><nav aria-label="History breadcrumb"><Link to="/approvals">Approvals</Link><span>/</span><Link to={`/approvals/${encodeURIComponent(data.submissionId)}`}>{data.submissionId}: {current?.snapshot.campaign ?? 'Content'}</Link><span>/</span><strong>Revision History</strong></nav><div className="journey-title-row"><h1>{current?.snapshot.title ?? 'Revision Journey'}</h1><Badge tone={current?.status === 'approved' ? 'success' : current?.status === 'changes-requested' ? 'danger' : 'neutral'}>{current ? `${current.status === 'approved' ? 'Approved' : current.status === 'changes-requested' ? 'Changes Requested' : current.status==='draft'?'Draft':current.status==='checked'?'Checked':'Awaiting Review'} · V${current.number} Current` : 'Snapshot unavailable'}</Badge></div></div><div className="action-group"><Button disabled={data.revisions.length < 2} onClick={compareFirstTwo}><ArrowLeftRight size={15} />Compare V1 ↔ V2</Button><Link className="button button-primary" to={selectedWorkspace}><ExternalLink size={15} />View Review Workspace</Link></div></header>
      <section className="journey-roadmap-card" aria-labelledby="roadmap-heading"><header><div><TrendingUp size={18} /><h2 id="roadmap-heading">Revision Roadmap</h2><code>Viewing Revision V{revision?.number ?? current?.number ?? '—'}</code></div><p className="journey-approval-status">{approvals.length ? `Approval recorded for ${approvals.map((item) => `V${item.number}`).join(', ')}` : 'No reviewer approval recorded'}{current?.decision && <span> · Current decision: {new Date(current.decision.decidedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}</p></header>
        {milestones.length ? <RevisionRoadmap milestones={milestones} selectedId={selected?.id} onSelect={choose} /> : <StatePanel title="No history events yet"><p>Available snapshots can be compared below, but no event journal is available.</p>{scenario === 'empty' && <Button onClick={() => setScenario('default')}>Return to Default</Button>}</StatePanel>}
        <p className="journey-provenance">{live?'Milestones use persisted revision, review, submission and approval records. Finding times reflect the completed review that stored them. Approval is tied to its original revision and body hash.':'Creation/check milestones labeled “At submission” are derived from saved snapshots; their independent times were not recorded. Recorded decisions retain their original timestamps. All AI findings are simulated.'}</p>
      </section>
      <div className="journey-detail-grid"><div>{params.has('event') && !selected ? <section className="journey-card"><h2>Event unavailable</h2><p>Select a milestone or reset the event selection.</p><Button onClick={() => { const next = new URLSearchParams(params); next.delete('event'); setParams(next, { replace: true }); }}>Reset event selection</Button></section> : <EventInspector event={selected} revision={revision} submissionId={data.submissionId} />}</div><VersionComparison revisions={data.revisions} beforeId={params.get('from') ?? pair[0]} afterId={params.get('to') ?? pair[1]} onChange={changeVersion} onReset={resetComparison} /></div>
    </>}
  </div>;
}
