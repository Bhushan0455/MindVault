import type { ReactNode } from 'react';
import { CircleCheck } from 'lucide-react';
import type { SubmittedRevision } from '../../types/reviewer-detail';

export function RevisionCopy({ text, revision, onInspect }: { text: string; revision: SubmittedRevision; onInspect: (id: string) => void }) {
  const findings = revision.findings.filter((item) => item.claim && text.toLowerCase().includes(item.claim.toLowerCase()));
  if (!findings.length) return text;
  const pattern = findings.map((item) => item.claim.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  return text.split(new RegExp(`(${pattern})`, 'gi')).map((part, index): ReactNode => {
    const finding = findings.find((item) => item.claim.toLowerCase() === part.toLowerCase());
    return finding ? <button key={index} type="button" className={`review-inline-claim ${finding.severity === 'blocker' ? 'blocker' : finding.id === 'price' ? 'price' : ''}`} aria-label={`Inspect evidence for ${part}`} onClick={() => onInspect(finding.id)}><CircleCheck size={12} />{part}</button> : part;
  });
}
