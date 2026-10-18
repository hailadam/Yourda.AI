"""SQLAlchemy persistence. DATABASE_URL=sqlite:///... is local-only; use PostgreSQL for deployment."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass


def build_engine(url=None):
    url = url or os.getenv('DATABASE_URL', 'sqlite:///./yourda_dev.db')
    args = {'check_same_thread': False} if url.startswith('sqlite:') else {}
    return create_engine(url, connect_args=args, pool_pre_ping=True)

engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db():
    with SessionLocal() as session:
        yield session
