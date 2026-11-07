from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.main import app
from app.db import engine, Base, SessionLocal
from app.models import Rule, Content, Revision, ReviewRun, Fact
from app.models import ServiceJob
from datetime import datetime,timezone,timedelta
from app.core.config import settings
from app.migration import migrate, ADDITIONS, require_current_schema
from test_workflows import new_content, review, upload


def test_claim_evidence_exact_sentence_not_blanket_exception(client,auth,brand):
    data={'brand_id':brand,'product':'Veyra Beat 200','attribute':'claim','value_text':'Veyra Beat 200 is the best.', 'market':'IN'}
    fact=client.post('/api/facts',headers=auth['admin'],json=data)
    assert fact.status_code==200,fact.text
    client.post('/api/facts/'+fact.json()['id']+'/approve',headers=auth['admin'])
    matched=review(client,auth,new_content(client,auth,brand,'Veyra Beat 200 is the best.'))
    assert any(f['category']=='claims' and f['verdict']=='supported' for f in matched['findings'])
    other=review(client,auth,new_content(client,auth,brand,'Veyra Beat 200 is the fastest.'))
    assert any(f['category']=='claims' and f['verdict']=='unsupported' for f in other['findings'])


def test_edit_fix_deletion_and_no_automatic_apply(client,auth,brand):
    item=new_content(client,auth,brand,'Veyra Beat 200 are cheap.')
    run=review(client,auth,item); f=next(f for f in run['findings'] if f['category']=='terminology')
    response=client.post('/api/findings/'+f['id']+'/decision',headers=auth['creator'],json={'action':'edit','edited_text':''})
    assert response.status_code==200
    before=client.get('/api/content/'+item['id'],headers=auth['creator']).json()
    assert 'cheap' in before['current_revision']['body_text']
    after=client.post('/api/content/'+item['id']+'/apply-fixes',headers=auth['creator'])
    assert after.status_code==200,after.text
    assert 'cheap' not in after.json()['content']['current_revision']['body_text']


def test_overlap_safe_atomic_apply(client,auth,brand):
    for code,term in [('OVER1','cheap headphones'),('OVER2','headphones')]:
        rule=client.post('/api/rules',headers=auth['admin'],json={'brand_id':brand,'code':code,'instruction':'Avoid '+term,
            'category':'terminology','forbidden_terms':[term],'preferred_terms':{term:'audio'}}).json()
        client.post('/api/rules/'+rule['id']+'/approve',headers=auth['admin'])
    item=new_content(client,auth,brand,'cheap headphones')
    run=review(client,auth,item)
    for f in run['findings']:
        if f['category']=='terminology':
            assert client.post('/api/findings/'+f['id']+'/decision',headers=auth['creator'],json={'action':'accept'}).status_code==200
    assert client.post('/api/content/'+item['id']+'/apply-fixes',headers=auth['creator']).status_code==409
    assert client.get('/api/content/'+item['id'],headers=auth['creator']).json()['current_revision']['number']==1


def test_no_fixes_and_supported_fix_rejected(client,auth,brand):
    item=new_content(client,auth,brand,'Veyra Beat 200 at ₹999.')
    run=review(client,auth,item); supported=next(f for f in run['findings'] if f['verdict']=='supported')
    assert client.post('/api/findings/'+supported['id']+'/decision',headers=auth['creator'],json={'action':'accept'}).status_code==422
    assert client.post('/api/content/'+item['id']+'/apply-fixes',headers=auth['creator']).status_code==409


def test_conflicting_facts_are_needs_review(client,auth,brand):
    f=client.post('/api/facts',headers=auth['admin'],json={'brand_id':brand,'product':'Veyra Beat 200',
        'attribute':'price','value_num':1000,'value_text':'₹1000','unit':'INR','market':'IN'}).json()
    client.post('/api/facts/'+f['id']+'/approve',headers=auth['admin'])
    run=review(client,auth,new_content(client,auth,brand))
    assert any(f['category']=='price' and f['verdict']=='needs_review' and f['suggested_fix'] is None for f in run['findings'])


def test_source_reference_resolves_actual_document(client,auth,brand):
    doc=upload(client,auth,brand,'Product Z: price INR 500.')
    data={'brand_id':brand,'product':'Product Z','attribute':'price','value_num':500,'value_text':'₹500','unit':'INR',
        'market':'IN','source_document_id':doc['id'],'source_location':'line 1','source_excerpt':'Product Z: price INR 500.'}
    fact=client.post('/api/facts',headers=auth['admin'],json=data)
    assert fact.status_code==200,fact.text
    client.post('/api/facts/'+fact.json()['id']+'/approve',headers=auth['admin'])
    item=new_content(client,auth,brand,'Product Z at ₹400.',context={'product':'Product Z','region':'IN'})
    f=next(f for f in review(client,auth,item)['findings'] if f['category']=='price')
    assert f['source']=={'document_id':doc['id'],'document_title':'policy.txt','location':'line 1','excerpt':'Product Z: price INR 500.'}


def test_invalid_candidate_metadata_and_tenant_job_access(client,auth,brand,other_users):
    doc=upload(client,auth,brand)
    extraction=client.post('/api/documents/'+doc['id']+'/extract',headers=auth['admin']).json()
    candidates=client.get('/api/documents/'+doc['id']+'/candidates',headers=auth['admin']).json()
    fact=next(c for c in candidates if c['kind']=='fact')
    data={'knowledge':{'brand_id':brand,'product':'Veyra Beat 200','attribute':'price','value_num':999,'value_text':'₹999','unit':'INR'}}
    assert client.post('/api/candidates/'+fact['id']+'/approve',json=data,headers=auth['admin']).status_code==422
    assert client.get('/api/jobs/'+extraction['job_id'],headers=other_users[0]).status_code==404
    assert client.get('/api/documents/'+doc['id']+'/candidates',headers=auth['creator']).status_code==403


def test_upload_size_limit(client,auth,brand):
    r=client.post('/api/documents',headers=auth['admin'],data={'brand_id':brand,'kind':'rules'},
        files={'file':('large.txt',b'x'*(settings.max_upload_mb*1024*1024+1),'text/plain')})
    assert r.status_code==413


def test_docx_and_pdf_upload_preserve_honest_locations(client,auth,brand):
    from docx import Document as Word
    from pypdf import PdfWriter
    word=Word(); word.add_paragraph('Avoid cheap; use affordable.'); docx=BytesIO(); word.save(docx)
    r=client.post('/api/documents',headers=auth['admin'],data={'brand_id':brand,'kind':'rules'},files={'file':('policy.docx',docx.getvalue())})
    assert r.status_code==200,r.text
    client.post('/api/documents/'+r.json()['id']+'/extract',headers=auth['admin'])
    candidate=client.get('/api/documents/'+r.json()['id']+'/candidates',headers=auth['admin']).json()[0]
    assert 'paragraph' in candidate['data']['source']['location'] and 'page' not in candidate['data']['source']['location']
    writer=PdfWriter(); writer.add_blank_page(width=72,height=72); pdf=BytesIO(); writer.write(pdf)
    r=client.post('/api/documents',headers=auth['admin'],data={'brand_id':brand,'kind':'facts'},files={'file':('blank.pdf',pdf.getvalue())})
    assert r.status_code==422 and r.json()['code']=='no_text'
    from examples.extraction_demo import sample_pdf
    r=client.post('/api/documents',headers=auth['admin'],data={'brand_id':brand,'kind':'facts'},files={'file':('facts.pdf',sample_pdf())})
    assert r.status_code==200,r.text
    with SessionLocal() as db:
        assert '[[PAGE 2]]' in db.get(__import__('app.models',fromlist=['Document']).Document,r.json()['id']).text


def test_stale_clarity_after_rule_superseded(client,auth,brand):
    rule=client.post('/api/rules',headers=auth['admin'],json={'brand_id':brand,'code':'SHORT','instruction':'Keep captions short.','category':'tone'}).json()
    client.post('/api/rules/'+rule['id']+'/approve',headers=auth['admin'])
    job=client.post('/api/brands/'+brand+'/clarity',headers=auth['admin']).json()
    proposal=next(p for p in job['result']['findings'] if p['rule_id']==rule['id'])
    new=client.patch('/api/rules/'+rule['id'],headers=auth['admin'],json={'instruction':'Keep captions under 15 words.'}).json()
    client.post('/api/rules/'+new['id']+'/approve',headers=auth['admin'])
    assert client.post('/api/clarity/'+job['id']+'/accept',headers=auth['admin'],json={'proposal_id':proposal['id'],'instruction':'20 words'}).status_code==409


def test_demo_disabled_and_unhandled_error_cors(client,auth):
    with patch.object(settings,'demo_mode',False):
        assert client.post('/api/auth/demo?role=creator').status_code==404
    from app.db import get_db
    def broken(): raise RuntimeError('sensitive value should not leak')
    app.dependency_overrides[get_db]=broken
    try:
        with TestClient(app,raise_server_exceptions=False) as c:
            r=c.get('/api/health',headers={'Origin':'http://localhost:5173'})
            assert r.status_code==500 and r.json()['code']=='internal_error'
            assert 'sensitive' not in r.text
            assert r.headers['access-control-allow-origin']=='http://localhost:5173'
    finally: app.dependency_overrides.clear()


@pytest.mark.skipif(engine.dialect.name!='postgresql',reason='PostgreSQL locking test')
def test_parallel_revision_edits_one_winner(client,auth,brand):
    item=new_content(client,auth,brand)
    payload={'title':'Concurrent','body_text':'Updated','expected_revision_id':item['current_revision']['id']}
    def edit(): return client.post('/api/content/'+item['id']+'/revisions',json=payload,headers=auth['creator']).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: codes=list(pool.map(lambda _:edit(),range(2)))
    assert sorted(codes)==[200,409]


@pytest.mark.skipif(engine.dialect.name!='postgresql',reason='PostgreSQL locking test')
def test_parallel_approval_one_winner(client,auth,brand):
    item=new_content(client,auth,brand,'A friendly greeting.')
    review(client,auth,item)
    client.post('/api/content/'+item['id']+'/submit',headers=auth['creator'])
    def approve(): return client.post('/api/content/'+item['id']+'/approve',headers=auth['reviewer'],json={'revision_id':item['current_revision']['id'],'comment':'Please revise the draft.'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: codes=list(pool.map(lambda _:approve(),range(2)))
    assert sorted(codes)==[200,409]


def test_migration_adds_columns_preserves_rows_and_is_idempotent():
    # Reconstruct the supplied pre-integration schema from checked-in SQL,
    # then run the same migration used for an existing Role A installation.
    from pathlib import Path
    Base.metadata.drop_all(engine)
    ddl=(Path(__file__).parent/'fixtures/role_a_schema.sql').read_text()
    if engine.dialect.name=='sqlite': ddl=ddl.replace('BYTEA','BLOB')
    with engine.begin() as connection:
        for statement in ddl.split(';'):
            if statement.strip(): connection.exec_driver_sql(statement)
        connection.execute(text("INSERT INTO organisations(id,name) VALUES ('preserved','Existing organisation')"))
        connection.execute(text("INSERT INTO review_runs(id,revision_id,status,progress_step,applied_rules,skipped,ai_used,created_at) VALUES ('legacy-run','legacy-revision','done','done','[]','[]',FALSE,CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO approvals(id,content_id,revision_id,body_hash,reviewer_id,decision,created_at) VALUES ('legacy-approval','legacy-content','legacy-revision','original-hash','legacy-reviewer','approved',CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO facts(id,org_id,brand_id,product,attribute,value_text,value_num,unit,market,status,version) VALUES ('legacy-fact','preserved','legacy-brand','Product','price','INR 1.01',1.01,'INR','IN','approved',1)"))
        migrate(connection)
    require_current_schema(engine)
    with engine.begin() as connection:
        migrate(connection)
        assert connection.execute(text("SELECT name FROM organisations WHERE id='preserved'")).scalar()=='Existing organisation'
        assert connection.execute(text("SELECT status FROM review_runs WHERE id='legacy-run'")).scalar()=='legacy'
        assert connection.execute(text("SELECT body_hash FROM approvals WHERE id='legacy-approval'")).scalar()=='original-hash'
        assert connection.execute(text("SELECT qualifier FROM facts WHERE id='legacy-fact'")).scalar()=='exact'


def test_knowledge_changes_require_new_review_before_submit(client,auth,brand):
    item=new_content(client,auth,brand,'A friendly greeting.')
    review(client,auth,item)
    client.post('/api/rules',headers=auth['admin'],json={'brand_id':brand,'code':'NEW-KNOWLEDGE','instruction':'Use clear language.'})
    response=client.post('/api/content/'+item['id']+'/submit',headers=auth['creator'])
    assert response.status_code==409 and response.json()['code']=='knowledge_changed'
    review(client,auth,item)
    assert client.post('/api/content/'+item['id']+'/submit',headers=auth['creator']).status_code==200


def test_knowledge_changes_block_old_approval_but_allow_request_changes(client,auth,brand):
    item=new_content(client,auth,brand,'A friendly greeting.'); review(client,auth,item)
    client.post('/api/content/'+item['id']+'/submit',headers=auth['creator'])
    client.post('/api/rules',headers=auth['admin'],json={'brand_id':brand,'code':'UPDATE','instruction':'Be precise.'})
    payload={'revision_id':item['current_revision']['id'],'comment':'Please recheck the updated knowledge.'}
    response=client.post('/api/content/'+item['id']+'/approve',json=payload,headers=auth['reviewer'])
    assert response.status_code==409 and response.json()['code']=='knowledge_changed'
    assert client.post('/api/content/'+item['id']+'/request-changes',json=payload,headers=auth['reviewer']).status_code==200


def test_interrupted_review_and_extraction_reach_terminal_status(client,auth,brand):
    item=new_content(client,auth,brand)
    with SessionLocal() as db:
        creator_content=db.get(Content,item['id'])
        old=datetime.now(timezone.utc)-timedelta(minutes=10)
        run=ReviewRun(revision_id=item['current_revision']['id'],status='running',created_at=old)
        job=ServiceJob(org_id=creator_content.org_id,brand_id=brand,kind='extraction',status='queued',created_at=old)
        db.add_all([run,job]); db.flush(); creator_content.latest_run_id=run.id; db.commit(); run_id,job_id=run.id,job.id
    assert client.get('/api/review-runs/'+run_id,headers=auth['creator']).json()['status']=='failed'
    timed=client.get('/api/jobs/'+job_id,headers=auth['admin']).json()
    assert timed['status']=='failed' and timed['result']['code']=='job_timeout'
    from app.main import run_review
    from app.routers.knowledge import extraction_job
    run_review(run_id)
    extraction_job(job_id,'unused-document-id')
    assert client.get('/api/review-runs/'+run_id,headers=auth['creator']).json()['status']=='failed'
    assert client.get('/api/jobs/'+job_id,headers=auth['admin']).json()['result']['code']=='job_timeout'


def test_late_worker_cannot_change_new_revision_state(client,auth,brand):
    from app.services.integration import review_revision as original
    item=new_content(client,auth,brand)
    def edit_during_review(revision,content,db):
        response=client.post('/api/content/'+item['id']+'/revisions',headers=auth['creator'],
            json={'title':'Edited during review','body_text':'The next draft'})
        assert response.status_code==200,response.text
        return original(revision,content,db)
    with patch('app.main.review_revision',side_effect=edit_during_review): review(client,auth,item)
    current=client.get('/api/content/'+item['id'],headers=auth['creator']).json()
    assert current['status']=='draft' and current['latest_run_id'] is None and current['current_revision']['number']==2


def test_source_lookup_scoped_and_location_checked(client,auth,brand,other_users):
    doc=upload(client,auth,brand)
    response=client.get('/api/sources/'+doc['id'],params={'location':'line 1'},headers=auth['creator'])
    assert response.status_code==200,response.text
    assert response.json()['blocks'][0]['text']=='Avoid cheap; use affordable.'
    assert client.get('/api/sources/'+doc['id'],params={'location':'page 99'},headers=auth['creator']).status_code==404
    assert client.get('/api/sources/'+doc['id'],params={'location':'line 1'},headers=other_users[0]).status_code==404


def test_revision_without_context_preserves_previous_context_and_changes_title(client,auth,brand):
    item=new_content(client,auth,brand,context={'product':'Product Z','channel':'email','audience':'retailer','region':'GB','content_type':'email','campaign':'Launch'})
    response=client.post('/api/content/'+item['id']+'/revisions',headers=auth['creator'],json={'title':'Renamed','body_text':'Rewritten'})
    assert response.status_code==200,response.text
    assert response.json()['context']==item['context'] and response.json()['title']=='Renamed'


def test_large_json_and_chunked_body_rejected_before_parsing(client,auth):
    r=client.post('/api/brands',headers={**auth['admin'],'Origin':'http://localhost:5173'},content=b'x'*300000)
    assert r.status_code==413 and r.headers['access-control-allow-origin']=='http://localhost:5173'
    r=client.post('/api/brands',headers=auth['admin'],content=iter([b'x'*160000,b'x'*160000]))
    assert r.status_code==413


def test_demo_password_login_disabled_with_demo_mode(client):
    with patch.object(settings,'demo_mode',False):
        assert client.post('/api/auth/login',json={'email':'admin@demo','password':'demo'}).status_code==401


def test_editing_pending_version_supersedes_approved_ancestor(client,auth):
    old=next(r for r in client.get('/api/rules',headers=auth['admin']).json() if r['code']=='TERM-01')
    v2=client.patch('/api/rules/'+old['id'],headers=auth['admin'],json={'instruction':'Second draft'}).json()
    v3=client.patch('/api/rules/'+v2['id'],headers=auth['admin'],json={'instruction':'Third draft'}).json()
    response=client.post('/api/rules/'+v3['id']+'/approve',headers=auth['admin'])
    assert response.status_code==200,response.text
    family=[r for r in client.get('/api/rules',headers=auth['admin']).json() if r['code']=='TERM-01']
    assert [r['id'] for r in family if r['status']=='approved']==[v3['id']]


@pytest.mark.skipif(engine.dialect.name!='postgresql',reason='PostgreSQL locking test')
def test_competing_rule_versions_cannot_both_be_approved(client,auth):
    old=next(r for r in client.get('/api/rules',headers=auth['admin']).json() if r['code']=='TERM-01')
    versions=[client.patch('/api/rules/'+old['id'],headers=auth['admin'],json={'instruction':f'Branch {n}'}).json() for n in range(2)]
    def approve(row): return client.post('/api/rules/'+row['id']+'/approve',headers=auth['admin']).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: codes=list(pool.map(approve,versions))
    assert sorted(codes)==[200,409]


def test_product_aliases_preserve_multi_product_price_attribution(client,auth,brand):
    product=client.post('/api/products',headers=auth['admin'],json={'brand_id':brand,'name':'Veyra Air 100','aliases':['Air 100']})
    assert product.status_code==200,product.text
    fact=client.post('/api/facts',headers=auth['admin'],json={'brand_id':brand,'product':'Air 100',
        'attribute':'price','value_num':1499,'value_text':'₹1499','unit':'INR','market':'IN'})
    assert fact.status_code==200 and fact.json()['product']=='Veyra Air 100'
    client.post('/api/facts/'+fact.json()['id']+'/approve',headers=auth['admin'])
    item=new_content(client,auth,brand,'Beat 200 at ₹799 and Air 100 at ₹1499.')
    findings=[f for f in review(client,auth,item)['findings'] if f['category']=='price']
    assert [(f['quoted_text'],f['verdict']) for f in findings]==[('₹799','violation'),('₹1499','supported')]
    assert findings[1]['fact_id']==fact.json()['id']


def test_alias_collisions_and_permissions(client,auth,brand,other_users):
    existing=client.get('/api/products',headers=auth['creator']).json()[0]
    assert existing['name']=='Veyra Beat 200'
    payload={'brand_id':brand,'name':'Other product','aliases':['Beat 200']}
    assert client.post('/api/products',json=payload,headers=auth['admin']).status_code==409
    assert client.post('/api/products',json=payload,headers=auth['creator']).status_code==403
    assert client.post('/api/products',json=payload,headers=other_users[0]).status_code==404
    assert client.patch('/api/products/'+existing['id'],json={'aliases':['Beat 200','Beat 200']},headers=auth['admin']).status_code==422
    assert client.patch('/api/products/'+existing['id'],json={'aliases':['Short name']},headers=auth['admin']).status_code==200
    assert client.get('/api/products',headers=other_users[0]).json()==[]


def test_alias_updates_require_fresh_review(client,auth,brand):
    item=new_content(client,auth,brand,'A friendly greeting.'); review(client,auth,item)
    existing=client.get('/api/products',headers=auth['admin']).json()[0]
    client.patch('/api/products/'+existing['id'],json={'aliases':['Beat 200','Beat200']},headers=auth['admin'])
    response=client.post('/api/content/'+item['id']+'/submit',headers=auth['creator'])
    assert response.status_code==409 and response.json()['code']=='knowledge_changed'
