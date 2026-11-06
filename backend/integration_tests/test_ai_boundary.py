"""Transport boundary fakes verify integration; these are never live AI claims."""
import json
from unittest.mock import patch
from app.core.config import settings
from app.services.ai_review import REVIEW_SCHEMA
from app.services.knowledge_extract import RESPONSE_SCHEMA, _offline
from app.services.ai_clarity import SCHEMA
from app.services.llm import knowledge_provider_schema
from test_workflows import new_content, review, upload


class Provider:
    model='test-model'
    def __init__(self,response):
        self.response=response; self.calls=[]
        self.events=[{'purpose':'content_review','model':'test-model','attempt':1,'success':True,'redacted':True,
                     'api_key':'do-not-persist-this','draft':'do-not-persist-this'}]
    def __call__(self,payload):
        self.calls.append(payload)
        return self.response(payload) if callable(self.response) else self.response


def test_validated_ai_content_saved_with_exact_evidence_and_private_data_redacted(client,auth,brand):
    item=new_content(client,auth,brand,'🎧 Veyra Beat 200 at ₹799 are totally awesome. Contact person@example.com.',
        context={'product':'Veyra Beat 200','channel':'investor_deck','region':'IN','content_type':'organic_post'})
    provider=Provider({'findings':[{'category':'tone','quoted_text':'totally awesome','rule_code':'TONE-INV-03','fact_id':None,
        'verdict':'violation','severity':'medium','confidence':0.9,'explanation':'Informal wording conflicts with the supplied rule.',
        'suggested_fix':'suitable for everyday listening'}]})
    with patch.object(settings,'enable_semantic',True),patch('app.services.integration.GeminiContentGenerator',return_value=provider):
        result=review(client,auth,item)
    assert result['ai_used'] and result['ai_status']=='completed'
    ai=next(f for f in result['findings'] if f['origin']=='ai')
    body=item['current_revision']['body_text']
    assert body[ai['span_start']:ai['span_end']]=='totally awesome'
    assert ai['rule']['code']=='TONE-INV-03' and ai['source']['location']=='line 6'
    assert 'person@example.com' not in json.dumps(provider.calls)
    audit=client.get('/api/audit',headers=auth['admin']).json()
    ai_events=[a for a in audit if a['event_type']=='ai_call']
    assert len(ai_events)==1
    assert 'do-not-persist-this' not in json.dumps(ai_events)


def test_ai_knowledge_extraction_saves_pending_candidates(client,auth,brand):
    doc=upload(client,auth,brand)
    provider=Provider(_offline)
    with patch.object(settings,'enable_semantic',True),patch('app.routers.knowledge.GeminiKnowledgeGenerator',return_value=provider):
        extraction=client.post('/api/documents/'+doc['id']+'/extract',headers=auth['admin']).json()
    job=client.get('/api/jobs/'+extraction['job_id'],headers=auth['admin']).json()
    assert job['result']['method']=='ai' and job['status']=='done'
    candidates=client.get('/api/documents/'+doc['id']+'/candidates',headers=auth['admin']).json()
    assert len(candidates)==2 and all(c['status']=='pending' for c in candidates)


def test_ai_clarity_status_and_fallback_persisted(client,auth,brand):
    provider=Provider({'clarity_findings':[]})
    with patch.object(settings,'enable_semantic',True),patch('app.routers.knowledge.GeminiClarityGenerator',return_value=provider):
        result=client.post('/api/brands/'+brand+'/clarity',headers=auth['admin']).json()['result']
    assert result['ai_used'] and result['ai_status']=='completed'
    def unavailable(payload): raise RuntimeError('secret-like-provider-detail')
    with patch.object(settings,'enable_semantic',True),patch('app.routers.knowledge.GeminiClarityGenerator',return_value=Provider(unavailable)):
        response=client.post('/api/brands/'+brand+'/clarity',headers=auth['admin'])
    assert response.status_code==200 and not response.json()['result']['ai_used']
    assert response.json()['result']['ai_status']=='unavailable' and 'secret-like' not in response.text


def test_installed_google_sdk_accepts_all_service_config_shapes_without_network():
    from google.genai import types
    for schema in [REVIEW_SCHEMA,RESPONSE_SCHEMA,knowledge_provider_schema(),SCHEMA]:
        config=types.GenerateContentConfig.model_validate({'http_options':{'timeout':30000,'retry_options':{'attempts':1}},
            'response_json_schema':schema,'response_mime_type':'application/json','max_output_tokens':6000,'temperature':0})
        assert config.http_options.timeout==30000
