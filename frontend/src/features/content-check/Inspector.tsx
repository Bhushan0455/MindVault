import { useRef } from 'react';
import { CheckCircle2, ChevronDown, WandSparkles, X } from 'lucide-react';
import type { ContentCheck } from '../../types/content-check';
import { Badge, Button } from '../../components/ui';
import { SourceEvidence } from '../../components/SourceEvidence';

export function Inspector({ data, conflict, stale, busy, canFix, submitted, onClose, onFix, onRecheck, onUndo }: {
  data: ContentCheck; conflict: boolean; stale: boolean; busy: boolean; canFix: boolean; submitted: boolean;
  onClose: () => void; onFix: () => void; onRecheck: () => void; onUndo: () => void;
}) {
  const sourceDetails = useRef<HTMLDetailsElement>(null);
  function openGuidelines() {
    if (!sourceDetails.current) return;
    sourceDetails.current.open = true;
    sourceDetails.current.querySelector('summary')?.focus();
    sourceDetails.current.scrollIntoView({ block: 'nearest' });
  }
  return <aside className="inspector" id="inspector-panel" aria-label="Content inspector">
    <div className="inspector-content">
      <div className="inspector-heading"><h2>Inspector</h2><Badge tone={stale ? 'neutral' : conflict ? 'danger' : 'success'}>{stale ? 'Recheck needed' : conflict ? '1 Conflict' : '0 Conflicts'}</Badge><Button variant="ghost" onClick={onClose} aria-label="Collapse inspector"><X size={17} /></Button></div>
      <div className={`finding-card ${!conflict && !stale ? 'resolved' : ''}`}>
        {stale ? <>
          <h3>Draft updated</h3><p>Recheck the latest draft to refresh the sample findings.</p>
          <Button variant="primary" onClick={onRecheck} disabled={busy}>Recheck demo draft</Button>
          {!canFix && <Button variant="ghost" onClick={onUndo} disabled={busy}>Undo price correction</Button>}
        </> : conflict ? <>
          <div className="finding-category"><span><i className="status-dot danger" />MAP Compliance</span><code>RULE #{data.finding.ruleId}</code></div>
          <h3>{data.finding.title}</h3>
          <div className="price-comparison"><del>{data.finding.original}</del><span>vs</span><strong>{data.finding.replacement}</strong><small>(Approved MAP)</small></div>
          <Button variant="primary" className="quick-fix" onClick={onFix} disabled={busy || !canFix}><WandSparkles size={15} />Quick Fix (Apply {data.finding.replacement})<kbd>Ctrl/⌘ ↵</kbd></Button>
        </> : <>
          <div className="resolved-title"><CheckCircle2 size={17} />Sample conflict resolved</div><p>The draft no longer contains the sample ₹799 price. The demo is ready for simulated sign-off.</p>
          <Button variant="ghost" onClick={onUndo} disabled={busy || submitted}>Undo price correction</Button>
        </>}
        <details ref={sourceDetails} className="source-details"><summary>Inspect Source &amp; Rules<ChevronDown size={15} /></summary><SourceEvidence source={data.source} /></details>
      </div>
    </div>
    <div className="inspector-footer"><span><i className="status-dot" />{data.rulebook} · Demo</span><button className="guidelines-button" type="button" onClick={openGuidelines}>Guidelines</button></div>
  </aside>;
}
