import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.main import app, _auth_attempts

@pytest.fixture
def client(tmp_path):
    _auth_attempts.clear()
    engine=create_engine(f'sqlite:///{tmp_path}/unit.sqlite', connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    maker=sessionmaker(bind=engine, expire_on_commit=False)
    def get_test_db():
        with maker() as s: yield s
    app.dependency_overrides[get_db]=get_test_db
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.fixture
def register(client):
    def make(n):
        payload={'email':f'{n}@example.org','handle':n,'display_name':n.title(),'password':'very-secure-passphrase!'}
        response=client.post('/api/v1/auth/register',json=payload)
        assert response.status_code==201,response.text
        return {'Authorization':'Bearer '+response.json()['token']}
    return make
