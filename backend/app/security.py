"""Argon2id credential hashing and revocable opaque access tokens."""
import hashlib, secrets
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from sqlalchemy.orm import Session as DBSession
from fastapi import Header, Depends, HTTPException
from .db import get_db
from .models import User, Session

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)

def hash_password(password): return hasher.hash(password)

def verify_password(digest, password):
    try: return hasher.verify(digest, password)
    except (VerifyMismatchError, VerificationError): return False

def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()

def make_session(db: DBSession, user_id: str):
    token = secrets.token_urlsafe(40)
    db.add(Session(token_hash=token_hash(token), user_id=user_id,
                   expires_at=datetime.now(timezone.utc) + timedelta(hours=12)))
    db.commit()
    return token

def current_user(authorization: str | None = Header(default=None), db: DBSession = Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Sign in required')
    value = authorization[7:]
    if len(value) > 180: raise HTTPException(401, 'Invalid session')
    session = db.get(Session, token_hash(value))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(401, 'Session expired')
    user = db.get(User, session.user_id)
    if not user: raise HTTPException(401, 'Invalid session')
    return user
