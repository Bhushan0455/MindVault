"""Always create a disposable local database; never use a developer's DATABASE_URL."""
import os
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

path = Path(__file__).resolve().parents[1] / ('.test-' + uuid4().hex + '.sqlite')
postgres = os.getenv('MINDVAULT_TEST_POSTGRES_DSN')
schema = 'mv_test_' + uuid4().hex
admin_engine = None
database_url = 'sqlite:///' + path.as_posix()
if postgres:
    admin_engine = create_engine(postgres)
    with admin_engine.begin() as connection: connection.execute(text(f'CREATE SCHEMA {schema}'))
    database_url = make_url(postgres).update_query_dict({'options':'-csearch_path='+schema}).render_as_string(hide_password=False)
os.environ.update(DATABASE_URL=database_url, JWT_SECRET='isolated-integration-test-secret-32-bytes',
                  DEMO_MODE='true', ENABLE_SEMANTIC='false')
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, SessionLocal
from app.models import Organisation, User, Brand
from app.core.security import issue_token
from app.services.seed import seed


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db: seed(db)
    yield


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c: yield c


@pytest.fixture
def auth(client):
    return {role: {'Authorization':'Bearer '+client.post('/api/auth/demo',params={'role':role}).json()['token']}
            for role in ['admin','creator','reviewer']}


@pytest.fixture
def brand(client,auth):
    return client.get('/api/brands',headers=auth['admin']).json()[0]['id']


@pytest.fixture
def other_users():
    with SessionLocal() as db:
        org=Organisation(name='Other org'); db.add(org); db.flush()
        foreign=User(org_id=org.id,email='foreign@test',name='Other admin',role='admin',password_hash='unused')
        local_org=db.query(Organisation).filter_by(name='Demo Org').one()
        sibling=User(org_id=local_org.id,email='sibling@test',name='Other creator',role='creator',password_hash='unused')
        db.add_all([foreign,sibling]); db.flush()
        headers=[{'Authorization':'Bearer '+issue_token(u)} for u in [foreign,sibling]]
        db.commit(); return headers


def pytest_sessionfinish(session,exitstatus):
    engine.dispose()
    if admin_engine:
        with admin_engine.begin() as connection: connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin_engine.dispose()
    path.unlink(missing_ok=True)
