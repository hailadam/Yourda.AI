"""Core database entities. All user-owned operations are scoped by owner_id."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Text, Boolean, Integer, Float, ForeignKey, UniqueConstraint, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    handle: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Session(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Strategy(Base):
    __tablename__ = 'strategies'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey('strategies.id'), nullable=True)
    title: Mapped[str] = mapped_column(String(140))
    summary: Mapped[str] = mapped_column(Text)
    symbol: Mapped[str] = mapped_column(String(12))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    visibility: Mapped[str] = mapped_column(String(16), default='public')
    evidence_status: Mapped[str] = mapped_column(String(24), default='untested')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Comment(Base):
    __tablename__ = 'comments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    strategy_id: Mapped[str] = mapped_column(ForeignKey('strategies.id'), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey('comments.id'), nullable=True)
    body: Mapped[str] = mapped_column(String(1500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Follow(Base):
    __tablename__ = 'follows'
    follower_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    followed_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)

class Bookmark(Base):
    __tablename__ = 'bookmarks'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(ForeignKey('strategies.id'), primary_key=True)

class Like(Base):
    __tablename__ = 'likes'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(ForeignKey('strategies.id'), primary_key=True)

class Community(Base):
    __tablename__ = 'communities'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(2000), default='')
    visibility: Mapped[str] = mapped_column(String(20), default='public')
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)

class Membership(Base):
    __tablename__ = 'memberships'
    community_id: Mapped[str] = mapped_column(ForeignKey('communities.id'), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)

class PaperAccount(Base):
    __tablename__ = 'paper_accounts'
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    cash: Mapped[float] = mapped_column(Float, default=10000.0)

class PaperTrade(Base):
    __tablename__ = 'paper_trades'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    symbol: Mapped[str] = mapped_column(String(12))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    strategy_id: Mapped[str] = mapped_column(ForeignKey('strategies.id'))
    reason: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
