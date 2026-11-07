import type { RuleSource } from '../types/content-check';
import { useEffect,useRef,useState } from 'react';
import { api,id } from '../api/client';

export function SourceEvidence({ source }: { source: RuleSource }) {
  const [blocks,setBlocks]=useState<{text:string;location:string}[]|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);const generation=useRef(0);
  useEffect(()=>{generation.current++;setBlocks(null);setError('');setBusy(false);return()=>{generation.current++;};},[source.documentId,source.location]);
  async function inspect(){if(!source.documentId||busy)return;const request=++generation.current;setBusy(true);setError('');try{const result=await api.request<{blocks:{text:string;location:string}[]}>(`/sources/${id(source.documentId)}?location=${id(source.location)}`);if(request===generation.current)setBlocks(result.blocks);}catch(reason){if(request===generation.current)setError(reason instanceof Error?reason.message:'Source could not be loaded');}finally{if(request===generation.current)setBusy(false);}}
  return <div className="source-excerpt"><strong>{source.title}</strong><p>“{source.quote}”</p><code>{source.location}</code>{source.documentId?<div className="demo-note"><p>Persisted source excerpt.</p>{source.documentId.startsWith('manual:')?<p>Manually entered knowledge.</p>:<button className="button button-ghost" disabled={busy} onClick={()=>void inspect()}>{busy?'Loading source…':'Inspect original source block'}</button>}{blocks?.map((block,index)=><pre className="source-block" key={index}>{block.text}</pre>)}{error&&<p role="alert">{error}</p>}</div>:<p className="demo-note">Sample excerpt. No original source PDF is supplied; no real AI or compliance service has evaluated this content.</p>}</div>;
}
