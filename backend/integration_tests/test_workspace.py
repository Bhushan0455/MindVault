from unittest.mock import patch
from sqlalchemy import select
from app.db import Base,engine,SessionLocal
from app.models import User,Organisation,Brand
from app.core.config import settings
from test_workflows import new_content,review,upload


def test_history_records_exact_snapshots_and_preserves_approved_revision_after_edit(client,auth,brand):
    item=new_content(client,auth,brand,title='First title')
    initial=item['current_revision']
    report=review(client,auth,item)
    price=next(f for f in report['findings'] if f['category']=='price')
    client.post('/api/findings/'+price['id']+'/decision',headers=auth['creator'],json={'action':'accept'})
    result=client.post('/api/content/'+item['id']+'/apply-fixes',headers=auth['creator']).json()
    second=result['content']['current_revision']
    assert client.post('/api/content/'+item['id']+'/submit',headers=auth['creator']).status_code==200
    assert client.post('/api/content/'+item['id']+'/approve',headers=auth['reviewer'],json={'revision_id':second['id'],'comment':'Verified source and corrected price.'}).status_code==200
    third=client.post('/api/content/'+item['id']+'/revisions',headers=auth['creator'],json={'title':'Changed title','body_text':'A newer unapproved draft','expected_revision_id':second['id']}).json()
    history=client.get('/api/content/'+item['id']+'/history',headers=auth['creator'])
    assert history.status_code==200,history.text
    data=history.json();assert data['persisted'] and len(data['revisions'])==3
    assert data['revisions'][0]['title']=='First title' and data['revisions'][0]['body_text']==initial['body_text']
    assert data['revisions'][1]['title']=='First title' and data['revisions'][1]['body_text']==second['body_text']
    assert data['revisions'][1]['approvals'][0]['body_hash']==second['body_hash']
    assert data['revisions'][2]['title']=='Changed title' and data['revisions'][2]['approvals']==[]
    assert {event['kind'] for event in data['events']} >= {'draft-created','revision-created','ai-check','rechecked','submitted','approved','finding-detected'}
    assert all(event['at'].endswith('+00:00') for event in data['events'])
    queue=client.get('/api/submissions',headers=auth['reviewer']).json()
    assert len(queue)==1 and queue[0]['status']=='approved' and queue[0]['revision_id']==second['id']
    assert queue[0]['current_revision_id']==third['current_revision']['id']
    assert client.post('/api/content/'+item['id']+'/approve',headers=auth['reviewer'],json={'revision_id':second['id']}).status_code==409


def test_history_and_submissions_are_scoped_and_do_not_invent_check_events(client,auth,brand,other_users):
    item=new_content(client,auth,brand)
    history=client.get('/api/content/'+item['id']+'/history',headers=auth['creator']).json()
    assert [event['kind'] for event in history['events']]==['draft-created']
    assert history['revisions'][0]['review_runs']==[]
    for headers in other_users:
        assert client.get('/api/content/'+item['id']+'/history',headers=headers).status_code==404
    assert client.get('/api/submissions',headers=auth['creator']).status_code==403
    assert client.get('/api/submissions',headers=other_users[0]).json()==[]


def test_real_team_account_login_preserves_password_and_permissions(client,auth,other_users):
    password='  fictional secure password  '
    response=client.post('/api/team',headers=auth['admin'],json={'name':'  Test Writer  ','email':' WRITER@example.test ','password':password,'role':'creator'})
    assert response.status_code==200,response.text
    assert response.json()['name']=='Test Writer' and response.json()['email']=='writer@example.test'
    assert 'password' not in response.text
    login=client.post('/api/auth/login',json={'email':'writer@example.test','password':password})
    assert login.status_code==200,login.text
    assert client.post('/api/auth/login',json={'email':'writer@example.test','password':password.strip()}).status_code==401
    writer={'Authorization':'Bearer '+login.json()['token']}
    assert client.get('/api/team',headers=writer).status_code==403
    assert client.post('/api/team',headers=writer,json={'name':'Bad','email':'bad@example.test','password':'fictional-long-pass','role':'admin'}).status_code==403
    assert len(client.get('/api/team',headers=auth['admin']).json())==5
    assert all(row['email']!='foreign@test' for row in client.get('/api/team',headers=auth['admin']).json())
    assert len(client.get('/api/team',headers=other_users[0]).json())==1
    assert client.post('/api/team',headers=auth['admin'],json={'name':'Another','email':'writer@example.test','password':'another-fictional-pass','role':'reviewer'}).status_code==409


def test_setup_is_one_time_and_creates_an_authenticated_real_workspace(client):
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    payload={'name':'First Admin','email':'first@example.test','password':'first fictional password','organisation':'Team Workspace','brand':'Uploaded Document Brand'}
    with patch.object(settings,'demo_mode',False):
        assert client.get('/api/setup').json()['setup_required']
        response=client.post('/api/setup',json=payload)
        assert response.status_code==200,response.text
        auth={'Authorization':'Bearer '+response.json()['token']}
        assert response.json()['user']['role']=='admin'
        assert client.get('/api/me',headers=auth).json()['org_name']=='Team Workspace'
        assert client.get('/api/brands',headers=auth).json()[0]['name']=='Uploaded Document Brand'
        assert client.get('/api/setup').json()['setup_required'] is False
        assert client.post('/api/setup',json=payload).status_code==409
        assert client.post('/api/auth/demo?role=admin').status_code==404
    with SessionLocal() as db:
        assert len(list(db.scalars(select(User))))==1
        assert len(list(db.scalars(select(Organisation))))==1
        assert len(list(db.scalars(select(Brand))))==1


def test_request_changes_requires_comment_and_history_persists_it(client,auth,brand):
    item=new_content(client,auth,brand,'A plain greeting.');review(client,auth,item)
    assert client.post('/api/content/'+item['id']+'/submit',headers=auth['creator']).status_code==200
    path='/api/content/'+item['id']+'/request-changes'
    for comment in [None,'','   ']:
        response=client.post(path,headers=auth['reviewer'],json={'revision_id':item['current_revision']['id'],'comment':comment})
        assert response.status_code==422,response.text
    assert client.post(path,headers=auth['reviewer'],json={'revision_id':item['current_revision']['id'],'comment':'Please specify the audience.'}).status_code==200
    data=client.get('/api/content/'+item['id']+'/history',headers=auth['creator']).json()
    assert data['revisions'][0]['approvals'][0]['comment']=='Please specify the audience.'
    assert any(event['kind']=='changes-requested' and event['comment']=='Please specify the audience.' for event in data['events'])


def test_document_brand_identity_comment_author_and_language_are_persisted(client,auth,brand):
    doc=upload(client,auth,brand)
    docs=client.get('/api/documents',headers=auth['creator']).json()
    saved=next(row for row in docs if row['id']==doc['id'])
    assert saved['brand_id']==brand and saved['uploaded_by_name']=='Demo Admin'
    assert client.get('/api/documents/'+doc['id'],headers=auth['creator']).json()['brand_id']==brand
    item=new_content(client,auth,brand,'A greeting.',context={'product':'Veyra Beat 200','region':'IN','language':'English'})
    review(client,auth,item)
    assert client.post('/api/content/'+item['id']+'/comments',headers=auth['reviewer'],json={'body':'Please consider the source.'}).status_code==200
    comments=client.get('/api/content/'+item['id']+'/comments',headers=auth['creator']).json()
    assert comments[0]['user_name']=='Demo Reviewer'
    history=client.get('/api/content/'+item['id']+'/history',headers=auth['creator']).json()
    assert history['revisions'][0]['context']['language']=='English'


def test_evaluation_is_a_labelled_development_report_with_role_guard(client,auth):
    assert client.get('/api/evaluation',headers=auth['creator']).status_code==403
    response=client.get('/api/evaluation',headers=auth['admin'])
    assert response.status_code==200 and response.json()['available']
    assert response.json()['report']['summary']['cases']==50
    assert 'synthetic' in response.json()['scope'].lower()
