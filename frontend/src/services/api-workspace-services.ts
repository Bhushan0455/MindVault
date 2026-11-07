import { api,id,initials,subscribe,invalidate,utc,type Finding,type History,type Submission } from '../api/client';
import type { ContentDraft,RuleSource } from '../types/content-check';
import type { QueueSeverity,QueueSubmission,ReviewerQueueService } from '../types/reviewer-queue';
import type { ReviewerDetailService,ReviewFinding,SubmissionReview,SubmittedRevision } from '../types/reviewer-detail';
import type { RevisionJourneyService } from '../types/revision-journey';

export function sourceView(finding:Finding):RuleSource[]{return finding.source?[{title:finding.source.document_title,quote:finding.source.excerpt,location:finding.source.location,documentId:finding.source.document_id}]:[];}
export function severity(finding:Finding):QueueSeverity{return finding.verdict==='supported'?'none':['critical','high'].includes(finding.severity)&&!['rejected','dismissed'].includes(finding.status)?'blocker':finding.severity==='low'?'advisory':'warning';}
function contentDraft(contentId:string,title:string,body:string,context:History['content']['context']):ContentDraft{
  return {id:contentId,title,introduction:body,promotion:'',channel:context.channel,audience:context.audience,region:context.region,language:context.language||'Not specified'};
}
function reviewFinding(f:Finding):ReviewFinding{return {id:f.id,ruleId:f.rule?.code??f.fact?.id??f.category,title:`${f.category.replaceAll('_',' ')} · ${f.verdict.replaceAll('_',' ')}`,
  claim:f.quoted_text,severity:severity(f),status:f.verdict==='supported'?'matched':f.severity==='low'?'advisory':'attention',
  explanation:f.explanation+(f.decision_note?` Creator decision: ${f.status} — ${f.decision_note}`:''),sources:sourceView(f),simulated:false,
  blocking:severity(f)==='blocker',origin:f.origin,verdict:f.verdict,decisionStatus:f.status};}
function snapshot(data:History,brands:Map<string,string>):SubmissionReview{
  const revisions:SubmittedRevision[]=data.revisions.map(r=>{
    const approval=r.approvals.at(-1);const run=r.review_runs.filter(run=>run.status==='done').at(-1);
    const current=r.id===data.content.current_revision.id;
    const status:SubmittedRevision['status']=approval?(approval.decision==='approved'?'approved':'changes-requested'):
      current?(data.content.status==='in_review'?'pending':data.content.status==='checked'?'checked':'draft'):'superseded';
    return {id:r.id,bodyHash:r.body_hash,submissionId:data.content.id,number:r.number,submitted:!!r.submitted_at,submittedAt:utc(r.submitted_at??r.created_at)!,status,
      snapshot:{title:r.title??`Revision ${r.number}`,campaign:r.context.campaign??data.content.title,brand:brands.get(data.content.brand_id)??'Unavailable brand',
        contentCheckPath:`/content-checks?content=${id(data.content.id)}`,creator:{name:r.created_by.name,team:r.created_by.role??'Creator',initials:initials(r.created_by.name)},
        content:contentDraft(data.content.id,r.title??`Revision ${r.number}`,r.body_text,r.context),assets:[]},
      findings:(run?.findings??[]).map(reviewFinding),
      decision:approval?{id:approval.id,submissionId:data.content.id,revisionId:r.id,kind:approval.decision==='approved'?'approved':'changes-requested',
        comment:approval.comment??'',reviewer:approval.reviewer.name,decidedAt:utc(approval.created_at)!}:undefined};
  });
  const kinds=new Set(['draft-created','ai-check','finding-detected','revision-created','rechecked','submitted','approved','changes-requested']);
  return {submissionId:data.content.id,currentRevisionId:data.content.current_revision.id,revisions,persisted:true,
    events:data.events.filter(e=>kinds.has(e.kind)).map(e=>({id:e.id,submissionId:data.content.id,revisionId:e.revision_id,revisionNumber:e.revision_number,
      kind:e.kind as SubmissionReview['events'][number]['kind'],actor:e.actor,at:utc(e.at)!,comment:e.comment,findingId:e.finding_id??undefined}))};
}
let queueCache:readonly QueueSubmission[]=[];let queueGeneration=0;
if(typeof window!=='undefined')window.addEventListener('mindvault:session-changed',()=>{queueCache=[];queueGeneration++;invalidate();});
function queueRecord(s:Submission):QueueSubmission{
  const severityOrder:QueueSeverity[]=['blocker','warning','advisory','none'];
  const level=severityOrder.find(level=>s.findings.some(f=>severity(f)===level))??'none';
  return {id:s.id,sourceDraftId:s.id,revisionId:s.revision_id,title:s.title,campaign:s.context.campaign??s.title,
    assetDescription:`Revision ${s.revision_number} · ${s.ai_status}`,brand:s.brand,
    submittedBy:{name:s.creator.name,team:s.creator.role??'Creator',initials:initials(s.creator.name)},channel:s.context.channel,region:s.context.region,
    submittedAt:utc(s.submitted_at)!,approvedAt:s.status==='approved'?utc(s.decision_at):undefined,
    status:s.status==='approved'?'approved':s.status==='changes_requested'?'changes-requested':'pending',severity:level,
    statusLabel:s.status==='approved'?'Approved':s.status==='changes_requested'?'Changes requested':'Pending review',
    summary:`${s.findings.filter(f=>f.verdict!=='supported').length} review findings · ${s.ai_status}`,draft:contentDraft(s.id,s.title,s.body_text,s.context),origin:'api',simulated:false};
}
export const apiQueueService:ReviewerQueueService={mode:'api',subscribe,getSnapshot:()=>queueCache,getHistory:()=>({reviewedBeforeVisibleQueue:0,approvedYesterday:0}),
  async load(){const generation=++queueGeneration;const data=await api.request<Submission[]>('/submissions');
    const next=data.map(queueRecord);if(generation===queueGeneration){const changed=JSON.stringify(next)!==JSON.stringify(queueCache);queueCache=next;if(changed)invalidate();}return next;}};
async function loadHistory(contentId:string){
  const [data,brands]=await Promise.all([api.request<History>(`/content/${id(contentId)}/history`),api.request<{id:string;name:string}[]>('/brands')]);
  return snapshot(data,new Map(brands.map(b=>[b.id,b.name])));
}
export const apiReviewService:ReviewerDetailService={mode:'api',subscribe,load:loadHistory,
  async decide(request){await api.post(`/content/${id(request.submissionId)}/${request.kind==='approved'?'approve':'request-changes'}`,
    {revision_id:request.revisionId,comment:request.comment});invalidate();return loadHistory(request.submissionId);}};
export const apiJourneyService:RevisionJourneyService={mode:'api',subscribe,load:loadHistory};
