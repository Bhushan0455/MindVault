"""Exercise real AI through a local demo API. Never reads server credentials.

Creates a separate fictional brand, upload, draft and two manually specified
fixture rules plus a price fact. AI candidates/rewrites remain pending; no
content is submitted, approved or published. No mock provider is used here.
"""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlparse
from uuid import uuid4
import httpx


class VerificationError(RuntimeError):
    pass


def local_base(value):
    parsed=urlparse(value)
    if parsed.scheme!='http' or parsed.hostname not in ('localhost','127.0.0.1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise ValueError('Use a loopback HTTP API root, such as http://127.0.0.1:8000')
    return value.rstrip('/')


def run_checks(client,emit=print):
    """Client injection is for offline tests; the CLI always uses real HTTP."""
    def request(method,path,**kwargs):
        response=client.request(method,path,**kwargs)
        if not response.is_success:
            raise VerificationError(f'{method} {path}: HTTP {response.status_code}')
        return response.json()

    health=request('GET','/api/health')
    if not all(health.get(k) is True for k in ('db','demo_mode','ai_configured','semantic_enabled')):
        raise VerificationError('Local demo API must have a connected DB and configured, enabled AI. Restart after updating .env.')
    identities={role:request('POST','/api/auth/demo',params={'role':role}) for role in ('admin','creator')}
    if any(value['user'].get('org_name')!='Demo Org' for value in identities.values()):
        raise VerificationError('This check requires the fictional Demo Org accounts')
    auth={role:{'Authorization':'Bearer '+value['token']} for role,value in identities.items()}
    label='FICTIONAL AI verification '+uuid4().hex[:10]
    brand=request('POST','/api/brands',headers=auth['admin'],json={'name':label})
    lines=['Avoid cheap; use affordable.','Paid ads must include T&C apply.',
        'Veyra Beat 200: price INR 999.','Veyra Beat 200: battery life up to 40 hours.',
        'Veyra Beat 200: warranty 1 year.','Use a formal tone in investor communications.',
        'Use business-friendly wording in technical explanations.']
    doc=request('POST','/api/documents',headers=auth['admin'],data={'brand_id':brand['id'],'kind':'guidelines'},
        files={'file':('fictional_ai_verification.txt','\n'.join(lines).encode('utf-8'),'text/plain')})
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'fixture_brand_id':brand['id'],
        'evidence_source':'real HTTP requests to configured local demo API','checks':{}}

    def poll(path,headers):
        deadline=time.monotonic()+195
        while time.monotonic()<deadline:
            result=request('GET',path,headers=headers)
            if result['status'] in ('done','failed','legacy'): return result
            time.sleep(1)
        raise VerificationError('API job did not reach a terminal state within the polling deadline')

    emit('STAGE 1/3: AI knowledge extraction through document upload and job endpoints...')
    extraction=request('POST',f"/api/documents/{doc['id']}/extract",headers=auth['admin'])
    job=poll('/api/jobs/'+extraction['job_id'],auth['admin'])
    candidates=request('GET',f"/api/documents/{doc['id']}/candidates",headers=auth['admin'])
    result=job.get('result',{})
    passed=job['status']=='done' and result.get('method')=='ai' and bool(candidates) and all(c['status']=='pending' for c in candidates)
    report['checks']['knowledge_extraction']={'verified':passed,'status':job['status'],'method':result.get('method'),
        'pending_candidates':sum(c['status']=='pending' for c in candidates),'job_id':job['id']}
    emit(f"knowledge_extraction: {'VERIFIED' if passed else 'NOT VERIFIED'}; method={result.get('method')}; pending={len(candidates)}")

    # These are manually specified test fixtures, not auto-approval of AI output.
    for code,instruction,line_number,channel in [('INV-AI-01',lines[5],6,'investor_deck'),('CLARITY-AI-01',lines[6],7,'technical_document')]:
        rule=request('POST','/api/rules',headers=auth['admin'],json={'brand_id':brand['id'],'code':code,
            'instruction':instruction,'category':'tone','severity':'medium','scope_channel':[channel],
            'source_document_id':doc['id'],'source_location':f'line {line_number}','source_excerpt':instruction})
        request('POST',f"/api/rules/{rule['id']}/approve",headers=auth['admin'])
    fact=request('POST','/api/facts',headers=auth['admin'],json={'brand_id':brand['id'],'product':'Veyra Beat 200',
        'attribute':'price','value_num':999,'value_text':'₹999','unit':'INR','market':'IN',
        'source_document_id':doc['id'],'source_location':'line 3','source_excerpt':lines[2]})
    request('POST',f"/api/facts/{fact['id']}/approve",headers=auth['admin'])

    emit('STAGE 2/3: AI content review through draft and review-run endpoints...')
    body='Veyra Beat 200 at ₹799 are totally awesome for investors.'
    item=request('POST','/api/content',headers=auth['creator'],json={'brand_id':brand['id'],'title':label,
        'body_text':body,'context':{'product':'Veyra Beat 200','region':'IN','channel':'investor_deck',
            'audience':'investor','content_type':'organic_post','publication_date':date.today().isoformat()}})
    started=request('POST',f"/api/content/{item['id']}/review",headers=auth['creator'])
    review=poll('/api/review-runs/'+started['run_id'],auth['creator'])
    findings=review.get('findings',[])
    retained=[f for f in findings if f['origin']=='ai']
    exact=all(body[f['span_start']:f['span_end']]==f['quoted_text'] and
        (f.get('source') or {}).get('document_id')==doc['id'] for f in retained)
    price=any(f['category']=='price' and f['origin']=='deterministic' and f['suggested_fix']=='₹999' for f in findings)
    passed=review['status']=='done' and review['ai_used'] is True and bool(retained) and exact and price
    report['checks']['content_review']={'verified':passed,'status':review['status'],'ai_used':review.get('ai_used'),
        'ai_status':review.get('ai_status'),'retained_ai_findings':len(retained),'exact_spans_and_sources':exact,
        'deterministic_price_retained':price,'run_id':review['id']}
    emit(f"content_review: {'VERIFIED' if passed else 'NOT VERIFIED'}; ai_used={review.get('ai_used')}; retained AI findings={len(retained)}")

    emit('STAGE 3/3: AI clarity audit through the brand endpoint...')
    clarity=request('POST',f"/api/brands/{brand['id']}/clarity",headers=auth['admin'])
    result=clarity.get('result',{})
    proposals=[f for f in result.get('findings',[]) if f.get('method')=='ai']
    pending=bool(proposals) and all(f['status']=='pending' and (f.get('source') or {}).get('document_id')==doc['id'] for f in proposals)
    passed=result.get('ai_used') is True and pending
    report['checks']['clarity_audit']={'verified':passed,'ai_used':result.get('ai_used'),'ai_status':result.get('ai_status'),
        'retained_ai_proposals':len(proposals),'source_validated_pending_proposals':pending,'job_id':clarity['id']}
    emit(f"clarity_audit: {'VERIFIED' if passed else 'NOT VERIFIED'}; ai_used={result.get('ai_used')}; retained AI proposals={len(proposals)}")
    report['all_services_verified']=all(v['verified'] for v in report['checks'].values())
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',nargs='?',default='http://127.0.0.1:8000')
    parser.add_argument('--report',type=Path,help='Save metadata-only verification JSON; never saves credentials')
    args=parser.parse_args()
    try:
        base=local_base(args.base)
        with httpx.Client(base_url=base,timeout=70,follow_redirects=False) as client:
            report=run_checks(client,emit=lambda message:print(message,flush=True))
        if args.report:
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        print('LIVE API AI: '+('ALL THREE VERIFIED FOR FICTIONAL FIXTURES' if report['all_services_verified'] else 'NOT FULLY VERIFIED'))
        print('AI candidates and rewrites remain pending; no content was approved or published. No key was read by this client.')
        return 0 if report['all_services_verified'] else 1
    except (VerificationError,ValueError) as exc:
        print('API verification stopped: '+str(exc)); return 1
    except httpx.HTTPError:
        print('API verification stopped: local API request failed or timed out. Check that the server is running.'); return 1


if __name__=='__main__': raise SystemExit(main())
