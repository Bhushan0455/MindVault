from copy import deepcopy
from unittest.mock import patch
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Rule, Fact, Revision, Finding, Content, Approval, Document
from app.core.config import settings


def new_content(client,auth,brand,text='Veyra Beat 200 headphones for ₹799.',**kwargs):
    payload={'title':'Integration draft','brand_id':brand,'body_text':text,
             'context':{'product':'Veyra Beat 200','region':'IN','content_type':'organic_post','publication_date':'2026-11-06'}}
    payload.update(kwargs)
    response=client.post('/api/content',json=payload,headers=auth['creator'])
    assert response.status_code==200,response.text
    return response.json()


def review(client,auth,item):
    r=client.post('/api/content/'+item['id']+'/review',headers=auth['creator'])
    assert r.status_code==202,r.text
    result=client.get('/api/review-runs/'+r.json()['run_id'],headers=auth['creator'])
    assert result.status_code==200,result.text
    assert result.json()['status']=='done',result.text
    return result.json()


def upload(client,auth,brand,text='Avoid cheap; use affordable.\nVeyra Beat 200: price INR 999.'):
    r=client.post('/api/documents',headers=auth['admin'],data={'brand_id':brand,'kind':'rules'},
                  files={'file':('policy.txt',text.encode(),'text/plain')})
    assert r.status_code==200,r.text
    return r.json()


def test_full_fix_recheck_submit_approve_and_new_revision(client,auth,brand):
    item=new_content(client,auth,brand)
    run=review(client,auth,item)
    assert run['ai_status']=='not_requested' and not run['ai_used']
    f=next(f for f in run['findings'] if f['category']=='price')
    assert f['quoted_text']=='₹799' and f['suggested_fix']=='₹999'
    assert f['fact']['source_document']=='Fictional Veyra Product Facts'
    assert f['fact']['value']=='₹999' and f['fact']['page'] is None
    assert f['source']['location']=='line 1'
    assert client.post(f"/api/content/{item['id']}/submit",headers=auth['creator']).status_code==409
    assert client.post(f"/api/findings/{f['id']}/decision",json={'action':'accept'},headers=auth['creator']).status_code==200
    # Merely accepting a suggested fix must not make the unchanged draft submittable.
    assert client.post(f"/api/content/{item['id']}/submit",headers=auth['creator']).status_code==409
    fixed=client.post(f"/api/content/{item['id']}/apply-fixes",headers=auth['creator'])
    assert fixed.status_code==200,fixed.text
    current=fixed.json()['content']; revision=current['current_revision']
    assert revision['number']==2 and '₹999' in revision['body_text']
    original=client.get(f"/api/content/{item['id']}/revisions/1",headers=auth['creator']).json()
    assert '₹799' in original['body_text']
    assert client.get(f"/api/content/{item['id']}/diff?from=1&to=2",headers=auth['creator']).json()['diff']
    assert client.post(f"/api/content/{item['id']}/submit",headers=auth['creator']).status_code==200
    assert any(x['id']==item['id'] for x in client.get('/api/queue',headers=auth['reviewer']).json())
    assert client.post(f"/api/content/{item['id']}/approve",json={'revision_id':original['id']},headers=auth['reviewer']).status_code==409
    approved=client.post(f"/api/content/{item['id']}/approve",json={'revision_id':revision['id']},headers=auth['reviewer'])
    assert approved.status_code==200,approved.text
    assert approved.json()['approval']['body_hash']==revision['body_hash']
    assert client.post(f"/api/content/{item['id']}/review",headers=auth['creator']).status_code==409
    edited=client.post(f"/api/content/{item['id']}/revisions",json={'title':'Edited','body_text':'New draft'},headers=auth['creator']).json()
    assert edited['status']=='draft' and edited['latest_run_id'] is None
    with SessionLocal() as db: assert len(list(db.scalars(select(Approval))))==1


def test_terminology_disclaimer_claim_numeric_checks(client,auth,brand):
    item=new_content(client,auth,brand,'Veyra Beat 200 are the best cheap headphones at ₹799 with battery life 50 hours and warranty 2 years.',
        context={'product':'Veyra Beat 200','region':'IN','content_type':'paid_ad','publication_date':'2026-11-06'})
    run=review(client,auth,item)
    categories={f['category'] for f in run['findings']}
    assert {'price','battery_life','warranty','terminology','claims','disclaimer'}<=categories
    assert all(item['current_revision']['body_text'][f['span_start']:f['span_end']]==f['quoted_text'] for f in run['findings'])


def test_context_rules_and_pending_not_applied(client,auth,brand):
    pending=client.post('/api/rules',headers=auth['admin'],json={'brand_id':brand,'code':'NEW','instruction':'Avoid weird.',
        'category':'terminology','forbidden_terms':['weird']}).json()
    item=new_content(client,auth,brand,'weird',context={'channel':'investor_deck','region':'IN','content_type':'organic_post'})
    run=review(client,auth,item)
    assert 'TONE-INV-03' in [r['code'] for r in run['applied_rules']]
    assert 'TONE-IG-02' not in [r['code'] for r in run['applied_rules']]
    assert 'NEW' in [r['code'] for r in run['skipped_rules']]


def test_rejection_reason_and_risk_visible_to_reviewer(client,auth,brand):
    item=new_content(client,auth,brand); run=review(client,auth,item)
    f=next(f for f in run['findings'] if f['verdict']=='violation')
    url=f"/api/findings/{f['id']}/decision"
    for data in [{'action':'reject'},{'action':'reject','note':' '},{'action':'dismiss'},{'action':'edit'}]:
        assert client.post(url,json=data,headers=auth['creator']).status_code==422
    assert client.post(url,json={'action':'reject','note':'Reviewer must assess this campaign exception'},headers=auth['creator']).status_code==200
    assert client.post(f"/api/content/{item['id']}/submit",headers=auth['creator']).status_code==200
    queued=client.get('/api/queue',headers=auth['reviewer']).json()[0]
    assert queued['risk_decisions'][0]['decision_note']
    assert client.post(url,json={'action':'accept'},headers=auth['creator']).status_code==409
    r=client.post(f"/api/content/{item['id']}/request-changes",headers=auth['reviewer'],json={'revision_id':item['current_revision']['id'],'comment':'Please revise the draft.'})
    assert r.json()['content']['status']=='changes_requested'


def test_stale_finding_and_stale_editor(client,auth,brand):
    item=new_content(client,auth,brand); run=review(client,auth,item)
    old=item['current_revision']['id']
    payload={'title':'New','body_text':'Updated content','expected_revision_id':old}
    assert client.post(f"/api/content/{item['id']}/revisions",json=payload,headers=auth['creator']).status_code==200
    assert client.post(f"/api/content/{item['id']}/revisions",json=payload,headers=auth['creator']).status_code==409
    assert client.post(f"/api/findings/{run['findings'][0]['id']}/decision",json={'action':'accept'},headers=auth['creator']).status_code==409


def test_source_snapshots_do_not_change_with_database_edits(client,auth,brand):
    item=new_content(client,auth,brand); run=review(client,auth,item)
    original=run['findings'][0]
    with SessionLocal() as db:
        fact=db.get(Fact,original['fact_id']); fact.value_text='CHANGED'; fact.source_location='changed'; db.commit()
    again=client.get('/api/review-runs/'+run['id'],headers=auth['creator']).json()['findings'][0]
    assert again==original


def test_rule_versions_approval_supersession(client,auth,brand):
    rules=client.get('/api/rules',headers=auth['admin']).json()
    old=next(r for r in rules if r['code']=='TERM-01')
    changed=client.patch('/api/rules/'+old['id'],json={'instruction':'Avoid cheap and bargain.','forbidden_terms':['cheap','bargain']},headers=auth['admin'])
    assert changed.status_code==200,changed.text
    new=changed.json(); assert new['id']!=old['id'] and new['version']==2 and new['status']=='pending'
    assert next(r for r in client.get('/api/rules',headers=auth['admin']).json() if r['id']==old['id'])['status']=='approved'
    assert client.post('/api/rules/'+new['id']+'/approve',headers=auth['admin']).status_code==200
    assert next(r for r in client.get('/api/rules',headers=auth['admin']).json() if r['id']==old['id'])['status']=='superseded'
    assert client.post('/api/rules/'+new['id']+'/approve',headers=auth['admin']).status_code==409
    assert client.post('/api/rules/'+new['id']+'/reject',headers=auth['admin']).status_code==409


def test_fact_versions_and_pending_validation(client,auth,brand):
    old=client.get('/api/facts',headers=auth['admin']).json()[0]
    changed=client.patch('/api/facts/'+old['id'],json={'value_text':'₹1099','value_num':1099},headers=auth['admin'])
    assert changed.status_code==200,changed.text
    assert changed.json()['version']==2 and changed.json()['status']=='pending'
    assert client.post('/api/facts/'+changed.json()['id']+'/approve',headers=auth['admin']).status_code==200
    for bad in [{'value_num':-1},{'unit':'USD'},{'attribute':'unknown'},{'valid_from':'2027-01-01','valid_to':'2026-01-01'}]:
        assert client.patch('/api/facts/'+changed.json()['id'],json=bad,headers=auth['admin']).status_code==422


def test_real_document_extraction_candidates_approval_and_idempotence(client,auth,brand):
    doc=upload(client,auth,brand)
    r=client.post('/api/documents/'+doc['id']+'/extract',headers=auth['admin']); assert r.status_code==202,r.text
    job=client.get('/api/jobs/'+r.json()['job_id'],headers=auth['admin']).json()
    assert job['status']=='done' and job['result']['method']=='deterministic'
    candidates=client.get('/api/documents/'+doc['id']+'/candidates',headers=auth['admin']).json()
    assert len(candidates)==2 and all(c['status']=='pending' for c in candidates)
    candidate=next(c for c in candidates if c['kind']=='fact')
    data={'knowledge':{'brand_id':brand,'product':'Veyra Beat 200','attribute':'price',
                       'value_text':'₹999','value_num':999,'unit':'INR','market':'IN','valid_from':'2026-11-06'}}
    accepted=client.post('/api/candidates/'+candidate['id']+'/approve',json=data,headers=auth['admin'])
    assert accepted.status_code==200,accepted.text
    assert accepted.json()['knowledge']['source_document_id']==doc['id']
    assert accepted.json()['knowledge']['source_excerpt']=='Veyra Beat 200: price INR 999.'
    assert client.post('/api/candidates/'+candidate['id']+'/approve',json=data,headers=auth['admin']).status_code==409
    rule=next(c for c in candidates if c['kind']=='rule')
    assert client.post('/api/candidates/'+rule['id']+'/reject',headers=auth['admin']).status_code==200
    client.post('/api/documents/'+doc['id']+'/extract',headers=auth['admin'])
    assert len(client.get('/api/documents/'+doc['id']+'/candidates',headers=auth['admin']).json())==2


def test_clarity_proposal_is_pending_version_and_cannot_reapply(client,auth,brand):
    rule=client.post('/api/rules',headers=auth['admin'],json={'brand_id':brand,'code':'VAGUE','instruction':'Keep captions short.','category':'tone'}).json()
    client.post('/api/rules/'+rule['id']+'/approve',headers=auth['admin'])
    job=client.post('/api/brands/'+brand+'/clarity',headers=auth['admin'])
    assert job.status_code==200,job.text
    job=job.json(); p=next(p for p in job['result']['findings'] if p['rule_id']==rule['id'])
    payload={'proposal_id':p['id'],'instruction':'Keep captions under 20 words.'}
    new=client.post('/api/clarity/'+job['id']+'/accept',headers=auth['admin'],json=payload)
    assert new.status_code==200,new.text
    assert new.json()['status']=='pending' and new.json()['version']==2
    assert client.post('/api/clarity/'+job['id']+'/accept',headers=auth['admin'],json=payload).status_code==409


def test_comments_scoped_to_content_and_revision(client,auth,brand):
    a=new_content(client,auth,brand); b=new_content(client,auth,brand)
    url=f"/api/content/{a['id']}/comments"
    assert client.post(url,json={'body':'Good','revision_id':b['current_revision']['id']},headers=auth['creator']).status_code==404
    assert client.post(url,json={'body':'Check this'},headers=auth['reviewer']).status_code==200
    assert len(client.get(url,headers=auth['creator']).json())==1


def test_tenant_and_creator_access_isolation(client,auth,brand,other_users):
    item=new_content(client,auth,brand); run=review(client,auth,item); doc=upload(client,auth,brand)
    for headers in other_users:
        for url in [f"/api/content/{item['id']}",f"/api/content/{item['id']}/revisions/1",
                    f"/api/content/{item['id']}/diff?from=1&to=1",f"/api/content/{item['id']}/comments",'/api/review-runs/'+run['id']]:
            assert client.get(url,headers=headers).status_code==404,url
    foreign=other_users[0]
    assert client.get('/api/documents/'+doc['id'],headers=foreign).status_code==404
    assert client.post('/api/content',json={'title':'Bad','body_text':'X','brand_id':brand},headers=foreign).status_code==404
    assert client.get('/api/content',headers=foreign).json()==[]
    assert client.get('/api/audit',headers=foreign).json()==[]
    assert client.get('/api/insights',headers=foreign).json()['findings_by_category']=={}


def test_auth_role_validation_cors_and_errors(client,auth,brand):
    assert client.get('/api/me').status_code==401
    assert client.get('/api/me',headers={'Authorization':'Bearer invalid'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'admin@demo','password':'bad'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'admin@demo','password':'demo'}).status_code==200
    assert client.post('/api/brands',json={'name':'New'},headers=auth['creator']).status_code==403
    assert client.get('/api/queue',headers=auth['creator']).status_code==403
    assert client.post('/api/brands',json={},headers=auth['admin']).status_code==422
    assert client.post('/api/rules',json={'brand_id':brand},headers=auth['admin']).status_code==422
    response=client.get('/api/me',headers={'Origin':'http://localhost:5173'})
    assert response.headers['access-control-allow-origin']=='http://localhost:5173'
    assert client.get('/api/health').json()['db']
    assert client.get('/openapi.json').status_code==200
    assert client.get('/api/missing-route').json()['code']=='not_found'
    assert client.post('/api/me',headers=auth['creator']).json()['code']=='method_not_allowed'


def test_invalid_uploads_and_cross_brand_sources(client,auth,brand):
    for filename,content in [('bad.exe',b'hi'),('bad.pdf',b'not a PDF'),('bad.txt',b'\xff\xfe\x00')]:
        r=client.post('/api/documents',headers=auth['admin'],data={'brand_id':brand,'kind':'rules'},files={'file':(filename,content)})
        assert r.status_code==422,r.text
    doc=upload(client,auth,brand)
    brand2=client.post('/api/brands',headers=auth['admin'],json={'name':'Other'}).json()['id']
    r=client.post('/api/rules',headers=auth['admin'],json={'brand_id':brand2,'code':'SOURCE','instruction':'Hello',
        'source_document_id':doc['id'],'source_excerpt':'Avoid cheap; use affordable.','source_location':'line 1'})
    assert r.status_code==422


def test_ai_failure_retains_deterministic_findings(client,auth,brand):
    item=new_content(client,auth,brand)
    with patch.object(settings,'enable_semantic',True), patch('app.services.integration.GeminiContentGenerator') as gen:
        gen.return_value.org_id=None
        # A real scoped callable with a failing provider, without network use.
        class Failing:
            model='test-model'
            def __call__(self,payload): raise RuntimeError('provider unavailable')
        gen.side_effect=lambda **kw: Failing()
        run=review(client,auth,item)
    assert run['ai_status']=='unavailable' and not run['ai_used']
    assert any(f['category']=='price' for f in run['findings'])


def test_corrupt_fix_span_is_rejected_without_revision(client,auth,brand):
    item=new_content(client,auth,brand); run=review(client,auth,item); f=run['findings'][0]
    client.post('/api/findings/'+f['id']+'/decision',headers=auth['creator'],json={'action':'accept'})
    with SessionLocal() as db:
        row=db.get(Finding,f['id']); snapshot=dict(row.snapshot); snapshot['span_start']=999; row.snapshot=snapshot; db.commit()
    r=client.post(f"/api/content/{item['id']}/apply-fixes",headers=auth['creator'])
    assert r.status_code==409,r.text
    assert client.get('/api/content/'+item['id'],headers=auth['creator']).json()['current_revision']['number']==1


def test_explicit_tone_constraints_respect_approved_context(client,auth,brand):
    ig=new_content(client,auth,brand,'Hello 🎧🎧🎧',context={'channel':'instagram','audience':'consumer','content_type':'organic_post'})
    ig_findings=review(client,auth,ig)['findings']
    assert any(f['category']=='tone' and f['quoted_text']=='🎧' for f in ig_findings)
    investor=new_content(client,auth,brand,'Hello!',context={'channel':'investor_deck','content_type':'organic_post'})
    assert any(f['category']=='tone' and f['quoted_text']=='!' for f in review(client,auth,investor)['findings'])
    other=new_content(client,auth,brand,'Hello! 🎧🎧🎧',context={'channel':'email','content_type':'organic_post'})
    assert not any(f['category']=='tone' for f in review(client,auth,other)['findings'])
