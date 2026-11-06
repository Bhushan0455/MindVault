"""Offline regression coverage for the reusable live API verifier."""
from unittest.mock import patch
import pytest
from app.core.config import settings
from app.services.knowledge_extract import _offline
from scripts.ai_api_smoke import run_checks, local_base


class Adapter:
    model='test-model'
    events=()
    def __init__(self,callback,**scope):
        self.callback=callback
        self.org_id,self.brand_id=scope['org_id'],scope['brand_id']
    def __call__(self,payload): return self.callback(payload)


def clarity_response(payload):
    rule=next(r for r in payload['data']['rules'] if 'business-friendly' in r['instruction'])
    return {'clarity_findings':[{'rule_id':rule['rule_id'],'rule_version':rule['rule_version'],
        'rule_snapshot_hash':rule['rule_snapshot_hash'],'kind':'undefined_term','excerpt':'business-friendly',
        'why_it_matters':'Reviewers need an operational definition for the intended audience.',
        'suggested_rewrite':'Explain technical terms in plain language and add an example approved for business readers.',
        'example_good':'An approved plain-language explanation.','example_bad':'Unexplained specialist jargon.',
        'confidence':0.9}]}


def content_response(payload):
    return {'findings':[{'category':'tone','quoted_text':'totally awesome','rule_code':'INV-AI-01','fact_id':None,
        'verdict':'violation','severity':'medium','confidence':0.9,'explanation':'Informal wording conflicts with the supplied formal tone rule.',
        'suggested_fix':'suitable for everyday listening'}]}


@pytest.mark.parametrize('content_fails',[False,True])
def test_api_verifier_reports_actual_service_outcomes_without_credentials(client,content_fails):
    def fail(payload): raise RuntimeError('fictional provider unavailable')
    with patch.object(settings,'enable_semantic',True),patch.object(settings,'gemini_api_key','fake-private-key'),patch.object(settings,'gemini_model','test-model'), \
         patch('app.routers.knowledge.GeminiKnowledgeGenerator',side_effect=lambda **kw:Adapter(_offline,**kw)), \
         patch('app.services.integration.GeminiContentGenerator',side_effect=lambda **kw:Adapter(fail if content_fails else content_response,**kw)), \
         patch('app.routers.knowledge.GeminiClarityGenerator',side_effect=lambda **kw:Adapter(clarity_response,**kw)):
        report=run_checks(client,emit=lambda message:None)
    assert report['checks']['knowledge_extraction']['verified']
    assert report['checks']['clarity_audit']['verified']
    assert report['checks']['content_review']['verified'] is (not content_fails)
    assert report['all_services_verified'] is (not content_fails)
    assert 'fake-private-key' not in str(report) and 'Bearer' not in str(report)
    health=client.get('/api/health').json()
    assert 'live_ai_verified' not in health and health['ai_verification_scope']=='per_service_result'


def test_live_api_verifier_requires_loopback_without_embedded_credentials():
    assert local_base('http://127.0.0.1:8000/')=='http://127.0.0.1:8000'
    for bad in ['https://example.com','http://key@localhost:8000','http://localhost:8000/?key=value']:
        with pytest.raises(ValueError): local_base(bad)
