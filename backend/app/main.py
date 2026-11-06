import hashlib, time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query, UploadFile, File, Form, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.db import Base, engine, SessionLocal, get_db
from app.models import User, Organisation, Brand, Rule, Fact, Content, Revision, ReviewRun, Finding, Approval, AuditEvent, Document
from app.schemas import LoginIn, ContentIn, DecisionIn, ApprovalIn, CommentIn
from app.core.config import settings
from app.core.security import current_user, require_role, verify_password, issue_token
from app.services.seed import seed
from app.services.integration import review_revision, json_data, stored_finding, knowledge_fingerprint, evidence_snapshot
from app.services.fixes import apply_selected_fixes, FixDecision, FixError
from app.routers.knowledge import router as knowledge_router
from app.services.audit import record
from app.body_limit import BodyLimitMiddleware
from app.services.job_status import expired

@asynccontextmanager
async def lifespan(app):
    startup()
    yield


app = FastAPI(title="MindVault AI API", version="2.0.0", description="Integrated Role A + Role B API", lifespan=lifespan)
app.include_router(knowledge_router)
app.add_middleware(BodyLimitMiddleware,upload_limit=settings.max_upload_mb*1024*1024)
# Allowed browser origins are configured explicitly.
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])

@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    from fastapi.responses import JSONResponse
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = detail
    else:
        codes = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405:"method_not_allowed", 409: "conflict", 422: "validation_error"}
        body = {"detail": str(detail), "code": codes.get(exc.status_code, "request_error")}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={"detail": "Request fields are invalid", "code": "validation_error"})

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred", "code": "internal_error"},
        headers={"Access-Control-Allow-Origin": request.headers['origin'], "Vary": "Origin"}
        if request.headers.get('origin') in settings.cors_origins else {})

def digest(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def user_dict(u, db):
    org = db.get(Organisation, u.org_id)
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "org_id": u.org_id, "org_name": org.name if org else ""}
def token_response(u, db): return {"token": issue_token(u), "user": user_dict(u, db)}
def scoped(db, model, user): return select(model).where(model.org_id == user.org_id)
def not_found(): raise HTTPException(404, detail={"detail": "Resource not found", "code": "not_found"})
def content_for(db, content_id, user):
    row = db.scalar(scoped(db, Content, user).where(Content.id == content_id).with_for_update())
    if row is None or (user.role == "creator" and row.created_by != user.id): not_found()
    return row
def revision_for(db, content):
    return db.get(Revision, content.current_revision_id) if content.current_revision_id else None
def finding_view(f, db):
    snapshot = dict(f.snapshot or {})
    nested = snapshot.pop('_api',{})
    if not snapshot:
        snapshot={key:getattr(f,key) for key in ('origin','category','severity','confidence','verdict',
            'span_start','span_end','quoted_text','explanation','suggested_fix','rule_id','fact_id')}
        snapshot.update(source=None,legacy=True)
    result = {"id": f.id, "revision_id": f.revision_id, **snapshot,
        "status": f.status, "decision_note": f.decision_note, "edited_text": f.edited_text}
    rule = snapshot.get('rule_id')
    result['rule'] = nested.get('rule') or ({"id": rule, "code": snapshot.get('rule_code'), "version": snapshot.get('rule_version')} if rule else None)
    fact = snapshot.get('fact_id')
    result['fact'] = nested.get('fact') or ({"id": fact, "version": snapshot.get('fact_version'),
        "source_document": (snapshot.get('source') or {}).get('document_title'),
        "location": (snapshot.get('source') or {}).get('location')} if fact else None)
    result['offset_unit'] = 'unicode_code_points'
    return result

def content_view(c, db, include_run=False):
    rev = revision_for(db, c); creator = db.get(User, c.created_by)
    ctx = rev.context if rev else {}
    result = {"id": c.id, "title": c.title, "brand_id": c.brand_id, "status": c.status, "context": ctx,
      "current_revision": {"id": rev.id, "number": rev.number, "body_text": rev.body_text, "body_hash": rev.body_hash} if rev else None,
      "latest_run_id": c.latest_run_id, "created_by": {"id": creator.id, "name": creator.name} if creator else None,
      "created_at": rev.created_at.isoformat() if rev else None, "updated_at": rev.created_at.isoformat() if rev else None}
    return result

def run_review(run_id):
    db = SessionLocal()
    try:
        run = db.get(ReviewRun, run_id, with_for_update=True)
        if not run or run.status!='queued': return
        run.status, run.progress_step = "running", "intake"; db.commit()
        rev = db.get(Revision, run.revision_id)
        item = db.get(Content, rev.content_id)
        run.progress_step = "context"; db.commit()
        result, knowledge_hash = review_revision(rev, item, db)
        db.refresh(run,with_for_update=True)
        if run.status not in ('queued','running'):
            db.rollback()
            return
        run.applied_rules = [{"id": a.rule.id, "code": a.rule.code, "version": a.rule.version, "why": a.why} for a in result.resolution.applied]
        run.skipped = [{"id": a.rule.id, "code": a.rule.code, "version": a.rule.version, "reason": a.reason} for a in result.resolution.skipped]
        run.ai_used, run.ai_status, run.model, run.issues = result.ai_used, result.ai_status, result.model, list(result.issues)
        run.knowledge_hash = knowledge_hash
        for finding in result.findings:
            data = json_data(finding)
            data['_api'] = evidence_snapshot(finding,db)
            values = {key: data[key] for key in ('origin','category','severity','confidence','verdict','span_start',
                'span_end','quoted_text','explanation','suggested_fix','rule_id','fact_id')}
            db.add(Finding(review_run_id=run.id, revision_id=rev.id, snapshot=data, **values))
        run.status, run.progress_step, run.finished_at = "done", "done", datetime.now(timezone.utc)
        # Re-read under lock: an older worker must never overwrite a newer revision.
        db.refresh(item, with_for_update=True)
        if item.current_revision_id == rev.id and item.latest_run_id == run.id and item.status not in ("in_review", "approved"):
            item.status = "checked"
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(ReviewRun, run_id)
        if run:
            run.status, run.progress_step, run.error, run.finished_at = "failed", "done", "Review could not be completed", datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()

def startup():
    for attempt in range(30):
        try:
            Base.metadata.create_all(engine)
            from app.migration import require_current_schema
            require_current_schema(engine)
            with SessionLocal() as db:
                if settings.demo_mode: seed(db)
            return
        except RuntimeError:
            raise
        except Exception:
            if attempt == 29: raise RuntimeError("Database unavailable after 30 seconds; verify DATABASE_URL and database access")
            time.sleep(1)

@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try: db.execute(text("SELECT 1")); connected = True
    except Exception: connected = False
    return {"status": "ok" if connected else "degraded", "db": connected,
        "ai_configured": bool(settings.gemini_api_key and settings.gemini_model),
        "semantic_enabled": settings.enable_semantic, "demo_mode":settings.demo_mode,
        "ai_verification_scope":"per_service_result"}

@app.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or (not settings.demo_mode and user.email in {'admin@demo','creator@demo','reviewer@demo'}) or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, detail={"detail": "Email or password is incorrect", "code": "invalid_credentials"})
    return token_response(user, db)

@app.post("/api/auth/demo")
def demo(role: str = Query(..., pattern="^(admin|creator|reviewer)$"), db: Session = Depends(get_db)):
    if not settings.demo_mode: not_found()
    user = db.scalar(select(User).where(User.email == f"{role}@demo"))
    if not user: not_found()
    return token_response(user, db)

@app.get("/api/me")
def me(user=Depends(current_user), db: Session = Depends(get_db)): return user_dict(user, db)

@app.get("/api/brands")
def brands(user=Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": x.id, "name": x.name} for x in db.scalars(scoped(db, Brand, user))]

@app.post("/api/documents")
async def upload_document(file: UploadFile=File(...), brand_id: str=Form(...), kind: str=Form(...,min_length=1,max_length=40),user=Depends(require_role("admin")),db: Session=Depends(get_db)):
    import hashlib
    from app.services.extraction import extract_document as parse_document, ExtractionError
    brand=db.scalar(scoped(db,Brand,user).where(Brand.id==brand_id))
    if not brand: not_found()
    raw=await file.read(settings.max_upload_mb*1024*1024 + 1)
    if len(raw)>settings.max_upload_mb*1024*1024: raise HTTPException(413,detail={"detail":"File exceeds the upload limit","code":"file_too_large"})
    if not file.filename or not file.filename.lower().endswith((".pdf",".docx",".txt")):
        raise HTTPException(422,detail={"detail":"Only PDF, DOCX and TXT files are supported","code":"unsupported_file_type"})
    try: extracted=parse_document(file.filename,raw,max_upload_bytes=settings.max_upload_mb*1024*1024)
    except ExtractionError as exc: raise HTTPException(422,detail={"detail":exc.detail,"code":exc.code})
    if len(extracted.filename)>255: raise HTTPException(422,detail='Filename exceeds 255 characters')
    row=Document(org_id=user.org_id,brand_id=brand.id,title=extracted.filename,kind=kind,filename=extracted.filename,file_bytes=raw,text=extracted.text,content_hash=hashlib.sha256(raw).hexdigest(),uploaded_by=user.id)
    db.add(row); db.flush(); record(db,user,"document_uploaded","document",row.id,{"filename":file.filename,"kind":kind}); db.commit(); db.refresh(row)
    return {"id":row.id,"title":row.title,"filename":row.filename,"kind":row.kind,"status":"uploaded","text_length":len(extracted.text)}

@app.get("/api/documents")
def list_documents(user=Depends(current_user),db: Session=Depends(get_db)):
    return [{"id":d.id,"title":d.title,"filename":d.filename,"kind":d.kind,"version":d.version,"created_at":d.created_at.isoformat()} for d in db.scalars(scoped(db,Document,user))]

@app.get("/api/documents/{document_id}")
def get_document(document_id: str,user=Depends(current_user),db: Session=Depends(get_db)):
    d=db.scalar(scoped(db,Document,user).where(Document.id==document_id))
    if not d: not_found()
    return {"id":d.id,"title":d.title,"filename":d.filename,"kind":d.kind,"text":d.text,"version":d.version,"content_hash":d.content_hash}

@app.post("/api/content")
def create_content(data: ContentIn, user=Depends(require_role("creator", "admin")), db: Session = Depends(get_db)):
    brand = db.scalar(scoped(db, Brand, user).where(Brand.id == data.brand_id)) if data.brand_id else db.scalar(scoped(db, Brand, user))
    if not brand: not_found()
    item = Content(org_id=user.org_id, brand_id=brand.id, title=data.title, created_by=user.id, status="draft")
    db.add(item); db.flush()
    rev = Revision(content_id=item.id, number=1, body_text=data.body_text, body_hash=digest(data.body_text), created_by=user.id,
                   context=data.context.model_dump(mode="json"))
    db.add(rev); db.flush(); item.current_revision_id = rev.id
    record(db, user, "content_created", "content", item.id, {"revision_id": rev.id}); db.commit(); db.refresh(item)
    return content_view(item, db)

@app.get("/api/content")
def list_content(user=Depends(current_user), db: Session = Depends(get_db)):
    q = scoped(db, Content, user)
    if user.role == "creator": q = q.where(Content.created_by == user.id)
    return [content_view(c, db) for c in db.scalars(q)]

@app.get("/api/content/{content_id}")
def get_content(content_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    c = content_for(db, content_id, user)
    if user.role == "creator" and c.created_by != user.id: not_found()
    return content_view(c, db)

@app.post("/api/content/{content_id}/revisions")
def edit_content(content_id: str, data: ContentIn, user=Depends(require_role("creator", "admin")), db: Session = Depends(get_db)):
    c = content_for(db, content_id, user)
    if user.role == "creator" and c.created_by != user.id: not_found()
    prev = revision_for(db, c)
    if data.brand_id and data.brand_id != c.brand_id: raise HTTPException(422, detail="A revision cannot change brand")
    if data.expected_revision_id and data.expected_revision_id != prev.id: raise HTTPException(409, detail="Revision changed; refresh first")
    c.title=data.title
    context=data.context.model_dump(mode="json") if 'context' in data.model_fields_set else prev.context
    rev = Revision(content_id=c.id, number=prev.number+1, body_text=data.body_text, body_hash=digest(data.body_text), created_by=user.id, context=context)
    db.add(rev); db.flush(); c.current_revision_id = rev.id; c.latest_run_id = None; c.status = "draft"
    record(db, user, "revision_created", "content", c.id, {"revision_id": rev.id}); db.commit(); db.refresh(c)
    return content_view(c, db)

@app.get("/api/content/{content_id}/revisions/{number}")
def revision_detail(content_id: str, number: int, user=Depends(current_user), db: Session=Depends(get_db)):
    c=content_for(db,content_id,user); r=db.scalar(select(Revision).where(Revision.content_id==c.id,Revision.number==number))
    if not r: not_found()
    return {"id":r.id,"number":r.number,"body_text":r.body_text,"body_hash":r.body_hash,"context":r.context,"created_at":r.created_at.isoformat()}

@app.get("/api/content/{content_id}/diff")
def revision_diff(content_id: str, from_: int=Query(alias="from"), to: int=Query(...), user=Depends(current_user), db: Session=Depends(get_db)):
    import difflib
    c=content_for(db,content_id,user); a=db.scalar(select(Revision).where(Revision.content_id==c.id,Revision.number==from_)); b=db.scalar(select(Revision).where(Revision.content_id==c.id,Revision.number==to))
    if not a or not b: not_found()
    return {"from":from_,"to":to,"diff":list(difflib.unified_diff(a.body_text.splitlines(),b.body_text.splitlines(),lineterm=""))}

@app.post("/api/content/{content_id}/review", status_code=202)
def start_review(content_id: str, tasks: BackgroundTasks, user=Depends(require_role("creator", "admin")), db: Session=Depends(get_db)):
    c=content_for(db,content_id,user)
    if user.role=="creator" and c.created_by!=user.id: not_found()
    if c.status in ('in_review','approved'): raise HTTPException(409,detail="Create a new revision before reviewing submitted content")
    previous=db.get(ReviewRun,c.latest_run_id) if c.latest_run_id else None
    if previous and previous.status in ('queued','running'): raise HTTPException(409,detail="A review is already running")
    rev=revision_for(db,c); run=ReviewRun(revision_id=rev.id,status="queued",progress_step="intake")
    db.add(run); db.flush(); c.latest_run_id=run.id; db.commit(); tasks.add_task(run_review,run.id)
    return {"run_id":run.id}

@app.get("/api/review-runs/{run_id}")
def get_run(run_id: str,user=Depends(current_user),db: Session=Depends(get_db)):
    run=db.get(ReviewRun,run_id); rev=db.get(Revision,run.revision_id) if run else None; c=db.get(Content,rev.content_id) if rev else None
    if not c or c.org_id!=user.org_id or (user.role=="creator" and c.created_by!=user.id): not_found()
    if expired(run):
        db.refresh(run,with_for_update=True)
        if expired(run):
            run.status='failed'; run.progress_step='done'; run.error='Review exceeded its time limit; retry the review'
            run.finished_at=datetime.now(timezone.utc); db.commit()
    findings=list(db.scalars(select(Finding).where(Finding.review_run_id==run.id)))
    return {"id":run.id,"content_id":c.id,"revision_id":rev.id,"revision_number":rev.number,"status":run.status,"progress_step":run.progress_step,"ai_used":run.ai_used,"ai_status":run.ai_status,"model":run.model,"issues":run.issues,"error":run.error,"applied_rules":run.applied_rules,"skipped_rules":run.skipped,"findings":[finding_view(f,db) for f in findings]}

@app.post("/api/findings/{finding_id}/decision")
def decide(finding_id: str, data: DecisionIn, user=Depends(require_role("creator","admin")), db: Session=Depends(get_db)):
    f=db.get(Finding,finding_id); rev=db.get(Revision,f.revision_id) if f else None; c=db.get(Content,rev.content_id) if rev else None
    if not c or c.org_id!=user.org_id or (user.role=="creator" and c.created_by!=user.id): not_found()
    c=content_for(db,c.id,user)
    run=db.get(ReviewRun,f.review_run_id)
    if not run or run.status!='done' or c.current_revision_id!=rev.id or c.latest_run_id!=f.review_run_id or c.status in ('in_review','approved'):
        raise HTTPException(409,detail="Finding is stale or content has already been submitted")
    if f.verdict=='supported' and data.action in ('accept','edit'):
        raise HTTPException(422,detail="A supported finding is not a correction")
    if data.action=='accept' and f.suggested_fix is None: raise HTTPException(422,detail="No suggested fix is available")
    if data.action=='dismiss' and f.verdict!='supported':
        raise HTTPException(422,detail="Use reject with a reason to acknowledge an unresolved finding")
    if data.action=="reject" and not (data.note and data.note.strip()):
        raise HTTPException(422,detail={"detail":"A reason is required when rejecting a finding","code":"rejection_reason_required"})
    if data.action=="edit" and data.edited_text is None:
        raise HTTPException(422,detail={"detail":"edited_text is required for an edit","code":"edited_text_required"})
    f.status={"accept":"accepted","edit":"edited","reject":"rejected","dismiss":"dismissed"}[data.action]
    f.edited_text=data.edited_text; f.decision_note=data.note; f.decided_by=user.id
    record(db,user,"finding_decision","finding",f.id,{"action":data.action}); db.commit(); return finding_view(f,db)

@app.post("/api/content/{content_id}/apply-fixes")
def apply_fixes(content_id: str,tasks: BackgroundTasks,user=Depends(require_role("creator","admin")),db: Session=Depends(get_db)):
    c=content_for(db,content_id,user); prev=revision_for(db,c)
    if user.role=="creator" and c.created_by!=user.id: not_found()
    run=db.get(ReviewRun,c.latest_run_id) if c.latest_run_id else None
    if not run or run.revision_id!=prev.id or run.status!="done": raise HTTPException(409,detail={"detail":"Review the current revision before applying fixes","code":"review_required"})
    fs=list(db.scalars(select(Finding).where(Finding.review_run_id==run.id,Finding.status.in_(["accepted","edited"]))))
    if c.status in ('in_review','approved'): raise HTTPException(409,detail="Create a new revision before applying fixes")
    try:
        result=apply_selected_fixes(prev.body_text,revision_id=prev.id,expected_body_hash=prev.body_hash,
            decisions=[FixDecision(f.id,f.revision_id,stored_finding(f),f.status,f.edited_text,f.decision_note) for f in fs])
    except FixError as exc: raise HTTPException(409,detail={"detail":str(exc),"code":exc.code})
    if not result.changed: raise HTTPException(409,detail={"detail":"No changes are ready to apply","code":"no_fixes"})
    body=result.body_text
    rev=Revision(content_id=c.id,number=prev.number+1,body_text=body,body_hash=digest(body),created_by=user.id,context=prev.context)
    db.add(rev); db.flush(); c.current_revision_id=rev.id; c.status="draft"
    newrun=ReviewRun(revision_id=rev.id,status="queued",progress_step="intake"); db.add(newrun); db.flush(); c.latest_run_id=newrun.id
    record(db,user,"fixes_applied","content",c.id,{"revision_id":rev.id,"run_id":newrun.id}); db.commit(); tasks.add_task(run_review,newrun.id)
    return {"content":content_view(c,db),"run_id":newrun.id}

@app.post("/api/content/{content_id}/submit")
def submit(content_id: str,user=Depends(require_role("creator","admin")),db: Session=Depends(get_db)):
    c=content_for(db,content_id,user); rev=revision_for(db,c)
    if user.role=="creator" and c.created_by!=user.id: not_found()
    run=db.get(ReviewRun,c.latest_run_id) if c.latest_run_id else None
    if c.status not in ("draft","checked","changes_requested"): raise HTTPException(409,detail="Content cannot be submitted from this state")
    blocking=[] if not run or run.revision_id!=rev.id or run.status!="done" else list(db.scalars(select(Finding).where(Finding.review_run_id==run.id,Finding.status.in_(["open","accepted","edited"]),Finding.verdict!="supported",Finding.severity.in_(["critical","high"]))))
    if not run or run.revision_id!=rev.id or run.status!="done" or blocking:
        raise HTTPException(409,detail={"detail":"Current revision must have a finished review and no unresolved critical/high findings; accepted fixes must be applied and reviewed","code":"open_findings","finding_ids":[f.id for f in blocking]})
    if run.knowledge_hash!=knowledge_fingerprint(c,db):
        raise HTTPException(409,detail={"detail":"Knowledge changed; review the current revision again","code":"knowledge_changed"})
    c.status="in_review"; record(db,user,"content_submitted","content",c.id,{"revision_id":rev.id}); db.commit()
    return content_view(c,db)

@app.get("/api/queue")
def queue(user=Depends(require_role("reviewer","admin")),db: Session=Depends(get_db)):
    items=list(db.scalars(scoped(db,Content,user).where(Content.status=="in_review")))
    result=[]
    for c in items:
        rev=revision_for(db,c); run=db.get(ReviewRun,c.latest_run_id) if c.latest_run_id else None
        fs=list(db.scalars(select(Finding).where(Finding.review_run_id==run.id))) if run else []
        data=content_view(c,db); data["findings_summary"]={s:sum(1 for f in fs if f.severity==s) for s in ["critical","high","medium","low","info"]}
        data["risk_decisions"]=[finding_view(f,db) for f in fs if f.status in {"rejected","dismissed"}]; result.append(data)
    return result

def reviewer_decision(content_id,data,user,db,decision):
    c=content_for(db,content_id,user); current=revision_for(db,c)
    if data.revision_id!=current.id:
        raise HTTPException(409,detail={"detail":"The content changed after this revision was reviewed","code":"stale_revision"})
    if c.status!="in_review": raise HTTPException(409,detail={"detail":"Content is not awaiting review","code":"invalid_transition"})
    if decision=='approved':
        run=db.get(ReviewRun,c.latest_run_id) if c.latest_run_id else None
        if not run or run.revision_id!=current.id or run.status!='done' or run.knowledge_hash!=knowledge_fingerprint(c,db):
            raise HTTPException(409,detail={"detail":"Knowledge changed; request changes and recheck before approval","code":"knowledge_changed"})
    approval=Approval(content_id=c.id,revision_id=current.id,body_hash=current.body_hash,reviewer_id=user.id,decision=decision,comment=data.comment)
    db.add(approval); c.status="approved" if decision=="approved" else "changes_requested"
    record(db,user,decision,"content",c.id,{"revision_id":current.id,"body_hash":current.body_hash}); db.commit()
    return {"content":content_view(c,db),"approval":{"id":approval.id,"revision_id":approval.revision_id,"body_hash":approval.body_hash,"decision":approval.decision}}

@app.post("/api/content/{content_id}/approve")
def approve(content_id: str,data: ApprovalIn,user=Depends(require_role("reviewer","admin")),db: Session=Depends(get_db)):
    return reviewer_decision(content_id,data,user,db,"approved")
@app.post("/api/content/{content_id}/request-changes")
def request_changes(content_id: str,data: ApprovalIn,user=Depends(require_role("reviewer","admin")),db: Session=Depends(get_db)):
    return reviewer_decision(content_id,data,user,db,"changes_requested")

@app.get("/api/content/{content_id}/comments")
def get_comments(content_id: str,user=Depends(current_user),db: Session=Depends(get_db)):
    from app.models import Comment
    c=content_for(db,content_id,user)
    return [{"id":x.id,"revision_id":x.revision_id,"finding_id":x.finding_id,"user_id":x.user_id,"body":x.body,"created_at":x.created_at.isoformat()} for x in db.scalars(select(Comment).where(Comment.content_id==c.id))]

@app.post("/api/content/{content_id}/comments")
def add_comment(content_id: str,data: CommentIn,user=Depends(current_user),db: Session=Depends(get_db)):
    from app.models import Comment
    c=content_for(db,content_id,user)
    revision=db.get(Revision,data.revision_id or c.current_revision_id)
    if not revision or revision.content_id!=c.id: not_found()
    if data.finding_id:
        finding=db.get(Finding,data.finding_id)
        if not finding or finding.revision_id!=revision.id: not_found()
    x=Comment(content_id=c.id,revision_id=revision.id,finding_id=data.finding_id,user_id=user.id,body=data.body)
    db.add(x); record(db,user,"comment_added","content",c.id); db.commit(); db.refresh(x)
    return {"id":x.id,"body":x.body,"created_at":x.created_at.isoformat()}

@app.get("/api/audit")
def audit(entity: str | None=None,user=Depends(require_role("admin","reviewer")),db: Session=Depends(get_db)):
    q=scoped(db,AuditEvent,user)
    if entity: q=q.where(AuditEvent.entity_type==entity)
    return [{"id":x.id,"actor_id":x.actor_id,"event_type":x.event_type,"entity_type":x.entity_type,"entity_id":x.entity_id,"payload":x.payload,"created_at":x.created_at.isoformat()} for x in db.scalars(q.order_by(AuditEvent.created_at.desc()).limit(500))]

@app.get("/api/insights")
def insights(user=Depends(require_role("admin")),db: Session=Depends(get_db)):
    contents=list(db.scalars(scoped(db,Content,user))); findings=list(db.scalars(select(Finding).join(ReviewRun,Finding.review_run_id==ReviewRun.id).join(Revision,Finding.revision_id==Revision.id).join(Content,Revision.content_id==Content.id).where(Content.org_id==user.org_id)))
    return {"content_by_status":{s:sum(c.status==s for c in contents) for s in ["draft","checked","in_review","approved","changes_requested"]},"findings_by_category":{k:sum(f.category==k for f in findings) for k in sorted({f.category for f in findings})}}
