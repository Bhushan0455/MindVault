import { createContext,useCallback,useContext,useEffect,useState,type ReactNode } from 'react';
import { api,invalidate,type User } from '../api/client';
import { Button,StatePanel } from '../components/ui';

export interface Health { status:string;db:boolean;ai_configured:boolean;semantic_enabled:boolean;demo_mode:boolean;ai_verification_scope?:string }
interface Auth { user:User|null;health:Health|null;logout:()=>void;refresh:()=>Promise<void> }
const AuthContext=createContext<Auth|null>(null);
export function useAuth(){const context=useContext(AuthContext);if(!context)throw new Error('Authentication provider missing');return context;}
export function useOptionalAuth(){return useContext(AuthContext);}

export function AuthProvider({children}:{children:ReactNode}){
  const [user,setUser]=useState<User|null>(null);const [health,setHealth]=useState<Health|null>(null);
  const [setup,setSetup]=useState(false);const [loading,setLoading]=useState(true);const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const logout=useCallback(()=>{api.setToken('');setUser(null);invalidate();},[]);
  const refresh=useCallback(async()=>{
    setLoading(true);setError('');
    try{const [h,s]=await Promise.all([api.request<Health>('/health',{anonymous:true}),api.request<{setup_required:boolean}>('/setup',{anonymous:true})]);setHealth(h);setSetup(s.setup_required);
      if(api.hasToken())setUser(await api.request<User>('/me'));
    }catch(reason){setError(reason instanceof Error?reason.message:'Unable to connect');}
    finally{setLoading(false);}
  },[]);
  useEffect(()=>{void refresh();window.addEventListener('mindvault:session-expired',logout);return()=>window.removeEventListener('mindvault:session-expired',logout);},[refresh,logout]);
  async function signIn(event:React.FormEvent<HTMLFormElement>){
    event.preventDefault();if(busy)return;setBusy(true);setError('');
    const values=Object.fromEntries(new FormData(event.currentTarget).entries());
    try{const payload=setup?{...values,role:'admin'}:values;
      const result=await api.request<{token:string;user:User}>(setup?'/setup':'/auth/login',{method:'POST',anonymous:true,body:JSON.stringify(payload)});
      api.setToken(result.token);setUser(result.user);setSetup(false);invalidate();
    }catch(reason){setError(reason instanceof Error?reason.message:'Sign-in failed');}finally{setBusy(false);}
  }
  async function demo(role:User['role']){
    if(busy)return;setBusy(true);setError('');
    try{const result=await api.request<{token:string;user:User}>(`/auth/demo?role=${role}`,{method:'POST',anonymous:true});api.setToken(result.token);setUser(result.user);invalidate();}
    catch(reason){setError(reason instanceof Error?reason.message:'Sign-in failed');}finally{setBusy(false);}
  }
  if(loading)return <div className="auth-page"><StatePanel title="Connecting to MindVault" loading>Checking your workspace and saved session…</StatePanel></div>;
  if(!user)return <div className="auth-page"><div className="auth-story"><span className="auth-brand"><b>M</b> MindVault AI</span><span className="eyebrow">A single source of brand truth</span><h1>Every claim.<br/>Backed by evidence.</h1><p>Bring your documents, check your content, and approve the exact revision your team reviewed.</p><div className="auth-benefits"><span>01 · Approved brand knowledge</span><span>02 · Context-aware checks</span><span>03 · Traceable human decisions</span></div></div><section className="auth-card"><span className="eyebrow">Your workspace</span><h2>{setup?'Create your workspace':'Welcome back'}</h2><p>{setup?'Set up the first administrator and brand.':'Sign in to continue to MindVault.'}</p>
    <form onSubmit={event=>void signIn(event)}>{setup&&<><label>Organisation<input name="organisation" required maxLength={120}/></label><label>Brand<input name="brand" required maxLength={120}/></label><label>Your name<input name="name" required maxLength={120}/></label></>}
      <label>Email<input name="email" type="email" required autoComplete="username"/></label><label>Password<input name="password" type="password" required minLength={setup?10:1} autoComplete={setup?'new-password':'current-password'}/></label>
      {error&&<p className="error-message" role="alert">{error}</p>}<button className="button button-primary" disabled={busy}>{busy?'Connecting…':setup?'Create workspace':'Sign in'}</button>
    </form>{health?.demo_mode&&!setup&&<div className="demo-signin"><span>Fictional demo workspace</span><p>Explore with a server-authorised test account. Uploaded documents and decisions still persist in the database.</p><div>{(['admin','creator','reviewer'] as const).map(role=><Button disabled={busy} key={role} onClick={()=>void demo(role)}>Continue as {role}</Button>)}</div></div>}
    {error&&<Button onClick={()=>void refresh()} disabled={busy}>Retry connection</Button>}</section></div>;
  return <AuthContext.Provider value={{user,health,logout,refresh}}><div key={user.id}>{children}</div></AuthContext.Provider>;
}
