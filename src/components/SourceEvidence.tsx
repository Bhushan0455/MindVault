import type { RuleSource } from '../types/content-check';

export function SourceEvidence({ source }: { source: RuleSource }) {
  return <div className="source-excerpt"><strong>{source.title}</strong><p>“{source.quote}”</p><code>{source.location}</code><p className="demo-note">Sample excerpt. No original source PDF is supplied; no real AI or compliance service has evaluated this content.</p></div>;
}
