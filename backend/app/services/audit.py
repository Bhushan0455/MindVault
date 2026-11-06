from app.models import AuditEvent

def record(db, user, event_type, entity_type, entity_id, payload=None):
    db.add(AuditEvent(org_id=user.org_id if user else "system", actor_id=user.id if user else None,
                      event_type=event_type, entity_type=entity_type, entity_id=entity_id, payload=payload or {}))
