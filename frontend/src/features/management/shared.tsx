import { useEffect,useRef,useState,type ReactNode } from 'react';
import { api } from '../../api/client';
import { Button } from '../../components/ui';
import { ShellHeader } from '../../components/ShellHeader';
import { useWorkspace } from '../../workspace/WorkspaceContext';

export function useResource<T>(path:string|null){
  const [data,setData]=useState<T>();const [error,setError]=useState('');const [loading,setLoading]=useState(true);const [version,setVersion]=useState(0);
  useEffect(()=>{let active=true;setData(undefined);setLoading(!!path);setError('');if(!path){return;}
    void api.request<T>(path).then(value=>{if(active)setData(value);}).catch(reason=>{if(active)setError(reason.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};
  },[path,version]);
  return {data,error,loading,refresh:()=>setVersion(value=>value+1)};
}
export function useAction(){
  const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const lock=useRef(false);
  async function run(task:()=>Promise<void>,success='Saved to the database.'){if(lock.current)return false;lock.current=true;setBusy(true);setError('');setNotice('');
    try{await task();setNotice(success);return true;}catch(reason){setError(reason instanceof Error?reason.message:'The action failed.');return false;}finally{lock.current=false;setBusy(false);}}
  return {busy,error,notice,run,setError};
}
export function Feedback({error,notice}:{error?:string;notice?:string}){return <>{error&&<p role="alert" className="error-message">{error}</p>}{notice&&<p role="status" className="notice">{notice}</p>}</>;}
export function Page({title,subtitle,children,actions,brand=true}:{title:string;subtitle:string;children:ReactNode;actions?:ReactNode;brand?:boolean}){
  const workspace=useWorkspace();return <div className="management-page"><ShellHeader><nav className="breadcrumb"><span>Workspace</span><span>/</span><strong>{title}</strong></nav></ShellHeader><header className="management-heading"><div><span className="eyebrow">MindVault workspace</span><h1>{title}</h1><p>{subtitle}</p></div><div className="action-group">{brand&&<label className="field inline-field">Brand<select aria-label="Active brand" value={workspace.brandId} onChange={e=>workspace.setBrandId(e.target.value)}>{workspace.brands.map(item=><option value={item.id} key={item.id}>{item.name}</option>)}</select></label>}{actions}</div></header>{children}</div>;
}
export function Empty({children}:{children:ReactNode}){return <div className="empty-inline">{children}</div>;}
export function Refresh({onClick}:{onClick:()=>void}){return <Button onClick={onClick}>Refresh</Button>;}
