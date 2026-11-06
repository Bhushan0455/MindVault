from datetime import date
from hashlib import sha256
from sqlalchemy import select
from app.models import Organisation, User, Brand, Rule, Fact, Document, ProductCatalog
from app.core.security import hash_password


def seed(db):
    org = db.scalar(select(Organisation).where(Organisation.name == "Demo Org"))
    if org is None:
        org = Organisation(name="Demo Org"); db.add(org); db.flush()
        brand = Brand(org_id=org.id, name="Veyra Audio"); db.add(brand); db.flush()
        db.add(ProductCatalog(org_id=org.id,brand_id=brand.id,name='Veyra Beat 200',aliases=['Beat 200']))
        for role, name in [("admin", "Demo Admin"), ("creator", "Demo Creator"), ("reviewer", "Demo Reviewer")]:
            db.add(User(org_id=org.id, email=f"{role}@demo", name=name, role=role, password_hash=hash_password("demo")))
        db.flush()
        admin = db.scalar(select(User).where(User.email == 'admin@demo'))
        rule_data = [
            ("CLAIM-01", "Superlative claims require approved evidence.", "claims", "high", "non_overridable", [], {}, None),
            ("CLAIM-02", "Prices must match the approved price for product and market.", "claims", "critical", "non_overridable", [], {}, None),
            ("TERM-01", "Do not use cheap; prefer affordable.", "terminology", "medium", "core", ["cheap"], {"cheap": "affordable"}, None),
            ("DISC-01", "Paid ads must include T&C apply.", "disclaimer", "high", "core", [], {}, "T&C apply"),
            ("TONE-IG-02", "Use a conversational tone and no more than two emojis.", "tone", "low", "scoped", [], {}, None),
            ("TONE-INV-03", "Use a formal tone and no exclamation marks.", "tone", "medium", "scoped", [], {}, None),
        ]
        fact_lines = [
            'Veyra Beat 200: price INR 999. India retail price, valid from 1 October 2026.',
            'Veyra Beat 200: historical price INR 899. India, 1 January to 30 September 2026.',
            'Veyra Beat 200: battery life 40 hours.',
            'Veyra Beat 200: warranty 1 year.']
        def make_document(title, filename, kind, lines):
            body='\n'.join(lines); raw=body.encode('utf-8')
            row=Document(org_id=org.id,brand_id=brand.id,title=title,filename=filename,kind=kind,
                file_bytes=raw,text=body,content_hash=sha256(raw).hexdigest(),uploaded_by=admin.id)
            db.add(row); db.flush(); return row
        guidelines=make_document('Fictional Veyra Brand Guidelines','fictional_veyra_guidelines.txt','guidelines',[r[1] for r in rule_data])
        facts_doc=make_document('Fictional Veyra Product Facts','fictional_veyra_facts.txt','facts',fact_lines)
        for index,(code, text, category, sev, authority, forbidden, preferred, required) in enumerate(rule_data):
            scopes = {"TONE-IG-02": {"scope_channel": ["instagram"], "scope_audience": ["consumer"]},
                      "DISC-01": {"scope_content_type": ["paid_ad"]},
                      "TONE-INV-03": {"scope_channel": ["investor_deck"]}}.get(code, {})
            db.add(Rule(org_id=org.id, brand_id=brand.id, code=code, instruction=text, category=category,
                        severity=sev, authority=authority, forbidden_terms=forbidden, preferred_terms=preferred,
                        required_text=required, status="approved", source_location=f"line {index+1}", source_excerpt=text,
                        source_document_id=guidelines.id, approved_by=admin.id, requires_claim_evidence=(code=="CLAIM-01"), **scopes))
        db.add_all([
            Fact(org_id=org.id, brand_id=brand.id, product="Veyra Beat 200", attribute="price", value_text="₹999", value_num=999, unit="INR", market="IN", valid_from=date(2026,10,1), status="approved", source_document_id=facts_doc.id, source_location="line 1", source_excerpt=fact_lines[0]),
            Fact(org_id=org.id, brand_id=brand.id, product="Veyra Beat 200", attribute="price", value_text="₹899", value_num=899, unit="INR", market="IN", valid_from=date(2026,1,1), valid_to=date(2026,9,30), status="expired", source_document_id=facts_doc.id, source_location="line 2", source_excerpt=fact_lines[1]),
            Fact(org_id=org.id, brand_id=brand.id, product="Veyra Beat 200", attribute="battery_life", value_text="40 hours", value_num=40, unit="hours", market="IN", status="approved", source_document_id=facts_doc.id, source_location="line 3", source_excerpt=fact_lines[2]),
            Fact(org_id=org.id, brand_id=brand.id, product="Veyra Beat 200", attribute="warranty", value_text="1 year", value_num=1, unit="years", market="IN", status="approved", source_document_id=facts_doc.id, source_location="line 4", source_excerpt=fact_lines[3]),
        ])
        db.commit()
    # Existing knowledge is never rewritten by application startup.
