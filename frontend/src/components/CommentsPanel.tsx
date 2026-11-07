import { useEffect,useRef,useState } from 'react';
import { api,id,utc } from '../api/client';
import { Button } from './ui';
import { useAuth } from '../auth/AuthContext';
interface Comment {id:string;revision_id:string;user_id:string;user_name?:string;body:string;created_at:string}
export function CommentsPanel({contentId,revisionId}:{contentId:string;revisionId:string}){
  const {user}=useAuth();const [items,setItems]=useState<Comment[]>([]);const [body,setBody]=useState('');const [error,setError]=useState('');const [busy,setBusy]=useState(false);const lock=useRef(false);
  useEffect(()=>{let active=true;void api.request<Comment[]>(`/content/${id(contentId)}/comments`).then(data=>{if(active)setItems(data);}).catch(reason=>{if(active)setError(reason.message);});return()=>{active=false;};},[contentId]);
  async function post(){if(!body.trim()||lock.current)return;lock.current=true;setBusy(true);setError('');try{await api.post(`/content/${id(contentId)}/comments`,{body,revision_id:revisionId});setItems(await api.request<Comment[]>(`/content/${id(contentId)}/comments`));setBody('');}catch(reason){setError(reason instanceof Error?reason.message:'Could not save comment');}finally{lock.current=false;setBusy(false);}}
  return <section className="discussion panel"><header><h2>Discussion</h2><span className="muted">Stored with the selected revision</span></header>{items.length?<ol>{items.map(item=><li key={item.id}><strong>{item.user_name??(item.user_id===user?.id?user.name:'Workspace member')}</strong><time>{new Date(utc(item.created_at)!).toLocaleString()}</time><p>{item.body}</p><small>Revision {item.revision_id.slice(0,8)}</small></li>)}</ol>:<p className="muted">No comments yet.</p>}<label className="field">Add a comment<textarea value={body} maxLength={10000} onChange={event=>setBody(event.target.value)} rows={3}/></label>{error&&<p role="alert" className="error-message">{error}</p>}<Button disabled={busy||!body.trim()} onClick={()=>void post()}>{busy?'Saving…':'Post comment'}</Button></section>;
}
