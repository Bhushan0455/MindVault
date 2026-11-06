"""Knowledge lifecycle: explicit approval, immutable versions, real extraction."""
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db, SessionLocal
from app.models import Brand, Rule, Fact, Document, KnowledgeCandidate, ServiceJob, ProductCatalog
from app.core.security import current_user, require_role
from app.core.config import settings
from app.knowledge_schemas import BrandIn, RuleIn, FactIn, CandidateApproval, ClarityAccept, ProductIn, ProductAliases
from app.services.audit import record
from app.services.integration import rule_contract, json_data
from app.services.extraction import extract_document
from app.services.knowledge_extract import extract_candidates
from app.services.llm import GeminiKnowledgeGenerator
from app.services.ai_clarity import run_clarity_audit, GeminiClarityGenerator
from app.services.clarity import rule_snapshot_hash
from app.services.job_status import expired
from app.services.ai_audit import save_ai_events

router = APIRouter(prefix='/api')


def find(db, model, row_id, user):
    row = db.scalar(select(model).where(model.id == row_id, model.org_id == user.org_id))
    if row is None: raise HTTPException(404, detail='Resource not found')
    # Every mutation locks brand before child records, avoiding reversed lock
    # order when two administrators approve competing knowledge versions.
    if model is not Brand: find(db, Brand, row.brand_id, user)
    db.refresh(row, with_for_update=True)
    return row


def view(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def verify_source(data, db, user):
    find(db, Brand, data.brand_id, user)
    if data.source_document_id:
        doc = find(db, Document, data.source_document_id, user)
        if doc.brand_id != data.brand_id: raise HTTPException(422, detail='Source belongs to another brand')
        extracted = extract_document(doc.filename, doc.file_bytes)
        if not data.source_excerpt or not data.source_location or not any(
            b.location == data.source_location and data.source_excerpt in b.text for b in extracted.blocks):
            raise HTTPException(422, detail='Source quote and location must match the uploaded document')


def add_knowledge(data, db, user, old=None):
    verify_source(data, db, user)
    model = Rule if isinstance(data, RuleIn) else Fact
    if isinstance(data, RuleIn):
        existing = db.scalar(select(Rule).where(Rule.org_id == user.org_id, Rule.brand_id == data.brand_id,
                                               Rule.code == data.code))
        if existing and old is None: raise HTTPException(409, detail='Rule code exists; edit that rule to create a version')
    values = data.model_dump()
    if isinstance(data,FactIn):
        for product in db.scalars(select(ProductCatalog).where(ProductCatalog.org_id==user.org_id,ProductCatalog.brand_id==data.brand_id)):
            if data.product.casefold() in {name.casefold() for name in [product.name,*product.aliases]}:
                values['product']=product.name
                break
    row = model(org_id=user.org_id, status='pending', **values)
    if old:
        successors = list(db.scalars(select(model).where(model.org_id == user.org_id,
            model.brand_id == old.brand_id)))
        family = [r for r in successors if (r.code == old.code if model is Rule else
            (r.product,r.attribute,r.market) == (old.product,old.attribute,old.market))]
        row.version = max(r.version for r in family) + 1
        row.supersedes_id = old.id
    db.add(row); db.flush()
    record(db,user,'knowledge_created',model.__tablename__,row.id,{'status':'pending','version':row.version})
    return row


def edit_knowledge(model, row_id, changes, db, user):
    old = find(db, model, row_id, user)
    schema = RuleIn if model is Rule else FactIn
    values = {name: getattr(old,name) for name in schema.model_fields}
    if any(k not in values for k in changes): raise HTTPException(422, detail='Unknown or immutable fields')
    if any(k in changes and changes[k] != values[k] for k in ('brand_id','code','product','attribute','market') if k in values):
        raise HTTPException(422, detail='Knowledge identity cannot change between versions')
    values.update(changes)
    try: data = schema.model_validate(values)
    except ValidationError: raise HTTPException(422, detail='Invalid knowledge fields')
    row = add_knowledge(data, db, user, old)
    return row


def approve_knowledge(row, db, user):
    if row.status != 'pending': raise HTTPException(409, detail='Only pending knowledge can be approved')
    # Lock the brand to serialize competing replacements in PostgreSQL.
    find(db, Brand, row.brand_id, user)
    model = type(row)
    if row.supersedes_id:
        ancestors=[]
        previous_id=row.supersedes_id
        while previous_id:
            previous=find(db,model,previous_id,user)
            if previous.status=='superseded': raise HTTPException(409,detail='A newer version was already approved')
            ancestors.append(previous)
            if previous.status=='approved': break
            previous_id=previous.supersedes_id
        for previous in ancestors:
            if previous.status!='rejected': previous.status='superseded'
    row.status = 'approved'
    if isinstance(row, Rule): row.approved_by = user.id
    record(db,user,'knowledge_approved',model.__tablename__,row.id,{'version':row.version})


@router.post('/brands')
def create_brand(data: BrandIn,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=Brand(org_id=user.org_id,name=data.name); db.add(row); db.flush()
    record(db,user,'brand_created','brand',row.id); db.commit(); return view(row)


def validate_product_aliases(db,user,brand_id,name,aliases,exclude=None):
    tokens=[t.casefold().strip() for t in [name,*aliases]]
    if len(tokens)!=len(set(tokens)): raise HTTPException(422,detail='Product names and aliases must be distinct')
    others=db.scalars(select(ProductCatalog).where(ProductCatalog.org_id==user.org_id,ProductCatalog.brand_id==brand_id))
    for row in others:
        if row.id!=exclude and set(tokens)&{t.casefold().strip() for t in [row.name,*row.aliases]}:
            raise HTTPException(409,detail='Product name or alias already belongs to another product')
    # An alias must not hide a canonical legacy fact product that has no
    # explicit catalogue record yet.
    fact_names=db.scalars(select(Fact.product).where(Fact.org_id==user.org_id,Fact.brand_id==brand_id))
    if {t.casefold().strip() for t in aliases}&{n.casefold().strip() for n in fact_names if n.casefold().strip()!=name.casefold().strip()}:
        raise HTTPException(409,detail='An alias conflicts with an existing fact product name')


@router.get('/products')
def products(brand_id: str|None=None,user=Depends(current_user),db: Session=Depends(get_db)):
    q=select(ProductCatalog).where(ProductCatalog.org_id==user.org_id)
    if brand_id: q=q.where(ProductCatalog.brand_id==brand_id)
    return [view(row) for row in db.scalars(q)]


@router.post('/products')
def create_product(data: ProductIn,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    find(db,Brand,data.brand_id,user)
    validate_product_aliases(db,user,data.brand_id,data.name,data.aliases)
    row=ProductCatalog(org_id=user.org_id,**data.model_dump()); db.add(row); db.flush()
    record(db,user,'product_created','product',row.id); db.commit(); return view(row)


@router.patch('/products/{product_id}')
def update_aliases(product_id: str,data: ProductAliases,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=find(db,ProductCatalog,product_id,user)
    validate_product_aliases(db,user,row.brand_id,row.name,data.aliases,exclude=row.id)
    row.aliases=data.aliases; record(db,user,'product_aliases_updated','product',row.id); db.commit(); return view(row)


@router.get('/rules')
def list_rules(status: str|None=None,brand_id: str|None=None,user=Depends(current_user),db: Session=Depends(get_db)):
    q=select(Rule).where(Rule.org_id==user.org_id)
    if status: q=q.where(Rule.status==status)
    if brand_id: q=q.where(Rule.brand_id==brand_id)
    return [view(r) for r in db.scalars(q)]


@router.post('/rules')
def create_rule(data: RuleIn,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=add_knowledge(data,db,user); db.commit(); return view(row)


@router.patch('/rules/{rule_id}')
def edit_rule(rule_id: str,data: dict,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=edit_knowledge(Rule,rule_id,data,db,user); db.commit(); return view(row)


@router.post('/rules/{rule_id}/approve')
def approve_rule(rule_id: str,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=find(db,Rule,rule_id,user); approve_knowledge(row,db,user); db.commit(); return view(row)


@router.post('/rules/{rule_id}/reject')
def reject_rule(rule_id: str,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=find(db,Rule,rule_id,user)
    if row.status!='pending': raise HTTPException(409,detail='Only pending knowledge can be rejected')
    row.status='rejected'; record(db,user,'knowledge_rejected','rule',row.id); db.commit(); return view(row)


@router.get('/facts')
def list_facts(user=Depends(current_user),db: Session=Depends(get_db)):
    return [view(r) for r in db.scalars(select(Fact).where(Fact.org_id==user.org_id))]


@router.post('/facts')
def create_fact(data: FactIn,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=add_knowledge(data,db,user); db.commit(); return view(row)


@router.patch('/facts/{fact_id}')
def edit_fact(fact_id: str,data: dict,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=edit_knowledge(Fact,fact_id,data,db,user); db.commit(); return view(row)


@router.post('/facts/{fact_id}/approve')
def approve_fact(fact_id: str,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=find(db,Fact,fact_id,user); approve_knowledge(row,db,user); db.commit(); return view(row)


@router.post('/facts/{fact_id}/reject')
def reject_fact(fact_id: str,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=find(db,Fact,fact_id,user)
    if row.status!='pending': raise HTTPException(409,detail='Only pending knowledge can be rejected')
    row.status='rejected'; record(db,user,'knowledge_rejected','fact',row.id); db.commit(); return view(row)


def extraction_job(job_id, document_id):
    with SessionLocal() as db:
        job=db.get(ServiceJob,job_id,with_for_update=True)
        if not job or job.status!='queued': return
        try:
            job.status='running'; db.commit()
            doc=db.get(Document,document_id)
            extracted=extract_document(doc.filename,doc.file_bytes)
            generator=GeminiKnowledgeGenerator(org_id=doc.org_id,brand_id=doc.brand_id) if settings.enable_semantic else None
            result=extract_candidates(extracted,org_id=doc.org_id,brand_id=doc.brand_id,document_id=doc.id,generator=generator)
            save_ai_events(db,generator,org_id=doc.org_id,actor_id=doc.uploaded_by,entity_type='extraction_job',entity_id=job.id)
            db.refresh(job,with_for_update=True)
            if job.status not in ('queued','running'):
                db.rollback(); return
            # Serialize repeated extraction saves for one document.
            db.refresh(doc,with_for_update=True)
            groups={'rules':[],'facts':[]}
            for candidate in result.candidates:
                saved=db.get(KnowledgeCandidate,candidate.id)
                if not saved:
                    saved=KnowledgeCandidate(id=candidate.id,org_id=doc.org_id,brand_id=doc.brand_id,
                        document_id=doc.id,kind=candidate.kind,data=json_data(candidate),status='pending')
                    db.add(saved)
                groups[candidate.kind+'s'].append(candidate.id)
            job.result={'document_id':doc.id,'method':result.method,'issues':list(result.issues),'candidates':groups}
            job.status='done'; db.commit()
        except Exception:
            db.rollback(); job=db.get(ServiceJob,job_id); job.status='failed'
            job.result={'code':'extraction_failed','detail':'Extraction could not be completed'}; db.commit()


@router.post('/documents/{document_id}/extract',status_code=202)
def start_extraction(document_id: str,tasks: BackgroundTasks,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    doc=find(db,Document,document_id,user)
    job=ServiceJob(org_id=user.org_id,brand_id=doc.brand_id,kind='extraction',status='queued')
    db.add(job); db.flush(); record(db,user,'extraction_requested','document',doc.id,{'job_id':job.id})
    db.commit(); tasks.add_task(extraction_job,job.id,doc.id)
    return {'job_id':job.id,'status':'queued','document_id':doc.id}


@router.get('/jobs/{job_id}')
def get_job(job_id: str,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=find(db,ServiceJob,job_id,user)
    if expired(row):
        row.status='failed'; row.result={'code':'job_timeout','detail':'Job exceeded its time limit; retry extraction'}; db.commit()
    return view(row)


@router.get('/sources/{document_id}')
def source(document_id: str,location: str=Query(...),user=Depends(current_user),db: Session=Depends(get_db)):
    doc=find(db,Document,document_id,user)
    extracted=extract_document(doc.filename,doc.file_bytes)
    blocks=[asdict(b) for b in extracted.blocks if b.location==location]
    if not blocks: raise HTTPException(404,detail='Source location not found')
    return {'document_id':doc.id,'document_title':doc.title,'blocks':blocks,'warnings':list(extracted.warnings)}


@router.get('/documents/{document_id}/candidates')
def candidates(document_id: str,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    find(db,Document,document_id,user)
    return [view(r) for r in db.scalars(select(KnowledgeCandidate).where(
        KnowledgeCandidate.document_id==document_id,KnowledgeCandidate.org_id==user.org_id))]


@router.post('/candidates/{candidate_id}/approve')
def approve_candidate(candidate_id: str,data: CandidateApproval,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=find(db,KnowledgeCandidate,candidate_id,user)
    if row.status!='pending': raise HTTPException(409,detail='Candidate already decided')
    knowledge=data.knowledge
    if (row.kind=='rule') != isinstance(knowledge,RuleIn) or knowledge.brand_id!=row.brand_id:
        raise HTTPException(422,detail='Candidate kind and brand must match')
    source=row.data['source']
    knowledge=knowledge.model_copy(update={'source_document_id':row.document_id,
        'source_location':source['location'],'source_excerpt':source['excerpt']})
    saved=add_knowledge(knowledge,db,user); approve_knowledge(saved,db,user)
    row.status='approved'; row.knowledge_id=saved.id
    record(db,user,'candidate_approved','candidate',row.id,{'knowledge_id':saved.id}); db.commit()
    return {'candidate':view(row),'knowledge':view(saved)}


@router.post('/candidates/{candidate_id}/reject')
def reject_candidate(candidate_id: str,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    row=find(db,KnowledgeCandidate,candidate_id,user)
    if row.status!='pending': raise HTTPException(409,detail='Candidate already decided')
    row.status='rejected'; record(db,user,'candidate_rejected','candidate',row.id); db.commit(); return view(row)


@router.post('/brands/{brand_id}/clarity')
def clarity(brand_id: str,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    find(db,Brand,brand_id,user)
    rows=list(db.scalars(select(Rule).where(Rule.org_id==user.org_id,Rule.brand_id==brand_id,Rule.status=='approved')))
    generator=GeminiClarityGenerator(org_id=user.org_id,brand_id=brand_id) if settings.enable_semantic else None
    result=run_clarity_audit([rule_contract(r,db) for r in rows],org_id=user.org_id,brand_id=brand_id,generator=generator)
    job=ServiceJob(org_id=user.org_id,brand_id=brand_id,kind='clarity',status='done',result=json_data(result))
    db.add(job); db.flush(); record(db,user,'clarity_audit','brand',brand_id,{'job_id':job.id}); db.commit()
    save_ai_events(db,generator,org_id=user.org_id,actor_id=user.id,entity_type='clarity_job',entity_id=job.id); db.commit()
    return view(job)


@router.post('/clarity/{job_id}/accept')
def accept_clarity(job_id: str,data: ClarityAccept,user=Depends(require_role('admin')),db: Session=Depends(get_db)):
    job=find(db,ServiceJob,job_id,user)
    proposal=next((p for p in job.result.get('findings',[]) if p['id']==data.proposal_id),None)
    if job.kind!='clarity' or not proposal: raise HTTPException(404,detail='Proposal not found')
    old=find(db,Rule,proposal['rule_id'],user)
    if old.status!='approved' or rule_snapshot_hash(rule_contract(old,db))!=proposal['rule_snapshot_hash']:
        raise HTTPException(409,detail='Rule changed; run the clarity audit again')
    if proposal.get('accepted_rule_id'): raise HTTPException(409,detail='Proposal already accepted')
    row=edit_knowledge(Rule,old.id,{'instruction':data.instruction},db,user)
    result=dict(job.result); result['findings']=[dict(p,accepted_rule_id=row.id) if p['id']==data.proposal_id else p for p in result['findings']]
    job.result=result; record(db,user,'clarity_proposed','rule',row.id); db.commit(); return view(row)
