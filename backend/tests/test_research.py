from app.research import backtest, anomalies
import pytest

def fixture_bars(n=100):
    return [{'time':f'bar-{i}', 'close':100+i*0.4,'volume':100+i*5} for i in range(n)]

def test_backtest_no_leakage_from_future_bar():
    points=fixture_bars()
    a=backtest(points)
    future=[dict(p) for p in points]
    future[-1]['close']=10000.0
    b=backtest(future)
    # Trades in the *final* period are determined exclusively from prior data.
    assert a['trade_actions']==b['trade_actions']
    assert a['total_return_pct']!=b['total_return_pct']
    assert a['is_forecast'] is False
    with pytest.raises(ValueError):backtest(points,fast=50,slow=20)

def test_anomalies_require_sufficient_data():
    with pytest.raises(ValueError):anomalies(fixture_bars(20))
    result=anomalies(fixture_bars())
    assert result['is_trade_signal'] is False
    assert result['sample_size']==100
