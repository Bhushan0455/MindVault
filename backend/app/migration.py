"""Additive upgrade for the supplied Role A schema. No user rows are deleted.

Run `python -m scripts.migrate_role_a` against an explicitly configured backup
or disposable database before upgrading an existing installation.
"""
from sqlalchemy import inspect, text
from app.db import Base
from app import models  # register tables

ADDITIONS = {
    'content_revisions': {'title':'VARCHAR(255)'},
    'rules': {'requires_claim_evidence':'BOOLEAN NOT NULL DEFAULT FALSE', 'supersedes_id':'VARCHAR(36)'},
    'facts': {'qualifier':"VARCHAR(20) NOT NULL DEFAULT 'exact'", 'source_excerpt':'TEXT', 'supersedes_id':'VARCHAR(36)'},
    'findings': {'snapshot':"JSON NOT NULL DEFAULT '{}'"},
    'review_runs': {'ai_status':"VARCHAR(40) NOT NULL DEFAULT 'not_requested'", 'model':'VARCHAR(120)', 'issues':"JSON NOT NULL DEFAULT '[]'", 'knowledge_hash':'VARCHAR(64)'},
}


def migrate(connection):
    if connection.dialect.name == 'postgresql':
        connection.execute(text('SELECT pg_advisory_xact_lock(734928105)'))
    inspector=inspect(connection)
    before=set(inspector.get_table_names())
    legacy='findings' in before and 'snapshot' not in {c['name'] for c in inspector.get_columns('findings')}
    for table,columns in ADDITIONS.items():
        if table not in before: continue
        present={c['name'] for c in inspector.get_columns(table)}
        for column,definition in columns.items():
            if column not in present:
                connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {definition}'))
    Base.metadata.create_all(connection)
    if legacy:
        # Old rows never stored a trustworthy evidence snapshot. Keep the rows
        # and approvals, but require a fresh review before submitting/applying.
        connection.execute(text("UPDATE review_runs SET status='legacy', issues=:issues"),
                           {'issues':'["Legacy review has no evidence snapshot; create a fresh review."]'})
        connection.execute(text("UPDATE rules SET requires_claim_evidence=TRUE WHERE code='CLAIM-01' AND instruction='Superlative claims require approved evidence.'"))
    if 'content_revisions' in before:
        duplicate=connection.execute(text('SELECT content_id, number FROM content_revisions GROUP BY content_id, number HAVING COUNT(*)>1')).first()
        if duplicate: raise RuntimeError('Duplicate revision numbers require manual resolution before migration')
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_revision_number ON content_revisions(content_id, number)'))
    if connection.dialect.name == 'postgresql' and 'facts' in before:
        connection.execute(text('ALTER TABLE facts ALTER COLUMN value_num TYPE NUMERIC(16,2) USING value_num::numeric(16,2)'))
    if connection.dialect.name == 'postgresql' and 'audit_events' in before:
        connection.execute(text('ALTER TABLE audit_events ALTER COLUMN entity_id TYPE VARCHAR(64)'))


def require_current_schema(engine):
    inspector=inspect(engine)
    for table,columns in ADDITIONS.items():
        present={c['name'] for c in inspector.get_columns(table)}
        if not set(columns)<=present:
            raise RuntimeError('Existing Role A schema needs migration: python -m scripts.migrate_role_a')
