import type { ReactNode } from 'react';

interface TextHighlight {
  text: string;
  kind: 'product' | 'claim';
  source?: string;
}

// Render text nodes rather than editable HTML, so draft edits remain safe.
export function DraftText({ text, highlights }: { text: string; highlights: readonly TextHighlight[] }) {
  const escaped = highlights.map((item) => item.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!escaped.length) return text;
  return text.split(new RegExp(`(${escaped.join('|')})`, 'gi')).map((part, index): ReactNode => {
    const highlight = highlights.find((item) => item.text.toLowerCase() === part.toLowerCase());
    if (!highlight) return part;
    return <span key={index} className={`draft-highlight-${highlight.kind}`} title={highlight.source ? `Sample reference: ${highlight.source}` : undefined}>{part}</span>;
  });
}
