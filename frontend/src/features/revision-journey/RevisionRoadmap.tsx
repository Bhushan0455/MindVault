import { useRef, type KeyboardEvent } from 'react';
import { BadgeCheck, CircleCheck, FilePenLine, Pencil, Send, Sparkles, TriangleAlert, Undo2, type LucideIcon } from 'lucide-react';
import type { JourneyMilestone } from '../../types/revision-journey';
import { milestoneLabel } from './journey-model';

const icons: Record<JourneyMilestone['kind'], LucideIcon> = { 'draft-created': FilePenLine, 'ai-check': Sparkles, 'finding-detected': TriangleAlert, 'revision-created': Pencil, rechecked: CircleCheck, submitted: Send, approved: BadgeCheck, 'changes-requested': Undo2 };

export function RevisionRoadmap({ milestones, selectedId, onSelect }: { milestones: readonly JourneyMilestone[]; selectedId?: string; onSelect: (event: JourneyMilestone) => void }) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  function move(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === 'ArrowRight' ? Math.min(index + 1, milestones.length - 1) : event.key === 'ArrowLeft' ? Math.max(0, index - 1) : event.key === 'Home' ? 0 : event.key === 'End' ? milestones.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault(); buttons.current[next]?.focus(); buttons.current[next]?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
  }
  return <div className="journey-track-scroll"><ol className="journey-track" aria-label="Revision roadmap">
    {milestones.map((event, index) => {
      const Icon = icons[event.kind];
      const selected = event.id === selectedId;
      return <li key={event.id} className={`journey-milestone journey-kind-${event.kind} ${selected ? 'selected' : ''}`}><button ref={(node) => { buttons.current[index] = node; }} type="button" aria-label={`${milestoneLabel(event)} · V${event.revisionNumber}`} aria-pressed={selected} onClick={() => onSelect(event)} onKeyDown={(key) => move(key, index)}><span className="journey-node"><Icon size={20} /><code>V{event.revisionNumber}</code></span><strong>{milestoneLabel(event)}</strong><span className="journey-event-time">{event.occurredAt !== undefined ? <time dateTime={new Date(event.occurredAt).toISOString()}>{new Date(event.occurredAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time> : 'At submission'}</span>{selected && <span className="journey-selected-tag">Selected</span>}</button></li>;
    })}
  </ol></div>;
}
