import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BadgeCheck, ChevronLeft, ChevronRight, CircleCheck, FileClock, Flag, Images, TriangleAlert } from 'lucide-react';
import { Button } from '../../components/ui';
import type { QueueSubmission } from '../../types/reviewer-queue';

function relativeTime(timestamp: number): string {
  const minutes = Math.max(0, Math.floor((Date.now() - timestamp) / 60_000));
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes} min${minutes === 1 ? '' : 's'} ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} hours ago`;
  if (minutes < 2880) return 'Yesterday';
  return `${Math.floor(minutes / 1440)} days ago`;
}

export function QueueTable({ rows, selected, onSelect, onSelectPage, href, page, pages, start, end, total, onPage }: {
  rows: readonly QueueSubmission[]; selected: ReadonlySet<string>; onSelect: (id: string, checked: boolean) => void; onSelectPage: (checked: boolean) => void; href: (id: string) => string;
  page: number; pages: number; start: number; end: number; total: number; onPage: (page: number) => void;
}) {
  const selectAll = useRef<HTMLInputElement>(null);
  const selectedOnPage = rows.filter((row) => selected.has(row.id)).length;
  useEffect(() => { if (selectAll.current) selectAll.current.indeterminate = selectedOnPage > 0 && selectedOnPage < rows.length; }, [selectedOnPage, rows.length]);
  return <div className="queue-table-card">
    <div className="queue-table-scroll" role="region" aria-label="Submissions table — scroll horizontally for status and actions" tabIndex={0}>
      <table className="queue-table"><caption className="sr-only">Simulated marketing submissions awaiting or completing review</caption><colgroup><col className="selection-column" /><col className="asset-column" /><col className="brand-column" /><col className="submitter-column" /><col className="channel-column" /><col className="date-column" /><col className="status-column" /><col className="action-column" /></colgroup>
        <thead><tr><th scope="col"><input ref={selectAll} type="checkbox" aria-label="Select all submissions on this page" checked={rows.length > 0 && selectedOnPage === rows.length} onChange={(event) => onSelectPage(event.target.checked)} /></th><th scope="col">Content Asset &amp; ID</th><th scope="col">Brand</th><th scope="col">Submitted By</th><th scope="col">Channel &amp; Region</th><th scope="col">Submitted</th><th scope="col">Verification Status</th><th scope="col" className="queue-action-cell">Action</th></tr></thead>
        <tbody>{rows.map((item) => {
          const Icon = item.status === 'approved' ? CircleCheck : item.status === 'changes-requested' ? FileClock : item.severity === 'blocker' ? TriangleAlert : item.severity === 'none' ? BadgeCheck : TriangleAlert;
          const tone = item.status === 'approved' ? 'approved' : item.status === 'changes-requested' ? 'changes' : item.severity;
          const action = item.status === 'approved' ? 'View Report' : item.status === 'changes-requested' ? 'View Feedback' : item.severity === 'blocker' ? 'Review & Fix' : 'Review Draft';
          return <tr key={item.id} className={item.severity === 'blocker' ? 'queue-blocker-row' : undefined}>
            <td><input type="checkbox" aria-label={`Select ${item.id}`} checked={selected.has(item.id)} onChange={(event) => onSelect(item.id, event.target.checked)} /></td>
            <td><div className="queue-asset-title"><span className={`queue-row-icon queue-tone-${tone}`} aria-hidden="true"><Icon size={13} /></span><Link to={href(item.id)} title={item.title} preventScrollReset>{item.title}</Link></div><div className="queue-asset-meta"><span>{item.id}</span><i>•</i><span>{item.campaign}</span><i>•</i><span><Images size={12} />{item.assetDescription}</span></div></td>
            <td><span className="queue-brand"><i className={`queue-brand-dot ${item.brand === 'Solace Home' ? 'solace' : item.brand === 'Lumina Skincare' ? 'lumina' : ''}`} />{item.brand}</span></td>
            <td><div className="queue-submitter"><span className="queue-person-avatar">{item.submittedBy.initials}</span><div><span>{item.submittedBy.name}</span><small>{item.submittedBy.team}</small></div></div></td>
            <td><span className="queue-cell-main">{item.channel}</span><small className="queue-cell-secondary"><Flag size={12} />{item.region}</small></td>
            <td><time dateTime={new Date(item.submittedAt).toISOString()} title={new Date(item.submittedAt).toLocaleString()}><span className="queue-cell-main">{relativeTime(item.submittedAt)}</span><small className="queue-cell-secondary font-mono">{new Date(item.submittedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small></time></td>
            <td><span className={`queue-verification queue-tone-${tone}`}><span className="status-dot" />{item.statusLabel}</span><small title={item.summary} className={`queue-status-summary ${item.severity === 'blocker' ? 'danger-text' : ''}`}>{item.summary}</small></td>
            <td className="queue-action-cell"><Link to={href(item.id)} className={`button button-${item.status === 'pending' ? 'primary' : 'secondary'}`} aria-label={`${action}: ${item.id}`} preventScrollReset>{action}{item.status === 'pending' && <ArrowRight size={14} />}</Link></td>
          </tr>;
        })}</tbody>
      </table>
    </div>
    <div className="queue-table-footer"><div className="queue-feed"><span className="status-dot" /><code>Simulated verification feed · No live services</code><span className="queue-result-count" role="status">Showing <strong>{start}–{end}</strong> of <strong>{total}</strong> submissions{selected.size > 0 && ` · ${selected.size} selected`}</span></div>
      <nav className="queue-pagination" aria-label="Queue pages"><Button disabled={page === 1} aria-label="Previous page" onClick={() => onPage(page - 1)}><ChevronLeft size={14} />Prev</Button>{Array.from({ length: pages }, (_, index) => index + 1).filter((value) => value === 1 || value === pages || Math.abs(value - page) <= 1).map((value) => <Button key={value} variant={page === value ? 'primary' : 'secondary'} aria-label={`Page ${value}`} aria-current={page === value ? 'page' : undefined} onClick={() => onPage(value)}>{value}</Button>)}<Button disabled={page === pages} aria-label="Next page" onClick={() => onPage(page + 1)}>Next<ChevronRight size={14} /></Button></nav>
    </div>
  </div>;
}
