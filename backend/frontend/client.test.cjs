// Run against compiled mindvault-client.js. Fetch is faked only at this boundary.
const assert = require('node:assert/strict');
const {findingSegments, MindVaultClient, ApiError} = require(process.argv[2]);
async function main() {
  assert.deepEqual(findingSegments('🎧 ₹799', {span_start:2,span_end:6,quoted_text:'₹799'}),
    {before:'🎧 ',quote:'₹799',after:'',insertion:false});
  assert.equal(findingSegments('Hi', {span_start:2,span_end:2,quoted_text:''}).insertion,true);
  assert.throws(() => findingSegments('Hi', {span_start:0,span_end:2,quoted_text:'No'}));
  const calls=[];
  global.fetch=async (url,init) => {
    calls.push({url,init});
    if (url.includes('/auth/demo')) return Response.json({token:'fake-test-token',user:{role:'creator'}});
    if (url.endsWith('/content/content-id/review')) return Response.json({run_id:'run-id'},{status:202});
    if (url.endsWith('/review-runs/run-id')) return Response.json({id:'run-id',status:'done',ai_used:false,ai_status:'not_requested',issues:[],findings:[]});
    return Response.json({code:'conflict',detail:'Refresh first'},{status:409});
  };
  const api=new MindVaultClient('http://localhost:8000/api');
  assert.equal((await api.demoLogin('creator')).role,'creator');
  assert.equal((await api.startReview('content-id')).run_id,'run-id');
  assert.equal(calls[1].init.headers.get('Authorization'),'Bearer fake-test-token');
  assert.equal((await api.waitForReview('run-id')).status,'done');
  await assert.rejects(() => api.request('/failure'), error => error instanceof ApiError && error.status===409 && error.code==='conflict');
  console.log('Frontend helper strict compilation and runtime checks passed.');
}
main().catch(error => { console.error(error); process.exitCode=1; });
