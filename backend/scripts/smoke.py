"""Run the fictional demo API journey: python scripts/smoke.py http://localhost:8000"""
import sys, time
import httpx as requests
from urllib.parse import urlparse

base = sys.argv[1].rstrip("/")
if urlparse(base).hostname not in {'localhost','127.0.0.1'}:
    raise SystemExit('Run this fictional demo smoke test against a local disposable database only.')
def check(ok, message):
    if not ok: raise SystemExit("FAIL: " + message)
health=requests.get(base+'/api/health',timeout=10).json()
check(health.get('demo_mode') is True,'demo mode required')
login = requests.post(base+"/api/auth/demo?role=creator", timeout=30); check(login.is_success, "creator demo login")
token=login.json()["token"]; h={"Authorization":"Bearer "+token}
brands=requests.get(base+"/api/brands",headers=h,timeout=20); check(brands.is_success and brands.json(),"brand list")
brand=brands.json()[0]["id"]
body="Veyra Beat 200 headphones now at just ₹799! Best headphones in India. 🎧🎧🎧"
created=requests.post(base+"/api/content",headers=h,json={"brand_id":brand,"title":"Demo price check","body_text":body,"context":{"product":"Veyra Beat 200","channel":"instagram","audience":"consumer","region":"IN","content_type":"paid_ad","publication_date":"2026-11-05"}},timeout=20)
check(created.is_success,"create content: "+created.text); cid=created.json()["id"]
started=requests.post(f"{base}/api/content/{cid}/review",headers=h,timeout=20); check(started.status_code==202,"start review")
rid=started.json()["run_id"]
for _ in range(60):
    run=requests.get(f"{base}/api/review-runs/{rid}",headers=h,timeout=20).json()
    if run["status"] in ("done","failed"): break
    time.sleep(1)
check(run["status"]=="done","review completed")
check(any(f["verdict"] in ("violation","outdated") and "999" in str(f.get("fact")) for f in run["findings"]),"price evidence cites ₹999")
check(any(f["verdict"]=="unsupported" for f in run["findings"]),"unsupported superlative")
price=next(f for f in run['findings'] if f.get('fact') and f['category']=='price')
source=requests.get(base+'/api/sources/'+price['source']['document_id'],params={'location':price['source']['location']},headers=h,timeout=20)
check(source.is_success,'stored source lookup')
for f in run['findings']:
    if f['verdict']=='supported': continue
    decision={'action':'accept'} if f['suggested_fix'] is not None else {'action':'reject','note':'Fictional smoke test: explicit risk acknowledgement for reviewer assessment.'}
    check(requests.post(base+'/api/findings/'+f['id']+'/decision',json=decision,headers=h,timeout=20).is_success,'finding decision')
fixed=requests.post(f'{base}/api/content/{cid}/apply-fixes',headers=h,timeout=20)
check(fixed.is_success,'apply fixes')
newrun=fixed.json()['run_id']
for _ in range(60):
    result=requests.get(base+'/api/review-runs/'+newrun,headers=h,timeout=20).json()
    if result['status'] in ('done','failed'): break
    time.sleep(1)
check(result['status']=='done','new revision rechecked')
for f in result['findings']:
    if f['verdict']!='supported':
        check(requests.post(base+'/api/findings/'+f['id']+'/decision',headers=h,
            json={'action':'reject','note':'Fictional smoke test: reviewer must assess this acknowledged risk.'},timeout=20).is_success,'new revision risk decision')
check(requests.post(f'{base}/api/content/{cid}/submit',headers=h,timeout=20).is_success,'submit')
reviewer=requests.post(base+'/api/auth/demo?role=reviewer',timeout=20).json()
rh={'Authorization':'Bearer '+reviewer['token']}
queue=requests.get(base+'/api/queue',headers=rh,timeout=20).json()
check(any(item['id']==cid for item in queue),'reviewer queue')
revision=fixed.json()['content']['current_revision']
approved=requests.post(f'{base}/api/content/{cid}/approve',headers=rh,
    json={'revision_id':revision['id'],'comment':'Fictional smoke approval with visible risk acknowledgements.'},timeout=20)
check(approved.is_success and approved.json()['approval']['body_hash']==revision['body_hash'],'approval binds exact hash')
print('Smoke passed: actual HTTP login, review, stored source, decisions, safe fixes, recheck, queue and exact-revision approval.')
