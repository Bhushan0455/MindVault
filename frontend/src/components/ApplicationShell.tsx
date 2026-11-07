import { useRef, useState, useSyncExternalStore } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { BadgeCheck, Bell, BookOpen, ChevronsUpDown, ClipboardCheck, Gavel, History, LayoutDashboard, Menu, Settings, Terminal, X,FileUp,Sparkles,Database,ChartColumn } from 'lucide-react';
import { Button } from './ui';
import { mockWorkspace } from '../mocks/app-shell';
import type { User } from '../api/client';
import type { ShellSlots } from './ShellHeader';
import type { ReviewerQueueService } from '../types/reviewer-queue';

export const navigation = [
  { group: 'Auditing', items: [
    { label: 'Overview', path: '/overview', icon: LayoutDashboard },
    { label: 'Brand Knowledge', path: '/brand-knowledge', icon: BookOpen },
    { label: 'Upload Documents', path: '/upload', icon: FileUp },
    { label: 'Content Checks', path: '/content-checks', icon: ClipboardCheck },
    { label: 'Approvals', path: '/approvals', icon: BadgeCheck },
  ] },
  { group: 'Governance', items: [
    { label: 'Audit Logs', path: '/audit-logs', icon: History },
    { label: 'Compliance Rules', path: '/compliance-rules', icon: Gavel },
    { label: 'Clarity Audit', path: '/clarity', icon: Sparkles },
    { label: 'Source Files', path: '/sources', icon: Database },
    { label: 'Evaluation', path: '/evaluation', icon: ChartColumn },
    { label: 'Settings', path: '/settings', icon: Settings },
  ] },
];

interface ShellWorkspace {name:string;engineVersion:string;user:{name:string;title:string;initials:string}}
function Sidebar({ onNavigate, approvalCount, historyRoute = false, workspace=mockWorkspace, live=false, role }: { onNavigate?: () => void; approvalCount: number; historyRoute?: boolean; workspace:ShellWorkspace;live:boolean;role?:User['role'] }) {
  return <>
    <div className="workspace-brand"><span className="brand-mark">M</span><div><strong>MindVault AI</strong><span>{workspace.name}</span></div>
      <details className="workspace-switcher shell-popover"><summary aria-label="Workspace details"><ChevronsUpDown size={18} /></summary><div className="shell-popover-content"><strong>{workspace.name}</strong><p>{live?'Your signed-in organisation. Data is stored by the backend.':'This demo contains one sample workspace.'}</p></div></details>
    </div>
    <div className="nav-groups">{navigation.map(({ group, items }) => <div key={group}>
      <p className="nav-label">{group}</p>
      <nav aria-label={group}>{items.filter(item=>!live||role==='admin'||(!['/upload','/clarity','/evaluation'].includes(item.path)&&(role==='reviewer'?!['/content-checks'].includes(item.path):!['/approvals','/audit-logs'].includes(item.path)))).map(({ label, path, icon: Icon }) => <NavLink key={path} to={path} onClick={onNavigate} aria-current={historyRoute && path === '/approvals' ? 'page' : undefined} className={({ isActive }) => `nav-link ${isActive || (historyRoute && path === '/approvals') || (path === '/overview' && location.pathname === '/dashboard') ? 'active' : ''}`}>
        <Icon size={16} /><span>{label}</span>{path === '/content-checks' && <span className="nav-dot" />}{path === '/approvals' && <span className="nav-count" aria-label={`${approvalCount} ${live?'pending':'sample'} approvals`}>{approvalCount}</span>}
      </NavLink>)}</nav>
    </div>)}</div>
    <div className="sidebar-status"><span className="status-dot" /><span>{live?'API connected':`Engine ${workspace.engineVersion} · Demo`}</span><Terminal size={16} /></div>
  </>;
}

export function ApplicationShell({ queueService, profile, workspaceName, live=false, onLogout, role, demo=false }: { queueService: ReviewerQueueService;profile?:{name:string;title:string;initials:string};workspaceName?:string;live?:boolean;onLogout?:()=>void;role?:User['role'];demo?:boolean }) {
  const workspace={...mockWorkspace,name:workspaceName??mockWorkspace.name,user:profile??mockWorkspace.user};
  const dialog = useRef<HTMLDialogElement>(null);
  const [headerTarget, setHeaderTarget] = useState<HTMLDivElement | null>(null);
  const [demoTarget, setDemoTarget] = useState<HTMLDivElement | null>(null);
  const location = useLocation();
  const submissions = useSyncExternalStore(queueService.subscribe, queueService.getSnapshot);
  const approvalCount = submissions.filter((item) => item.status === 'pending').length;
  const detailRoute = location.pathname.startsWith('/approvals/');
  const historyRoute = /^\/content\/[^/]+\/history\/?$/.test(location.pathname);
  const current = (location.pathname === '/dashboard' ? 'Overview' : navigation.flatMap((group) => group.items).find((item) => item.path === location.pathname)?.label) ?? (detailRoute ? 'Approvals' : historyRoute ? 'Revision History' : 'Page not found');
  return <div className={`app-shell ${location.pathname === '/approvals' || detailRoute || historyRoute ? 'reviewer-queue-shell' : ''} ${detailRoute ? 'reviewer-detail-shell' : ''}`}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="desktop-sidebar"><Sidebar workspace={workspace} live={live} role={role} approvalCount={approvalCount} historyRoute={historyRoute} /></aside>
    <dialog ref={dialog} className="mobile-nav" aria-label="Main navigation" onClick={(event) => { if (event.target === event.currentTarget) dialog.current?.close(); }}>
      <Button className="mobile-nav-close" variant="ghost" onClick={() => dialog.current?.close()} aria-label="Close navigation"><X size={20} /></Button>
      <Sidebar workspace={workspace} live={live} role={role} approvalCount={approvalCount} historyRoute={historyRoute} onNavigate={() => dialog.current?.close()} />
    </dialog>
    <div className="app-body">
      <header className="app-header">
        <Button variant="ghost" className="menu-toggle" aria-label="Open navigation" onClick={() => dialog.current?.showModal()}><Menu size={20} /></Button>
        <div ref={setHeaderTarget} className="header-route-slot" data-empty-label={current} />
        <div className="header-account">
          <details className="shell-popover notifications-menu"><summary aria-label="Notifications"><Bell size={18} /><span className="notification-dot" /></summary><div className="shell-popover-content"><strong>Notifications</strong><p>{live?'Review queue, history and audit pages show the latest persisted activity.':'No new notifications in this demo session.'}</p></div></details>
          <details className="shell-popover profile-menu"><summary aria-label={live?"Profile":"Profile and demo controls"}><span className="avatar" aria-hidden="true">{workspace.user.initials}</span><span className="account-text"><strong>{workspace.user.name}</strong><span>{workspace.user.title}</span></span></summary><div className="shell-popover-content"><strong>{workspace.user.name}</strong><p>{workspace.user.title} · {live?(demo?'Demo data':'Signed in'):'Demo session'}</p>{!live&&<div ref={setDemoTarget} />}{!live&&current !== 'Content Checks' && <p>All workspace data is simulated.</p>}{live&&onLogout&&<Button onClick={onLogout}>Sign out</Button>}</div></details>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}><Outlet context={{ headerTarget, demoTarget } satisfies ShellSlots} /></main>
    </div>
  </div>;
}
