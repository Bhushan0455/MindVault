import { Component, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { CircleAlert, LoaderCircle, RefreshCw } from 'lucide-react';

export function Button({ variant = 'secondary', className = '', children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' }) {
  return <button type="button" className={`button button-${variant} ${className}`} {...props}>{children}</button>;
}

export function Badge({ tone = 'neutral', children }: { tone?: 'neutral' | 'danger' | 'success'; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function StatePanel({ title, children, loading, retry }: { title: string; children?: ReactNode; loading?: boolean; retry?: () => void }) {
  return <section className="state-panel" aria-live="polite" aria-busy={loading}>
    {loading ? <LoaderCircle className="animate-spin" size={26} /> : <CircleAlert size={26} />}
    <h1>{title}</h1><div>{children}</div>
    {retry && <Button onClick={retry}><RefreshCw size={14} />Try again</Button>}
  </section>;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <StatePanel title="Something went wrong" retry={() => window.location.reload()}>Reload the demo to start again. Session edits will be cleared.</StatePanel>;
    return this.props.children;
  }
}
