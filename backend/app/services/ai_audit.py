"""Persist adapter metadata only; never provider payloads or exception text."""
from app.models import AuditEvent


def save_ai_events(db,generator,*,org_id,actor_id,entity_type,entity_id):
    for event in getattr(generator,'events',[]) if generator else []:
        payload={k:event[k] for k in ('purpose','model','redacted','attempt','success','error_code','failure_kind') if k in event}
        db.add(AuditEvent(org_id=org_id,actor_id=actor_id,event_type='ai_call',entity_type=entity_type,
            entity_id=entity_id,payload=payload))
