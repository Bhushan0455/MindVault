// @vitest-environment jsdom
import {afterEach,describe,expect,it,vi} from 'vitest';
import {ApiClient,ApiError,utc,type Finding} from './client';
import {exactSegments} from '../features/content-check/ConnectedContentCheckPage';
import {severity,sourceView} from '../services/api-workspace-services';
afterEach(()=>{vi.unstubAllGlobals();sessionStorage.clear();});
describe('Live API boundary',()=>{
  it('sends the actual bearer token and JSON payload',async()=>{
    const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify({id:'saved'})));
    vi.stubGlobal('fetch',fetcher);const api=new ApiClient('/api');api.setToken('test-session');
    expect(await api.post('/content',{title:'Real saved title'})).toEqual({id:'saved'});
    const [url,options]=fetcher.mock.calls[0];expect(url).toBe('/api/content');
    expect(options.headers.get('Authorization')).toBe('Bearer test-session');
    expect(JSON.parse(options.body)).toEqual({title:'Real saved title'});
  });
  it('retains API conflicts and never returns mock content on failures',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Revision changed',code:'revision_conflict'}),{status:409})));
    await expect(new ApiClient().post('/content/a/revisions',{})).rejects.toMatchObject({status:409,code:'revision_conflict',message:'Revision changed'});
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new TypeError('offline')));
    await expect(new ApiClient().request('/content')).rejects.toBeInstanceOf(ApiError);
  });
  it('rejects responses from a previous login session',async()=>{
    let finish!:(value:Response)=>void;vi.stubGlobal('fetch',vi.fn(()=>new Promise<Response>(resolve=>{finish=resolve;})));
    const api=new ApiClient();api.setToken('first');const pending=api.request('/content');api.setToken('second');
    finish(new Response(JSON.stringify([{id:'previous-account'}])));
    await expect(pending).rejects.toMatchObject({code:'session_changed'});
  });
  it('reports unreadable responses and failed jobs explicitly',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html>error</html>')));
    await expect(new ApiClient().request('/content')).rejects.toMatchObject({code:'invalid_response'});
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({status:'failed',detail:'Provider unavailable'}))));
    expect(await new ApiClient().poll('/jobs/a')).toMatchObject({status:'failed'});
  });
});
describe('Persisted finding display',()=>{
  const finding={span_start:2,span_end:6,quoted_text:'₹799',verdict:'violation',severity:'critical',status:'open',source:{document_id:'doc',document_title:'Uploaded source',location:'page 2',excerpt:'Price ₹999'}} as Finding;
  it('uses Python Unicode offsets and refuses mismatched excerpts',()=>{
    expect(exactSegments('🎧 ₹799 today',finding)).toEqual({before:'🎧 ',quote:'₹799',after:' today'});
    expect(exactSegments('🎧 ₹999 today',finding)).toBeNull();
  });
  it('keeps accepted high-risk findings blocking until a fix is applied',()=>{
    expect(severity({...finding,status:'accepted'})).toBe('blocker');
    expect(severity({...finding,status:'rejected'})).toBe('warning');
    expect(severity({...finding,verdict:'supported'})).toBe('none');
    expect(sourceView(finding)[0].documentId).toBe('doc');
  });
  it('parses SQLite and PostgreSQL timestamps as the same UTC instant',()=>{
    expect(utc('2026-11-06T12:00:00')).toBe(utc('2026-11-06T12:00:00+00:00'));
  });
});
