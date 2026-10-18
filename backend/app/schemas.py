from pydantic import BaseModel, Field, field_validator
import re

class Register(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    handle: str = Field(min_length=3, max_length=24)
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=128)
    @field_validator('email')
    @classmethod
    def valid_email(cls, v):
        v=v.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v): raise ValueError('Invalid email')
        return v
    @field_validator('handle')
    @classmethod
    def valid_handle(cls,v):
        v=v.strip().lower().lstrip('@')
        if not re.fullmatch('[a-z0-9_]{3,24}',v): raise ValueError('Use 3-24 letters, digits, underscores')
        return v

class Login(BaseModel):
    email: str
    password: str

class StrategyCreate(BaseModel):
    title: str = Field(min_length=3,max_length=140)
    summary: str = Field(min_length=4,max_length=5000)
    symbol: str = Field(default='SPY',min_length=1,max_length=12)
    tags: list[str] = Field(default_factory=list,max_length=8)
    fast_sma: int = Field(default=20,ge=2,le=190)
    slow_sma: int = Field(default=50,ge=3,le=200)
    volume_filter: bool = False
    @field_validator('symbol')
    @classmethod
    def symbol_valid(cls,v):
        v=v.upper()
        if not re.fullmatch('[A-Z.]{1,12}',v): raise ValueError('Invalid ticker')
        return v

class ForkCreate(BaseModel):
    fast_sma: int = Field(ge=2,le=190)
    slow_sma: int = Field(ge=3,le=200)
    volume_filter: bool = False
    note: str = Field(default='',max_length=500)

class CommentCreate(BaseModel):
    body: str = Field(min_length=1,max_length=1500)
    parent_id: str | None = None

class CommunityCreate(BaseModel):
    name: str = Field(min_length=3,max_length=100)
    description: str = Field(default='',max_length=2000)
    visibility: str = 'public'
    is_paid: bool = False

class PaperOrder(BaseModel):
    symbol: str = Field(min_length=1,max_length=12)
    side: str
    quantity: float = Field(gt=0,le=1e6)
    price: float = Field(gt=0,le=1e8)
    fee: float = Field(default=0,ge=0,le=1e4)

class BacktestRequest(BaseModel):
    symbol: str = 'SPY'
    range: str = '1Y'
    fast_sma: int = Field(default=20,ge=2,le=190)
    slow_sma: int = Field(default=50,ge=3,le=200)
    fee_bps: float = Field(default=5.0,ge=0,le=500)
    slippage_bps: float = Field(default=5.0,ge=0,le=500)


class AssistantMessage(BaseModel):
    message: str = Field(min_length=2,max_length=500)
