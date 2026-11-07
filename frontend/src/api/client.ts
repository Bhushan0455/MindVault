export interface User { id:string; org_id:string; org_name:string; name:string; email:string; role:'admin'|'creator'|'reviewer' }
export interface Brand { id:string; name:string }
export interface Context { product:string; channel:string; audience:string; region:string; content_type:string; campaign:string|null; publication_date:string; language?:string|null }
export interface Source { document_id:string; document_title:string; location:string; excerpt:string }
export interface Finding {
  id:string; revision_id:string; origin:string; category:string; severity:string; confidence:number; verdict:string;
  span_start:number; span_end:number; quoted_text:string; explanation:string; suggested_fix:string|null;
  status:string; decision_note:string|null; edited_text:string|null; source:Source|null;
  rule:{id?:string;code:string;version?:number;instruction?:string}|null;
  fact:{id:string;version?:number;value?:string;source_document?:string;location?:string;page?:number|null}|null;
}
export interface Content { id:string; title:string; brand_id:string; status:string; context:Context;
  current_revision:{id:string;number:number;body_text:string;body_hash:string};latest_run_id:string|null;
  created_by:{id:string;name:string};created_at:string;updated_at:string }
export interface Run { id:string; revision_id:string; status:string; progress_step?:string; ai_used:boolean; ai_status:string;
  model:string|null;issues:string[];findings:Finding[];applied_rules:Record<string,unknown>[];skipped_rules:Record<string,unknown>[] }
export interface Person { id:string|null; name:string; email?:string; role?:string|null }
export interface Approval { id:string;revision_id:string;body_hash:string;decision:string;comment:string|null;reviewer:Person;created_at:string }
export interface Revision { id:string;number:number;title:string|null;body_text:string;body_hash:string;context:Context;
  created_at:string;created_by:Person;review_runs:Run[];approvals:Approval[];submitted_at:string|null }
export interface HistoryEvent { id:string;revision_id:string;revision_number:number;kind:string;actor:string;at:string;comment:string;finding_id:string|null }
export interface History { content:Content; revisions:Revision[];events:HistoryEvent[];persisted:true }
export interface Submission { id:string;brand_id:string;brand:string;title:string;status:string;revision_id:string;revision_number:number;
  body_text:string;body_hash:string;context:Context;creator:Person;submitted_at:string;decision_at:string|null;current_revision_id:string;findings:Finding[];ai_status:string }
export interface Document { id:string;brand_id:string;title:string;filename:string;kind:string;version:number;created_at:string;text?:string;content_hash?:string;uploaded_by_name?:string }
export interface Knowledge { id:string;brand_id:string;status:string;version:number;code?:string;instruction?:string;category?:string;severity?:string;
  product?:string;attribute?:string;value_text?:string;value_num?:number|string;unit?:string;market?:string;qualifier?:string;
  scope_channel?:string[];scope_audience?:string[];scope_region?:string[];scope_content_type?:string[];scope_campaign?:string[];
  authority?:string;priority?:number;forbidden_terms?:string[];preferred_terms?:Record<string,string>;required_text?:string|null;
  requires_claim_evidence?:boolean;source_document_id?:string|null;source_location?:string|null;source_excerpt?:string|null;
  effective_from?:string|null;effective_to?:string|null;valid_from?:string|null;valid_to?:string|null }
export interface Candidate { id:string;document_id:string;brand_id:string;kind:'rule'|'fact';status:string;knowledge_id:string|null;
  data:{payload:Record<string,string>;source:Source;method:string;source_start:number;source_end:number} }
export interface ClarityProposal { id:string;rule_id:string;rule_code:string;rule_version:number;kind:string;excerpt:string;why_it_matters:string;
  suggested_rewrite:string;example_good:string;example_bad:string;assumptions:string[];requires_completion:boolean;source:Source;method:string;status:string;accepted_rule_id?:string }
export interface Job { id:string;kind:string;status:string;brand_id:string;result:{method?:string;issues?:string[];candidates?:{rules:string[];facts:string[]};
  findings?:ClarityProposal[];ai_used?:boolean;ai_status?:string;detail?:string;code?:string} }

export class ApiError extends Error {
  constructor(public status:number,public code:string,message:string){ super(message); }
}
type RequestOptions=RequestInit & { anonymous?:boolean };
const storageKey='mindvault.session';
function readToken(){ try{return sessionStorage.getItem(storageKey)??'';}catch{return '';} }
export class ApiClient {
  private token=readToken();
  private generation=0;
  constructor(public base=(import.meta.env.VITE_API_BASE_URL||'/api').replace(/\/$/,'')){}
  hasToken(){return !!this.token;}
  setToken(value:string){this.token=value;this.generation++;try{if(value)sessionStorage.setItem(storageKey,value);else sessionStorage.removeItem(storageKey);}catch{/* Session memory still works. */}if(typeof window!=='undefined')window.dispatchEvent(new Event('mindvault:session-changed'));}
  async request<T>(path:string,{anonymous=false,...options}:RequestOptions={}):Promise<T>{
    const generation=this.generation;
    const headers=new Headers(options.headers);
    if(this.token&&!anonymous)headers.set('Authorization',`Bearer ${this.token}`);
    if(options.body&&!(options.body instanceof FormData))headers.set('Content-Type','application/json');
    const timeout=AbortSignal.timeout(70000);
    const signal=options.signal?AbortSignal.any([options.signal,timeout]):timeout;
    let response:Response;
    try{response=await fetch(this.base+path,{...options,headers,signal,cache:'no-store'});}
    catch(error){if(error instanceof DOMException&&error.name==='AbortError')throw error;throw new ApiError(0,'connection_error','Cannot reach the backend. Check that it is running and try again.');}
    let data:unknown;
    try{data=await response.json();}catch{throw new ApiError(response.status,'invalid_response','The server returned an unreadable response.');}
    if(!anonymous&&generation!==this.generation)throw new ApiError(409,'session_changed','Your session changed; reload this view.');
    if(!response.ok){
      const failure=data as {detail?:string;code?:string};
      if(response.status===401&&!anonymous&&typeof window!=='undefined')window.dispatchEvent(new Event('mindvault:session-expired'));
      throw new ApiError(response.status,failure.code??'request_error',typeof failure.detail==='string'?failure.detail:'The request failed.');
    }
    return data as T;
  }
  post<T>(path:string,data?:unknown){return this.request<T>(path,{method:'POST',body:data===undefined?undefined:JSON.stringify(data)});}
  patch<T>(path:string,data:unknown){return this.request<T>(path,{method:'PATCH',body:JSON.stringify(data)});}
  async poll<T extends {status:string}>(path:string,onProgress?:(value:T)=>void,signal?:AbortSignal):Promise<T>{
    const deadline=Date.now()+195000;
    while(Date.now()<deadline){
      const value=await this.request<T>(path,{signal});onProgress?.(value);
      if(['done','failed','legacy'].includes(value.status))return value;
      await new Promise<void>((resolve,reject)=>{
        const cancel=()=>{clearTimeout(timer);reject(signal?.reason);};
        const timer=setTimeout(()=>{signal?.removeEventListener('abort',cancel);resolve();},1000);
        signal?.addEventListener('abort',cancel,{once:true});
      });
    }
    throw new ApiError(408,'poll_timeout','The job is taking too long. Refresh its status before retrying.');
  }
}
export const api=new ApiClient();
export const id=(value:string)=>encodeURIComponent(value);
const listeners=new Set<()=>void>();
export function invalidate(){for(const listener of listeners)listener();}
export function subscribe(listener:()=>void){listeners.add(listener);return()=>{listeners.delete(listener);};}
export function initials(name:string){return name.split(/\s+/).filter(Boolean).slice(0,2).map(s=>s[0]).join('').toUpperCase();}
export function utc(value:string|null|undefined){if(!value)return undefined;return Date.parse(/(?:Z|[+-]\d\d:\d\d)$/.test(value)?value:value+'Z');}
export function statusLabel(value:string){return ({in_review:'Pending review',approved:'Approved',changes_requested:'Changes requested',draft:'Draft',checked:'Checked',superseded:'Superseded',pending:'Pending approval'})[value]??value.replaceAll('_',' ');}
