import { useState } from 'react';
import { api,id,type Candidate,type Document,type Knowledge } from '../../api/client';
import { useAction,useResource,Feedback } from './shared';

function candidateValues(candidate?:Candidate):Partial<Knowledge>{
  if(!candidate)return {};const p=candidate.data.payload;return {instruction:p.instruction,category:p.category,product:p.product,attribute:p.attribute,value_text:p.value?`${p.qualifier==='up_to'?'up to ':''}${p.value} ${p.unit}`:'',value_num:p.value,unit:p.unit,market:p.market,qualifier:p.qualifier,
    code:'EXTRACT-'+candidate.id.slice(0,6).toUpperCase(),forbidden_terms:p.forbidden_term?[p.forbidden_term]:[],preferred_terms:p.preferred_term?{[p.forbidden_term]:p.preferred_term}:{},required_text:p.required_text||null,
    scope_channel:p.channel?[p.channel]:[],scope_audience:p.audience?[p.audience]:[],scope_region:p.region?[p.region]:[],scope_content_type:p.content_type?[p.content_type]:[],scope_campaign:p.campaign?[p.campaign]:[],
    source_document_id:candidate.document_id,source_location:candidate.data.source.location,source_excerpt:candidate.data.source.excerpt};
}
export function KnowledgeForm({kind,brandId,initial,candidate,onSaved}:{kind:'rule'|'fact';brandId:string;initial?:Knowledge;candidate?:Candidate;onSaved:()=>void}){
  const values={...candidateValues(candidate),...initial};const action=useAction();const docs=useResource<Document[]>('/documents');
  const [attribute,setAttribute]=useState(values.attribute??'price');const [category,setCategory]=useState(values.category??'terminology');
  const [sourceId,setSourceId]=useState(values.source_document_id??'');
  const csv=(input:FormData,key:string)=>String(input.get(key)||'').split(',').map(s=>s.trim()).filter(Boolean);
  async function submit(event:React.FormEvent<HTMLFormElement>){event.preventDefault();const form=new FormData(event.currentTarget);
    const text=(key:string)=>String(form.get(key)??'').trim();const date=(key:string)=>text(key)||null;
    await action.run(async()=>{
      const source={source_document_id:sourceId||null,source_location:text('source_location')||null,source_excerpt:text('source_excerpt')||null};
      let knowledge:Record<string,unknown>;
      if(kind==='rule'){
        const preferred:Record<string,string>={};for(const line of text('preferred_terms').split('\n').filter(Boolean)){
          const pair=line.split(/\s*(?:→|=>)\s*/);if(pair.length!==2||!pair[0]||!pair[1])throw new Error('Preferred phrases use one “forbidden → preferred” pair per line.');preferred[pair[0]]=pair[1];}
        knowledge={brand_id:brandId,code:initial?.code??text('code'),instruction:text('instruction'),category,severity:text('severity'),authority:text('authority'),priority:Number(text('priority')||0),
          forbidden_terms:csv(form,'forbidden_terms'),preferred_terms:preferred,required_text:text('required_text')||null,requires_claim_evidence:form.get('requires_claim_evidence')==='on',
          ...Object.fromEntries(['channel','audience','region','content_type','campaign'].map(key=>['scope_'+key,csv(form,'scope_'+key)])),
          effective_from:date('effective_from'),effective_to:date('effective_to'),...source};
      }else knowledge={brand_id:brandId,product:values.product&&initial?values.product:text('product'),attribute,market:values.market&&initial?values.market:text('market'),
        value_text:text('value_text'),value_num:attribute==='claim'?null:text('value_num'),unit:attribute==='claim'?null:text('unit'),qualifier:attribute==='claim'||attribute==='price'?'exact':text('qualifier'),
        valid_from:date('valid_from'),valid_to:date('valid_to'),...source};
      if(candidate)await api.post(`/candidates/${id(candidate.id)}/approve`,{knowledge});
      else if(initial)await api.patch(`/${kind==='rule'?'rules':'facts'}/${id(initial.id)}`,knowledge);
      else await api.post(`/${kind==='rule'?'rules':'facts'}`,knowledge);
      onSaved();
    },candidate?'Confirmed knowledge approved.':'A pending knowledge version was saved. Review and approve it before use.');
  }
  const field=(label:string,name:string,defaultValue:unknown,props:React.InputHTMLAttributes<HTMLInputElement>={})=><label className="field">{label}<input name={name} defaultValue={String(defaultValue??'')} {...props}/></label>;
  return <form className="knowledge-form" onSubmit={event=>void submit(event)}><fieldset disabled={action.busy}><p className="notice">{candidate?'Confirm the extracted meaning, scope, market and dates before approving.':'New and edited knowledge stays pending until an administrator approves it.'}</p>
    {kind==='rule'?<>{field('Rule code','code',values.code,{required:true,maxLength:40,readOnly:!!initial})}<label className="field">Instruction<textarea name="instruction" defaultValue={values.instruction??''} required maxLength={12000} rows={4}/></label>
      <div className="form-grid"><label className="field">Category<select name="category" value={category} onChange={e=>setCategory(e.target.value)}>{['terminology','disclaimer','claims','tone','general'].map(value=><option key={value}>{value}</option>)}</select></label><label className="field">Severity<select name="severity" defaultValue={values.severity??'medium'}>{['critical','high','medium','low'].map(value=><option key={value}>{value}</option>)}</select></label><label className="field">Authority<select name="authority" defaultValue={values.authority??'core'}>{['non_overridable','core','scoped','exception'].map(value=><option key={value}>{value}</option>)}</select></label>{field('Priority','priority',values.priority??0,{type:'number',min:-2147483648,max:2147483647})}</div>
      {field('Forbidden phrases (comma separated)','forbidden_terms',values.forbidden_terms?.join(', '),{required:category==='terminology'})}<label className="field">Preferred phrases<textarea name="preferred_terms" rows={2} defaultValue={Object.entries(values.preferred_terms??{}).map(([key,value])=>`${key} → ${value}`).join('\n')} placeholder="cheap → affordable"/></label>{field('Required disclaimer text','required_text',values.required_text,{required:category==='disclaimer'})}<label className="checkbox-field"><input name="requires_claim_evidence" type="checkbox" defaultChecked={values.requires_claim_evidence??false}/>Require exact approved evidence for claim wording</label>
      <details><summary>Scope and effective dates</summary><p className="muted">Empty scopes apply generally. Separate allowed values with commas.</p><div className="form-grid">{(['channel','audience','region','content_type','campaign'] as const).map(key=>field(key.replaceAll('_',' '),'scope_'+key,values[('scope_'+key) as keyof Knowledge] instanceof Array?(values[('scope_'+key) as keyof Knowledge] as string[]).join(', '):''))}{field('Effective from','effective_from',values.effective_from,{type:'date'})}{field('Effective through','effective_to',values.effective_to,{type:'date'})}</div></details>
    </>:<><div className="form-grid">{field('Product','product',values.product,{required:true,maxLength:120,readOnly:!!initial})}<label className="field">Attribute<select name="attribute" value={attribute} disabled={!!initial} onChange={e=>setAttribute(e.target.value)}>{['price','battery_life','warranty','claim'].map(value=><option key={value}>{value}</option>)}</select></label>{field('Market (e.g. IN)','market',values.market,{required:true,maxLength:20,readOnly:!!initial})}</div>
      {field(attribute==='claim'?'Exact approved claim sentence':'Display value','value_text',values.value_text,{required:true,maxLength:255})}{attribute!=='claim'&&<div className="form-grid">{field('Numeric value','value_num',values.value_num,{required:true,type:'number',min:0,step:'0.01'})}<label className="field">Unit<select key={attribute} name="unit" defaultValue={values.unit??(attribute==='price'?'INR':attribute==='battery_life'?'hours':'years')}>{(attribute==='price'?['INR']:attribute==='battery_life'?['hours']:['years','months']).map(value=><option key={value}>{value}</option>)}</select></label><label className="field">Qualifier<select name="qualifier" defaultValue={values.qualifier??'exact'}><option value="exact">Exact</option>{attribute!=='price'&&<option value="up_to">Up to</option>}</select></label></div>}
      <div className="form-grid">{field('Valid from','valid_from',values.valid_from,{type:'date'})}{field('Valid through','valid_to',values.valid_to,{type:'date'})}</div></>}
    <details open={!!candidate}><summary>Source evidence</summary><label className="field">Source document<select value={sourceId} disabled={!!candidate} onChange={e=>setSourceId(e.target.value)}><option value="">Manually entered knowledge</option>{docs.data?.filter(doc=>doc.brand_id===brandId).map(doc=><option key={doc.id} value={doc.id}>{doc.title}</option>)}</select></label>{field('Exact source location','source_location',values.source_location,{placeholder:'page 2 / line 3 / paragraph 1'})}<label className="field">Exact source excerpt<textarea name="source_excerpt" defaultValue={values.source_excerpt??''} rows={4}/></label></details>
    <Feedback error={action.error} notice={action.notice}/><button className="button button-primary" disabled={action.busy}>{action.busy?'Saving…':candidate?'Confirm & approve knowledge':initial?'Save new pending version':'Save pending knowledge'}</button>
  </fieldset></form>;
}
