import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useOutletContext } from 'react-router-dom';

export interface ShellSlots {
  headerTarget: HTMLDivElement | null;
  demoTarget: HTMLDivElement | null;
}

// Route actions stay in the shared header while retaining their page state.
export function ShellHeader({ children, demoControls }: { children: ReactNode; demoControls: ReactNode }) {
  const { headerTarget, demoTarget } = useOutletContext<ShellSlots>();
  return <>
    {headerTarget && createPortal(children, headerTarget)}
    {demoTarget && createPortal(demoControls, demoTarget)}
  </>;
}
