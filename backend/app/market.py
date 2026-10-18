"""Alpaca IEX adapter: no fallback quotes, no invented prices."""
import os
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import httpx
from fastapi import HTTPException

SYMBOLS = ('SPY','QQQ','DIA','IWM','VOO','AAPL','MSFT','NVDA','XLK','XLF','XLE','SMH','XBI')
NAMES = {'SPY':'SPDR S&P 500 ETF Trust','QQQ':'Invesco QQQ Trust','DIA':'SPDR Dow Jones Industrial Average ETF',
         'IWM':'iShares Russell 2000 ETF','VOO':'Vanguard S&P 500 ETF'}


def _key_headers():
    key=os.getenv('ALPACA_API_KEY',''); secret=os.getenv('ALPACA_API_SECRET','')
    if not key or not secret: raise HTTPException(503,'Market data not configured; connect a licensed provider')
    return {'APCA-API-KEY-ID':key, 'APCA-API-SECRET-KEY':secret}

async def _get(path, params):
    headers=_key_headers()
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response=await client.get('https://data.alpaca.markets'+path,
                                      params={**params,'feed':'iex'},headers=headers)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503,'Live market provider is unavailable') from None


def _iso(value):
    if isinstance(value,str): return value
    return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

async def overview():
    data=await _get('/v2/stocks/snapshots', {'symbols':','.join(SYMBOLS)})
    snapshots=data.get('snapshots',{})
    results=[]
    timestamps=[]
    now=datetime.now(timezone.utc)
    for symbol, snap in snapshots.items():
        if symbol not in SYMBOLS: continue
        trade=snap.get('latestTrade') or {}
        previous=snap.get('prevDailyBar') or {}
        price=trade.get('p'); prior=previous.get('c'); stamp=trade.get('t')
        if not price or not prior or not stamp or price<=0 or prior<=0: continue
        try: t=datetime.fromisoformat(stamp.replace('Z','+00:00'))
        except ValueError: continue
        timestamps.append(t)
        results.append({'symbol':symbol,'name':NAMES.get(symbol,symbol),
                        'asset_type':'stock' if symbol in ('AAPL','MSFT','NVDA') else 'etf',
                        'price':price,'previous_close':prior,'currency':'USD','as_of':_iso(stamp),
                        'sparkline':[]})
    if not results: raise HTTPException(503,'No current provider observations available')
    last=max(timestamps)
    age=(now-last).total_seconds()
    # IEX trade timestamps alone cannot prove the market session. Be conservative.
    status='live_iex' if age<=240 else 'end_of_day'
    return {'source':'alpaca_iex','status':status,'market_session':'unknown',
            'delayed_minutes':0,'as_of':_iso(last),'instruments':results}

async def history(symbol, range_name):
    symbol=symbol.upper()
    if symbol not in SYMBOLS: raise HTTPException(422,'Unsupported symbol')
    window={'1D':1,'1W':7,'1M':31,'3M':93,'1Y':366}.get(range_name)
    if not window: raise HTTPException(422,'Range must be 1D, 1W, 1M, 3M, 1Y')
    end=datetime.now(timezone.utc)
    start=end-timedelta(days=window)
    timeframe='1Min' if range_name=='1D' else '1Day'
    data=await _get(f'/v2/stocks/{symbol}/bars',{
        'start':_iso(start),'end':_iso(end),'timeframe':timeframe,
        'adjustment':'raw','limit':1000,'sort':'asc'})
    bars=data.get('bars') or []
    points=[{'time':b['t'],'close':b['c'],'volume':b['v']} for b in bars
            if b.get('c',0)>0 and b.get('v',-1)>=0 and b.get('t')]
    if not points: raise HTTPException(503,'No actual historical bars available')
    return {'symbol':symbol,'source':'alpaca_iex','as_of':points[-1]['time'],
            'adjustment':'raw','timeframe':timeframe,'points':points}
