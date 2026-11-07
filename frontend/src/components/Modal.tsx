import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { Button } from './ui';

export function Modal({ open, title, onClose, children, className = '' }: { open: boolean; title: string; onClose: () => void; children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  const headingId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog?.open) dialog?.showModal();
    else if (!open && dialog?.open) dialog.close();
  }, [open]);
  return <dialog ref={ref} className={`queue-dialog ${className}`} aria-labelledby={headingId} onCancel={(event) => { event.preventDefault(); onClose(); }} onClose={onClose} onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="queue-dialog-heading"><h2 id={headingId}>{title}</h2><Button variant="ghost" aria-label={`Close ${title.toLowerCase()}`} onClick={onClose}><X size={18} /></Button></div>
    <div className="queue-dialog-body">{children}</div>
  </dialog>;
}
