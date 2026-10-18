"""Yourda.AI integration API. Core social features run locally; vendors fail closed."""
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import (User, Session as LoginSession, Strategy, Comment, Follow, Bookmark, Like,
                     Community, Membership, PaperAccount, PaperTrade, Report)
from .security import hash_password, verify_password, make_session, current_user, token_hash
from .schemas import (Register, Login, StrategyCreate, ForkCreate, CommentCreate,
                      CommunityCreate, PaperOrder, BacktestRequest, AssistantMessage)
from . import market, research

@asynccontextmanager
async def lifespan(app):
    # For local demos only. Use reviewed schema migrations before production.
    if os.getenv('ENVIRONMENT','development') == 'development': Base.metadata.create_all(engine)
    yield

app=FastAPI(title='Yourda.AI API',version='0.14.0',lifespan=lifespan)
# Development-only per-process auth throttle; production requires shared Redis/WAF rate limiting.
_auth_attempts = defaultdict(deque)

origins=[s.strip() for s in os.getenv('CORS_ORIGINS','http://localhost:3000,http://localhost:8080').split(',') if s.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins,
    allow_origin_regex=r'http://localhost:\d+' if os.getenv('ENVIRONMENT','development') == 'development' else None,
    allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Authorization','Content-Type'])

@app.middleware('http')
async def security_headers(request: Request,call_next):
    if request.method == 'POST' and request.url.path in ('/api/v1/auth/login','/api/v1/auth/register'):
        key=(request.client.host if request.client else 'unknown',request.url.path)
        attempts=_auth_attempts[key]
        now=time.monotonic()
        while attempts and now-attempts[0]>60: attempts.popleft()
        if len(attempts)>=12:
            return JSONResponse(status_code=429,content={'detail':'Too many attempts; wait one minute'})
        attempts.append(now)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['Cache-Control']='no-store'
    response.headers['X-Request-ID']=request.headers.get('X-Request-ID',secrets.token_hex(8))[:64]
    return response

@app.get('/health')
def health(): return {'status':'ok','service':'yourda-api'}

@app.get('/ready')
def ready(db: Session=Depends(get_db)):
    db.execute(select(func.count()).select_from(User)).scalar_one()
    return {'status':'ready'}

def identity(user):
    return {'id':user.id,'handle':'@'+user.handle,'display_name':user.display_name}

def serialized(db, s):
    author=db.get(User,s.author_id)
    return {'id':s.id,'author':identity(author),'title':s.title,'summary':s.summary,
        'symbols':[s.symbol],'symbol':s.symbol,'tags':s.tags,'visibility':s.visibility,
        'version_id':s.id,'parent_version_id':s.parent_id,'strategy_rules':s.rules,
        'metrics':None,'evidence_status':s.evidence_status,'created_at':s.created_at.isoformat()+'Z' if s.created_at.tzinfo is None else s.created_at.isoformat()}

def public_strategy(db, id):
    s=db.get(Strategy,id)
    if not s or s.visibility!='public': raise HTTPException(404,'Research not found')
    return s

@app.post('/api/v1/auth/register',status_code=201)
def register(input:Register,db:Session=Depends(get_db)):
    if db.scalar(select(User).where(or_(User.email==input.email,User.handle==input.handle))):
        raise HTTPException(409,'Email or handle already registered')
    user=User(email=input.email,handle=input.handle,display_name=input.display_name,
              password_hash=hash_password(input.password))
    db.add(user);db.commit();db.refresh(user)
    return {'token':make_session(db,user.id),'user':identity(user),
            'email_verified':False,'notice':'Email verification is not configured; release blocked.'}

@app.post('/api/v1/auth/login')
def login(input:Login,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==input.email.strip().lower()))
    if not user or not verify_password(user.password_hash,input.password): raise HTTPException(401,'Invalid credentials')
    return {'token':make_session(db,user.id),'user':identity(user),'email_verified':user.email_verified}

@app.get('/api/v1/auth/me')
def me(user:User=Depends(current_user)):
    return {**identity(user),'email':user.email,'email_verified':user.email_verified}

@app.post('/api/v1/auth/logout')
def logout(request:Request,user:User=Depends(current_user),db:Session=Depends(get_db)):
    db.delete(db.get(LoginSession,token_hash(request.headers['authorization'][7:])))
    db.commit()
    return {'ok':True}

@app.get('/api/v1/me/activity')
def my_activity(user:User=Depends(current_user), db:Session=Depends(get_db)):
    """Current account's persisted social selections. Never expose another user's private graph."""
    followed_ids=db.scalars(select(Follow.followed_id).where(Follow.follower_id==user.id)).all()
    followed_handles=db.scalars(select(User.handle).where(User.id.in_(followed_ids))).all() if followed_ids else []
    own_bookmarks=db.scalars(select(Bookmark.strategy_id).join(Strategy, Bookmark.strategy_id==Strategy.id)
        .where(Bookmark.user_id==user.id, Strategy.visibility=='public')).all()
    own_likes=db.scalars(select(Like.strategy_id).join(Strategy, Like.strategy_id==Strategy.id)
        .where(Like.user_id==user.id, Strategy.visibility=='public')).all()
    member_ids=db.scalars(select(Membership.community_id).where(Membership.user_id==user.id)).all()
    return {'bookmarked_strategy_ids':own_bookmarks,
            'liked_strategy_ids':own_likes,
            'following_handles':['@'+h for h in followed_handles],
            'joined_community_ids':member_ids}

@app.get('/api/v1/me/strategies')
def my_strategies(user:User=Depends(current_user),db:Session=Depends(get_db),limit:int=Query(50,ge=1,le=100)):
    """Display a real profile's authored strategies, including unpublished versions to their owner only."""
    strategies=db.scalars(select(Strategy).where(Strategy.author_id==user.id)
        .order_by(Strategy.created_at.desc()).limit(limit)).all()
    return {'items':[serialized(db,s) for s in strategies]}

@app.get('/api/v1/feed')
def feed(db:Session=Depends(get_db),search:str='',symbol:str='',limit:int=Query(20,ge=1,le=50),offset:int=Query(0,ge=0)):
    q=select(Strategy).where(Strategy.visibility=='public')
    if search: q=q.where(or_(Strategy.title.ilike(f'%{search[:80]}%'),Strategy.summary.ilike(f'%{search[:80]}%')))
    if symbol: q=q.where(Strategy.symbol==symbol.upper())
    items=db.scalars(q.order_by(Strategy.created_at.desc(),Strategy.id.desc()).offset(offset).limit(limit)).all()
    return {'items':[serialized(db,s) for s in items], 'next_offset':offset+len(items) if len(items)==limit else None}

@app.get('/api/v1/strategies')
def list_strategies(db:Session=Depends(get_db),limit:int=Query(20,ge=1,le=50)):
    items=db.scalars(select(Strategy).where(Strategy.visibility=='public').order_by(Strategy.created_at.desc()).limit(limit)).all()
    return {'items':[serialized(db,s) for s in items]}

@app.post('/api/v1/strategies',status_code=201)
def create_strategy(input:StrategyCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if input.fast_sma>=input.slow_sma: raise HTTPException(422,'Fast SMA must be below slow SMA')
    s=Strategy(author_id=user.id,title=input.title,summary=input.summary,symbol=input.symbol,
               tags=input.tags,rules={'fast_sma':input.fast_sma,'slow_sma':input.slow_sma,'volume_filter':input.volume_filter})
    db.add(s);db.commit();db.refresh(s)
    return serialized(db,s)

@app.get('/api/v1/strategies/{strategy_id}')
def strategy_detail(strategy_id:str,db:Session=Depends(get_db)):
    return serialized(db,public_strategy(db,strategy_id))

@app.post('/api/v1/strategies/{strategy_id}/forks',status_code=201)
def fork(strategy_id:str,input:ForkCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    parent=public_strategy(db,strategy_id)
    if input.fast_sma>=input.slow_sma: raise HTTPException(422,'Fast SMA must be below slow SMA')
    item=Strategy(author_id=user.id,parent_id=parent.id,title='Fork: '+parent.title[:125],
        summary=input.note or 'Versioned research fork of '+parent.id,symbol=parent.symbol,tags=parent.tags,
        rules={'fast_sma':input.fast_sma,'slow_sma':input.slow_sma,'volume_filter':input.volume_filter})
    db.add(item);db.commit();db.refresh(item)
    return serialized(db,item)

@app.delete('/api/v1/strategies/{strategy_id}')
def delete_strategy(strategy_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    item=public_strategy(db,strategy_id)
    if item.author_id!=user.id: raise HTTPException(403,'Not the owner')
    # Prevent orphaning published forks or discussions; archive/private instead.
    item.visibility='private';db.commit();return {'ok':True}

@app.get('/api/v1/strategies/{strategy_id}/comments')
def comments(strategy_id:str,db:Session=Depends(get_db)):
    public_strategy(db,strategy_id)
    items=db.scalars(select(Comment).where(Comment.strategy_id==strategy_id).order_by(Comment.created_at).limit(200)).all()
    return {'items':[{'id':c.id,'body':c.body,'parent_id':c.parent_id,'author':identity(db.get(User,c.author_id))} for c in items]}

@app.post('/api/v1/strategies/{strategy_id}/comments',status_code=201)
def comment(strategy_id:str,input:CommentCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    public_strategy(db,strategy_id)
    if input.parent_id:
        parent=db.get(Comment,input.parent_id)
        if not parent or parent.strategy_id!=strategy_id: raise HTTPException(422,'Invalid parent comment')
    obj=Comment(strategy_id=strategy_id,author_id=user.id,parent_id=input.parent_id,body=input.body)
    db.add(obj);db.commit();db.refresh(obj)
    return {'id':obj.id,'body':obj.body,'parent_id':obj.parent_id,'author':identity(user)}

@app.post('/api/v1/strategies/{strategy_id}/bookmark')
def bookmark(strategy_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    public_strategy(db,strategy_id)
    row=db.get(Bookmark,(user.id,strategy_id))
    if row: db.delete(row)
    else: db.add(Bookmark(user_id=user.id,strategy_id=strategy_id))
    db.commit();return {'bookmarked':row is None}

@app.post('/api/v1/strategies/{strategy_id}/like')
def like(strategy_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    public_strategy(db,strategy_id)
    row=db.get(Like,(user.id,strategy_id))
    if row: db.delete(row)
    else: db.add(Like(user_id=user.id,strategy_id=strategy_id))
    db.commit();return {'liked':row is None}

@app.post('/api/v1/users/{handle}/follow')
def follow(handle:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    target=db.scalar(select(User).where(User.handle==handle.lstrip('@').lower()))
    if not target: raise HTTPException(404,'Creator not found')
    if target.id==user.id: raise HTTPException(422,'Cannot follow yourself')
    row=db.get(Follow,(user.id,target.id))
    if row: db.delete(row)
    else: db.add(Follow(follower_id=user.id,followed_id=target.id))
    db.commit();return {'following':row is None}

@app.post('/api/v1/strategies/{strategy_id}/report',status_code=201)
def report(strategy_id:str,request:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    public_strategy(db,strategy_id)
    reason=str(request.get('reason','')).strip()
    if len(reason)<5 or len(reason)>1000: raise HTTPException(422,'Reason must be 5-1000 characters')
    record=Report(author_id=user.id,strategy_id=strategy_id,reason=reason)
    db.add(record);db.commit();return {'id':record.id,'status':'pending_review'}

@app.get('/api/v1/communities')
def communities(db:Session=Depends(get_db)):
    rows=db.scalars(select(Community).where(Community.visibility=='public',Community.is_paid==False).limit(50)).all()
    return {'items':[{'id':c.id,'name':c.name,'description':c.description,'is_paid':c.is_paid} for c in rows]}

@app.post('/api/v1/communities',status_code=201)
def create_community(input:CommunityCreate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if input.is_paid: raise HTTPException(403,'Paid communities disabled until reviewed')
    if input.visibility!='public': raise HTTPException(422,'Private communities not launched yet')
    c=Community(owner_id=user.id,name=input.name,description=input.description,visibility='public',is_paid=False)
    db.add(c);db.flush();db.add(Membership(community_id=c.id,user_id=user.id));db.commit()
    return {'id':c.id,'name':c.name,'description':c.description,'is_paid':False}

@app.post('/api/v1/communities/{community_id}/join')
def join(community_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=db.get(Community,community_id)
    if not c or c.visibility!='public' or c.is_paid: raise HTTPException(404,'Community not available')
    if not db.get(Membership,(c.id,user.id)):
        db.add(Membership(community_id=c.id,user_id=user.id));db.commit()
    return {'joined':True}

@app.get('/api/v1/portfolio/paper')
def paper(user:User=Depends(current_user),db:Session=Depends(get_db)):
    account=db.get(PaperAccount,user.id)
    if not account:
        account=PaperAccount(owner_id=user.id,cash=10000.0)
        db.add(account);db.commit()
    trades=db.scalars(select(PaperTrade).where(PaperTrade.owner_id==user.id).order_by(PaperTrade.created_at)).all()
    quantities={}
    for t in trades: quantities[t.symbol]=round(quantities.get(t.symbol,0)+(t.quantity if t.side=='buy' else -t.quantity),8)
    return {'currency':'USD','virtual_cash':round(account.cash,2),'holdings':quantities,
            'transactions':[{'id':t.id,'symbol':t.symbol,'side':t.side,'quantity':t.quantity,'price':t.price,'fee':t.fee} for t in trades],
            'valuation_status':'unpriced','notice':'Demo paper ledger. User-entered execution prices; no brokerage orders or live holdings valuation.'}

@app.post('/api/v1/portfolio/paper/orders',status_code=201)
def paper_order(input:PaperOrder,user:User=Depends(current_user),db:Session=Depends(get_db)):
    symbol=input.symbol.upper()
    if symbol not in market.SYMBOLS: raise HTTPException(422,'Unsupported symbol')
    if input.side not in ('buy','sell'): raise HTTPException(422,'Side must be buy or sell')
    account=db.get(PaperAccount,user.id)
    if not account:
        account=PaperAccount(owner_id=user.id,cash=10000.0);db.add(account);db.flush()
    history=db.scalars(select(PaperTrade).where(PaperTrade.owner_id==user.id,PaperTrade.symbol==symbol)).all()
    held=sum(t.quantity if t.side=='buy' else -t.quantity for t in history)
    cost=round(input.quantity*input.price,6)
    if input.side=='buy':
        if account.cash+1e-8 < cost+input.fee: raise HTTPException(422,'Insufficient virtual cash')
        account.cash-=cost+input.fee
    else:
        if held+1e-8<input.quantity: raise HTTPException(422,'Insufficient virtual shares')
        account.cash+=cost-input.fee
    t=PaperTrade(owner_id=user.id,symbol=symbol,side=input.side,quantity=input.quantity,price=input.price,fee=input.fee)
    db.add(t);db.commit();return {'id':t.id,'status':'recorded','execution_type':'user_entered_simulated'}

@app.get('/api/v1/markets/overview')
async def overview(): return await market.overview()

@app.get('/api/v1/markets/history')
async def history(symbol:str='SPY',range:str='1M'): return await market.history(symbol,range)

@app.get('/api/v1/markets/{ticker}/bars')
async def bars(ticker:str,range:str='1M'): return await market.history(ticker,range)

@app.get('/api/v1/anomalies')
async def anomalies(symbol:str='SPY',range:str='3M'):
    history=await market.history(symbol,range)
    try: result=research.anomalies(history['points'])
    except ValueError as e: raise HTTPException(422,str(e)) from e
    return {'symbol':history['symbol'],'as_of':history['as_of'],'source':history['source'],**result}

@app.get('/api/v1/markets/anomalies')
async def scanner_contract(symbol: str = 'ALL', lookback: int = Query(20, ge=2, le=252)):
    # Compatibility contract used by the original Flutter anomaly widget.
    symbols = ['SPY','QQQ','AAPL','NVDA'] if symbol == 'ALL' else [symbol.upper()]
    signals = []
    latest = []
    adequate = 0
    for ticker in symbols:
        h = await market.history(ticker, '3M')
        latest.append(h['as_of'])
        try:
            values = research.anomalies(h['points'],lookback)
        except ValueError:
            continue
        adequate += 1
        z = values['volume_z_score']
        ratio = values['volatility_ratio']
        if z is not None and z >= 2:
            signals.append({'id':f'{ticker}-volume-{h["as_of"]}','symbol':ticker,
                'signal_type':'volume_spike','severity':'high' if z >= 3 else 'watch',
                'title':'Unusual volume','explanation':f'Volume z-score {z} vs prior {lookback} bars; not a trade recommendation.',
                'observed':z,'unit':'z_score','threshold':2.0,'as_of':h['as_of']})
        if ratio is not None and ratio >= 1.5:
            signals.append({'id':f'{ticker}-volatility-{h["as_of"]}','symbol':ticker,
                'signal_type':'volatility_spike','severity':'watch',
                'title':'Elevated realized volatility',
                'explanation':f'{lookback}-bar volatility ratio {ratio} vs preceding {lookback} bars; no return prediction.',
                'observed':ratio,'unit':'ratio','threshold':1.5,'as_of':h['as_of']})
    return {'source':'alpaca_iex','status':'ready' if adequate else 'insufficient_history',
            'as_of':max(latest),'lookback_sessions':lookback,'benchmark':'SPY',
            'market_session':'unknown',
            'methodology':f'Previous {lookback}-bar sample standardization; volume and log-return volatility',
            'signals':signals}

@app.post('/api/v1/backtests')
async def run_backtest(input:BacktestRequest,user:User=Depends(current_user)):
    # Server computes from real backend observations only; no fake benchmarks or promises.
    h=await market.history(input.symbol,input.range)
    try: result=research.backtest(h['points'],input.fast_sma,input.slow_sma,input.fee_bps,input.slippage_bps)
    except ValueError as e: raise HTTPException(422,str(e)) from e
    return {'owner_id':user.id,'symbol':h['symbol'],'source':h['source'],'as_of':h['as_of'],
            'evidence_status':'platform_backtested',**result}

@app.post('/api/v1/assistant/messages')
def assistant_message(input:AssistantMessage,user:User=Depends(current_user),db:Session=Depends(get_db)):
    '''Auditable, deterministic research queries. Not a connected generative model.

    Every answer derives from data this account owns or from public research;
    no external model is told about private posts, membership data, or credentials.
    '''
    text=input.message.strip().lower()
    sources=[]
    if any(term in text for term in ('portfolio','paper','cash','holdings','trades','balance')):
        account=db.get(PaperAccount,user.id)
        trades=db.scalars(select(PaperTrade).where(PaperTrade.owner_id==user.id)).all()
        cash=round(account.cash,2) if account else 10000.0
        holdings={}
        for t in trades:
            holdings[t.symbol]=round(holdings.get(t.symbol,0)+(t.quantity if t.side=='buy' else -t.quantity),6)
        holdings={symbol:qty for symbol,qty in holdings.items() if qty>1e-9}
        holdings_text=', '.join(f'{qty:g} {symbol}' for symbol,qty in sorted(holdings.items())) or 'none recorded'
        answer=(f'Your simulated paper ledger has ${cash:,.2f} in virtual cash and these recorded holdings: {holdings_text}. '
            'These transactions use user-entered prices, not executed brokerage orders or verified live valuations.')
        sources.append({'type':'paper_ledger','id':user.id,'label':'Your paper portfolio'})
    elif any(term in text for term in ('my strategies','my posts','i published','my research','my forks')):
        rows=db.scalars(select(Strategy).where(Strategy.author_id==user.id)
            .order_by(Strategy.created_at.desc()).limit(5)).all()
        if not rows:
            answer='You have no published research or private drafts yet. Open Discover to share your first research idea.'
        else:
            description='; '.join(f'{s.title} ({s.symbol}, {s.visibility}, {s.evidence_status})' for s in rows)
            answer=(f'Your {len(rows)} most recent research version(s): {description}. '
                'A saved strategy version is not evidence of profitable or predictive performance.')
            sources=[{'type':'strategy','id':s.id,'label':s.title} for s in rows]
    elif any(term in text for term in ('strategies','strategy','ideas','research','moving average','sma')):
        rows=db.scalars(select(Strategy).where(Strategy.visibility=='public')
            .order_by(Strategy.created_at.desc()).limit(5)).all()
        if not rows:
            answer='There are no public strategy posts yet. Ask another question or publish a research idea first.'
        else:
            description='; '.join(f'{s.title} ({s.symbol}, fast SMA {s.rules.get("fast_sma", "—")}, slow SMA {s.rules.get("slow_sma", "—")})' for s in rows)
            answer=(f'Here are the latest {len(rows)} public research ideas: {description}. '
                'They are user-authored, unverified ideas and not investment recommendations.')
            sources=[{'type':'strategy','id':s.id,'label':s.title} for s in rows]
    elif any(term in text for term in ('price','market','stock','live','quote','etf')):
        answer=('For current market prices use Markets, where the data provider and timestamp are identified. '
            'This assistant does not make up live quotes or price forecasts. Provider credentials may still be required.')
    else:
        answer=('I can summarize your own research versions, public strategy ideas, and your simulated paper portfolio. '
            'Ask “What are my strategies?”, “Describe public strategies”, or “Show my paper portfolio”. '
            'This is a deterministic local research assistant, not yet a generative AI model.')
    return {'answer':answer,'sources':sources,'mode':'local_research','generative_ai':False,
            'disclaimer':'Educational research only. No investment advice, trading signals, or live execution.'}

@app.get('/api/v1/config/features')
def features():
    return {'social':True,'communities_free':True,'paper_portfolio':True,
            'market_data':bool(os.getenv('ALPACA_API_KEY') and os.getenv('ALPACA_API_SECRET')),
            'ai':False,'assistant_local':True,'paid_communities':False,'email_verification':False}
