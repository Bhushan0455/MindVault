"""Persisted frontend views and administration; no simulated business records."""
from datetime import timezone
import json
from pathlib import Path
from pydantic import BaseModel,Field,ConfigDict,field_validator
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User,Organisation,Brand,Content,Revision,ReviewRun,Finding,Approval,AuditEvent,Comment
from app.core.security import current_user,require_role,hash_password,issue_token
from app.core.config import settings
from app.services.audit import record

router=APIRouter(prefix='/api')


def iso(value):
    if value is None: return None
    return (value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()


def person(row):
    return {'id':row.id,'name':row.name,'email':row.email,'role':row.role} if row else {'id':None,'name':'Unavailable account','role':None}


class TeamIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=120)
    email:str=Field(min_length=3,max_length=255)
    password:str=Field(min_length=10,max_length=200)
    role:Literal['admin','creator','reviewer']='creator'
    @field_validator('name','email',mode='before')
    @classmethod
    def trim_identity(cls,value):
        return value.strip() if isinstance(value,str) else value
    @field_validator('email')
    @classmethod
    def email_address(cls,value):
        import re
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value): raise ValueError('Enter a valid email address')
        return value.casefold()


class SetupIn(TeamIn):
    organisation:str=Field(min_length=1,max_length=120)
    brand:str=Field(min_length=1,max_length=120)
    role:Literal['admin']='admin'
    @field_validator('organisation','brand',mode='before')
    @classmethod
    def trim_workspace(cls,value):
        return value.strip() if isinstance(value,str) else value


@router.get('/setup')
def setup_status(db:Session=Depends(get_db)):
    return {'setup_required':db.scalar(select(func.count()).select_from(User))==0,'demo_mode':settings.demo_mode}


@router.post('/setup')
def setup(data:SetupIn,db:Session=Depends(get_db)):
    if db.bind.dialect.name=='postgresql': db.execute(text('SELECT pg_advisory_xact_lock(734928107)'))
    elif db.bind.dialect.name=='sqlite': db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    if db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(409,detail='Workspace is already configured; ask an administrator to add your account')
    org=Organisation(name=data.organisation); db.add(org); db.flush()
    user=User(org_id=org.id,email=data.email,name=data.name,role='admin',password_hash=hash_password(data.password))
    db.add(user); db.flush(); db.add(Brand(org_id=org.id,name=data.brand))
    record(db,user,'workspace_created','organisation',org.id); db.commit()
    return {'token':issue_token(user),'user':{**person(user),'org_id':org.id,'org_name':org.name}}


@router.get('/team')
def team(user=Depends(require_role('admin')),db:Session=Depends(get_db)):
    return [person(row) for row in db.scalars(select(User).where(User.org_id==user.org_id).order_by(User.name))]


@router.post('/team')
def add_member(data:TeamIn,user=Depends(require_role('admin')),db:Session=Depends(get_db)):
    db.scalar(select(Organisation).where(Organisation.id==user.org_id).with_for_update())
    if db.scalar(select(User).where(User.email==data.email)): raise HTTPException(409,detail='An account already uses that email')
    row=User(org_id=user.org_id,**data.model_dump(exclude={'password'}),password_hash=hash_password(data.password))
    db.add(row); db.flush(); record(db,user,'team_member_created','user',row.id,{'role':row.role}); db.commit()
    return person(row)


@router.get('/content/{content_id}/history')
def content_history(content_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    from app.main import content_for,content_view,finding_view
    item=content_for(db,content_id,user)
    versions=list(db.scalars(select(Revision).where(Revision.content_id==item.id).order_by(Revision.number)))
    ids=[row.id for row in versions]
    runs=list(db.scalars(select(ReviewRun).where(ReviewRun.revision_id.in_(ids)).order_by(ReviewRun.created_at)))
    findings=list(db.scalars(select(Finding).where(Finding.revision_id.in_(ids))))
    approvals=list(db.scalars(select(Approval).where(Approval.content_id==item.id).order_by(Approval.created_at)))
    audits=list(db.scalars(select(AuditEvent).where(AuditEvent.org_id==user.org_id,AuditEvent.entity_type=='content',AuditEvent.entity_id==item.id)))
    people={row.id:person(row) for row in db.scalars(select(User).where(User.org_id==user.org_id))}
    events=[]; records=[]
    for revision in versions:
        creator=people.get(revision.created_by,person(None))
        events.append({'id':'revision:'+revision.id,'revision_id':revision.id,'revision_number':revision.number,
            'kind':'draft-created' if revision.number==1 else 'revision-created','actor':creator['name'],
            'at':iso(revision.created_at),'comment':'Immutable content revision saved','finding_id':None})
        revision_runs=[]
        for run in [r for r in runs if r.revision_id==revision.id]:
            fs=[f for f in findings if f.review_run_id==run.id]
            revision_runs.append({'id':run.id,'status':run.status,'created_at':iso(run.created_at),'finished_at':iso(run.finished_at),
                'ai_used':run.ai_used,'ai_status':run.ai_status,'model':run.model,'issues':run.issues,
                'applied_rules':run.applied_rules,'skipped_rules':run.skipped,'findings':[finding_view(f,db) for f in fs]})
            if run.status=='done' and run.finished_at:
                events.append({'id':'check:'+run.id,'revision_id':revision.id,'revision_number':revision.number,
                    'kind':'ai-check' if revision.number==1 else 'rechecked','actor':'AI + deterministic analysis' if run.ai_used else 'Deterministic analysis',
                    'at':iso(run.finished_at),'comment':'Completed review: '+run.ai_status,'finding_id':None})
                for finding in fs:
                    if finding.verdict=='supported': continue
                    events.append({'id':'finding:'+finding.id,'revision_id':revision.id,'revision_number':revision.number,
                        'kind':'finding-detected','actor':finding.origin+' analysis','at':iso(run.finished_at),
                        'comment':finding.explanation,'finding_id':finding.id})
        decisions=[]
        for approval in [a for a in approvals if a.revision_id==revision.id]:
            decision={'id':approval.id,'revision_id':revision.id,'body_hash':approval.body_hash,'decision':approval.decision,
                'comment':approval.comment,'reviewer':people.get(approval.reviewer_id,person(None)),'created_at':iso(approval.created_at)}
            decisions.append(decision)
            events.append({'id':'approval:'+approval.id,'revision_id':revision.id,'revision_number':revision.number,
                'kind':'approved' if approval.decision=='approved' else 'changes-requested','actor':decision['reviewer']['name'],
                'at':decision['created_at'],'comment':approval.comment or '','finding_id':None})
        submissions=[]
        for audit in [a for a in audits if a.event_type=='content_submitted' and a.payload.get('revision_id')==revision.id]:
            submissions.append(iso(audit.created_at))
            events.append({'id':'audit:'+audit.id,'revision_id':revision.id,'revision_number':revision.number,'kind':'submitted',
                'actor':people.get(audit.actor_id,person(None))['name'],'at':iso(audit.created_at),'comment':'Submitted for reviewer approval','finding_id':None})
        records.append({'id':revision.id,'number':revision.number,'title':revision.title,'body_text':revision.body_text,
            'body_hash':revision.body_hash,'context':revision.context,'created_at':iso(revision.created_at),'created_by':creator,
            'review_runs':revision_runs,'approvals':decisions,'submitted_at':submissions[-1] if submissions else None})
    return {'content':content_view(item,db),'revisions':records,'events':sorted(events,key=lambda e:(e['at'],e['id'])),'persisted':True}


@router.get('/submissions')
def submissions(user=Depends(require_role('admin','reviewer')),db:Session=Depends(get_db)):
    from app.main import finding_view
    items=list(db.scalars(select(Content).where(Content.org_id==user.org_id)))
    result=[]
    for item in items:
        latest=db.scalar(select(AuditEvent).where(AuditEvent.org_id==user.org_id,AuditEvent.entity_type=='content',
            AuditEvent.entity_id==item.id,AuditEvent.event_type=='content_submitted').order_by(AuditEvent.created_at.desc()))
        last_decision=db.scalar(select(Approval).where(Approval.content_id==item.id).order_by(Approval.created_at.desc()))
        revision_id=latest.payload.get('revision_id') if latest else last_decision.revision_id if last_decision else None
        if not revision_id: continue
        revision=db.get(Revision,revision_id)
        if not revision or revision.content_id!=item.id: continue
        decision=last_decision if last_decision and last_decision.revision_id==revision.id else None
        status=decision.decision if decision else 'in_review' if item.current_revision_id==revision.id and item.status=='in_review' else 'superseded'
        if status=='superseded': continue
        run=db.scalar(select(ReviewRun).where(ReviewRun.revision_id==revision.id,ReviewRun.status=='done').order_by(ReviewRun.created_at.desc()))
        fs=list(db.scalars(select(Finding).where(Finding.review_run_id==run.id))) if run else []
        brand=db.get(Brand,item.brand_id)
        result.append({'id':item.id,'brand_id':item.brand_id,'brand':brand.name if brand else 'Unavailable brand',
            'title':revision.title or item.title,'status':status,'revision_id':revision.id,'revision_number':revision.number,
            'body_text':revision.body_text,'body_hash':revision.body_hash,'context':revision.context,
            'creator':person(db.get(User,item.created_by)),'submitted_at':iso(latest.created_at) if latest else iso(decision.created_at),
            'decision_at':iso(decision.created_at) if decision else None,'current_revision_id':item.current_revision_id,
            'findings':[finding_view(f,db) for f in fs],'ai_status':run.ai_status if run else 'unavailable'})
    return result


@router.get('/evaluation')
def evaluation_report(user=Depends(require_role('admin'))):
    path=Path(__file__).resolve().parents[2]/'evaluation/results/evaluation_report.json'
    if not path.exists(): return {'available':False,'detail':'No saved deterministic evaluation report'}
    return {'available':True,'scope':'Saved synthetic development evaluation; not accuracy on your uploaded documents',
        'report':json.loads(path.read_text(encoding='utf-8'))}
