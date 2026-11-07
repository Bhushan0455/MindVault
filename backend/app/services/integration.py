"""Database boundary for Role B's unchanged, independently tested services."""
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from hashlib import sha256
from sqlalchemy import select
from app import models as m
from app.services import contracts as c
from app.services.ai_review import run_review, GeminiContentGenerator
from app.core.config import settings
import json
from app.services.ai_audit import save_ai_events


def source_for(row, db):
    doc = db.get(m.Document, row.source_document_id) if row.source_document_id else None
    if doc and (doc.org_id!=row.org_id or doc.brand_id!=row.brand_id):
        raise ValueError('Source document scope does not match knowledge')
    return c.Source(row.source_document_id or f"manual:{row.id}",
        doc.title if doc else ('Source document unavailable' if row.source_document_id else "Manually entered knowledge"),
        row.source_location or "manual entry",
        row.source_excerpt or (row.instruction if isinstance(row, m.Rule) else row.value_text))


def rule_contract(row, db):
    return c.Rule(id=row.id, org_id=row.org_id, brand_id=row.brand_id, code=row.code,
        version=row.version, instruction=row.instruction, source=source_for(row, db),
        status=row.status, authority=row.authority, priority=row.priority,
        scope=c.RuleScope(**{k: tuple(getattr(row, 'scope_' + k) or ())
                            for k in ('channel','audience','region','content_type','campaign')}),
        effective_from=row.effective_from, effective_to=row.effective_to,
        category=row.category, severity=row.severity, forbidden_terms=tuple(row.forbidden_terms or ()),
        preferred_terms=tuple((row.preferred_terms or {}).items()), required_text=row.required_text,
        requires_claim_evidence=row.requires_claim_evidence)


def fact_contracts(rows, db, catalog):
    products={row.id:c.Product(row.id,row.org_id,row.brand_id,row.name,tuple(row.aliases)) for row in catalog}
    names={name.casefold().strip():row for row in catalog for name in [row.name,*row.aliases]}
    numeric, claims = [], []
    for row in rows:
        product=names.get(row.product.casefold().strip())
        key=product.id if product else sha256(f'{row.org_id}:{row.brand_id}:{row.product.casefold().strip()}'.encode()).hexdigest()
        if key not in products: products[key] = c.Product(key, row.org_id, row.brand_id, row.product)
        common = dict(id=row.id, org_id=row.org_id, brand_id=row.brand_id, version=row.version,
            market=row.market, source=source_for(row, db), status=row.status,
            valid_from=row.valid_from, valid_to=row.valid_to)
        if row.attribute == 'claim':
            claims.append(c.ClaimEvidence(product=product.name if product else row.product, claim_text=row.value_text, **common))
        else:
            numeric.append(c.NumericFact(product_id=key, attribute=row.attribute,
                value=Decimal(str(row.value_num)), unit=row.unit, qualifier=row.qualifier, **common))
    return list(products.values()), numeric, claims


def review_revision(rev, item, db):
    rules = list(db.scalars(select(m.Rule).where(m.Rule.org_id == item.org_id, m.Rule.brand_id == item.brand_id)))
    facts = list(db.scalars(select(m.Fact).where(m.Fact.org_id == item.org_id, m.Fact.brand_id == item.brand_id)))
    catalog = list(db.scalars(select(m.ProductCatalog).where(m.ProductCatalog.org_id==item.org_id,m.ProductCatalog.brand_id==item.brand_id)))
    products, numeric, claims = fact_contracts(facts, db, catalog)
    ctx = dict(rev.context)
    ctx.pop('language',None)  # Persisted UI metadata; not a rule scope dimension.
    ctx['market'] = ctx.pop('region', ctx.pop('market', ''))
    ctx['publication_date'] = date.fromisoformat(ctx['publication_date'])
    generator = GeminiContentGenerator(org_id=item.org_id, brand_id=item.brand_id) if settings.enable_semantic else None
    result = run_review(rev.body_text, context=c.ReviewContext(**ctx), products=products,
        rules=[rule_contract(r, db) for r in rules], numeric_facts=numeric, claim_evidence=claims,
        org_id=item.org_id, brand_id=item.brand_id, generator=generator, explicit_tone=True)
    save_ai_events(db,generator,org_id=item.org_id,actor_id=item.created_by,entity_type='revision',entity_id=rev.id)
    return result, fingerprint_rows(rules, facts, catalog)


def fingerprint_rows(rules, facts, catalog):
    rows=[[{column.name:getattr(row,column.name) for column in row.__table__.columns}
           for row in sorted(group,key=lambda r:r.id)] for group in (rules,facts,catalog)]
    return sha256(json.dumps(rows,sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()


def knowledge_fingerprint(item,db):
    # Serialize the gate with knowledge creation/approval; all mutation routes
    # take this same brand lock before changing knowledge.
    db.scalar(select(m.Brand).where(m.Brand.id==item.brand_id,m.Brand.org_id==item.org_id).with_for_update())
    groups=[list(db.scalars(select(model).where(model.org_id==item.org_id,model.brand_id==item.brand_id)))
            for model in (m.Rule,m.Fact,m.ProductCatalog)]
    return fingerprint_rows(*groups)


def stored_finding(row):
    data = dict(row.snapshot)
    data.pop('_api',None)
    if data.get('source'): data['source'] = c.Source(**data['source'])
    return c.Finding(**data)


def evidence_snapshot(finding,db):
    rule=db.get(m.Rule,finding.rule_id) if finding.rule_id else None
    fact=db.get(m.Fact,finding.fact_id) if finding.fact_id else None
    source=finding.source
    doc=db.get(m.Document,source.document_id) if source else None
    page=None
    if doc and doc.filename.lower().endswith('.pdf') and source.location.startswith('page '):
        try: page=int(source.location[5:])
        except ValueError: pass
    return {'rule':{'id':rule.id,'code':rule.code,'version':rule.version,'instruction':rule.instruction} if rule else None,
        'fact':{'id':fact.id,'version':fact.version,'value':fact.value_text,
            'source_document':source.document_title if source else None,
            'location':source.location if source else None,'page':page} if fact else None}


def json_data(value):
    import json
    return json.loads(json.dumps(asdict(value), default=str, ensure_ascii=False))
