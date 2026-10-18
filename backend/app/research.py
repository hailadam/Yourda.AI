"""Deterministic, fee-aware SMA backtest. Uses previous-bar signals; no lookahead.

Limitations: raw/unadjusted data, simple long-only, no financing/dividends, no order book.
"""
import math
from statistics import mean, pstdev

def backtest(points, fast=20, slow=50, fees_bps=5.0, slippage_bps=5.0):
    if fast>=slow or fast<2 or len(points)<slow+5:
        raise ValueError('Need fast < slow and at least slow + 5 historical bars')
    closes=[float(p['close']) for p in points]
    if any(not math.isfinite(c) or c<=0 for c in closes): raise ValueError('Bad prices')
    equity=1.0
    peak=1.0
    drawdown=0.0
    position=0
    fees=(fees_bps+slippage_bps)/10000
    curve=[]
    trades=0
    wins=0
    last_entry=None
    for i in range(slow,len(closes)):
        # previous bar (i-1) is known before the holding period (i-1 -> i).
        fast_ma=mean(closes[i-fast:i]); slow_ma=mean(closes[i-slow:i])
        desired=int(fast_ma>slow_ma)
        if desired!=position:
            equity*=1-fees
            trades+=1
            if not desired and last_entry is not None:
                wins+=int(closes[i-1]>last_entry)
                last_entry=None
            if desired: last_entry=closes[i-1]
            position=desired
        equity*= 1+position*(closes[i]/closes[i-1]-1)
        peak=max(peak,equity)
        drawdown=min(drawdown,equity/peak-1)
        curve.append({'time':points[i]['time'],'equity':round(equity,8)})
    total_return=equity-1
    return {'total_return_pct':round(100*total_return,4),
            'max_drawdown_pct':round(100*drawdown,4),
            'trade_actions':trades,'closed_winning_trades':wins,
            'equity_curve':curve,'fee_bps':fees_bps,'slippage_bps':slippage_bps,
            'methodology':'Long/cash SMA crossover; previous completed bar; raw closes; costs charged on position changes',
            'limitations':['Corporate actions are not adjusted','Dividends not included','Illustrative fills at closing prices','No out-of-sample validation'],
            'is_forecast':False}

def anomalies(points, lookback=20):
    if lookback < 2 or lookback > 252 or len(points) < 2*lookback+2:
        raise ValueError('Insufficient completed bars for the requested lookback')
    vols=[float(p['volume']) for p in points]
    closes=[float(p['close']) for p in points]
    base=vols[-lookback-1:-1]
    sigma=pstdev(base)
    volume_z=(vols[-1]-mean(base))/sigma if sigma>0 else None
    returns=[math.log(closes[i]/closes[i-1]) for i in range(1,len(closes))]
    old=returns[-2*lookback-1:-lookback-1]
    recent=returns[-lookback:]
    basevol=pstdev(old); recentvol=pstdev(recent)
    return {'volume_z_score':round(volume_z,3) if volume_z is not None else None,
            'volatility_ratio':round(recentvol/basevol,3) if basevol>0 else None,
            'sample_size':len(points),'methodology':f'Volume vs prior {lookback}-bar population std; realized log-return volatility ratio latest {lookback} vs preceding {lookback}',
            'is_trade_signal':False}
