// @vitest-environment jsdom
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter} from 'react-router-dom';
import {ConnectedContentCheckPage} from './ConnectedContentCheckPage';
import {api} from '../../api/client';
vi.mock('../../auth/AuthContext',()=>({useAuth:()=>({user:{name:'Test creator'},health:{demo_mode:true}})}));
vi.mock('../../components/ShellHeader',()=>({ShellHeader:({children}:{children:React.ReactNode})=><header>{children}</header>}));
const context={product:'Veyra Beat 200',channel:'instagram',audience:'consumer',region:'IN',content_type:'paid_ad',campaign:null,publication_date:'2026-11-06',language:'English'};
const content={id:'c',title:'Saved caption',brand_id:'b',status:'checked',context,current_revision:{id:'v1',number:1,body_text:'🎧 ₹799 today',body_hash:'hash'},latest_run_id:'r',created_by:{id:'creator',name:'Test creator'}};
const finding={id:'f',revision_id:'v1',origin:'deterministic',category:'price',severity:'critical',confidence:1,verdict:'violation',span_start:2,span_end:6,quoted_text:'₹799',explanation:'Approved price is ₹999.',suggested_fix:'₹999',status:'accepted',decision_note:null,edited_text:null,source:null,rule:null,fact:{id:'fact'}};
function setup(existing=false){
  api.setToken('test');
  const fetcher=vi.fn(async(input:RequestInfo|URL,options?:RequestInit)=>{
    const path=String(input).replace('/api','');
    if(options?.method==='POST'&&path.includes('/revisions'))return new Response(JSON.stringify({detail:'Another editor saved a newer revision.',code:'revision_conflict'}),{status:409});
    const value=path==='/brands'?[{id:'b',name:'Demo brand'}]:path==='/facts'?[]:path==='/content'?(existing?[content]:[]):path==='/content/c'?content:path==='/review-runs/r'?{id:'r',revision_id:'v1',status:'done',ai_used:false,ai_status:'disabled',issues:[],findings:[finding],applied_rules:[],skipped_rules:[]}:null;
    if(value===null)throw new Error('Unexpected endpoint '+path);
    return new Response(JSON.stringify(value));
  });
  vi.stubGlobal('fetch',fetcher);render(<MemoryRouter initialEntries={[existing?'/content-checks?content=c':'/content-checks']}><ConnectedContentCheckPage/></MemoryRouter>);
  return {user:userEvent.setup(),fetcher};
}
afterEach(()=>{cleanup();vi.unstubAllGlobals();api.setToken('');});
it('warns before discarding a new unsaved draft and keeps its text when cancelled',async()=>{
  const {user}=setup();await screen.findByRole('option',{name:'Demo brand'});
  await user.type(screen.getByLabelText('Draft title'),'My unsaved caption');await user.type(screen.getByLabelText('Content'),'My original text');
  const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);await user.click(screen.getByRole('button',{name:'New draft'}));
  expect(confirm).toHaveBeenCalledOnce();expect((screen.getByLabelText('Content') as HTMLTextAreaElement).value).toBe('My original text');confirm.mockRestore();
});
it('preserves an edited draft when the server rejects a stale revision',async()=>{
  const {user,fetcher}=setup(true);await screen.findByRole('heading',{name:'Saved caption'});
  await user.click(screen.getByRole('button',{name:'Edit draft'}));await user.type(screen.getByLabelText('Content'),' changed');
  await user.click(screen.getByRole('button',{name:'Save Draft'}));await screen.findByRole('alert');
  expect(screen.getByRole('alert').textContent).toContain('Another editor saved');
  expect((screen.getByLabelText('Content') as HTMLTextAreaElement).value).toBe('🎧 ₹799 today changed');
  const save=fetcher.mock.calls.find(([,options])=>options?.method==='POST');expect(JSON.parse(String(save?.[1]?.body)).expected_revision_id).toBe('v1');
});
it('retains the accepted price blocker and enables apply rather than submission',async()=>{
  setup(true);await screen.findByRole('heading',{name:'Saved caption'});
  await waitFor(()=>expect(screen.getAllByRole('button',{name:'Submit for Approval'}).every(button=>(button as HTMLButtonElement).disabled)).toBe(true));
  expect((screen.getByRole('button',{name:'Apply accepted fixes & recheck'}) as HTMLButtonElement).disabled).toBe(false);
  expect(screen.getByText('₹799',{selector:'button.inline-price'})).toBeTruthy();
});
