from datetime import datetime,timezone,timedelta
from app import market
from app.main import app
from fastapi.testclient import TestClient

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def test_real_provider_adapter_with_offline_contract_fixture(client,monkeypatch):
    async def fake_get(path,params):
        if path.endswith('snapshots'):
            return {'snapshots':{'SPY':{'latestTrade':{'p':123.4,'t':now()},'prevDailyBar':{'c':120.0}}}}
        return {'bars':[{'t':(datetime.now(timezone.utc)-timedelta(days=2-i)).isoformat(),
                         'c':100+i,'v':1000+i} for i in range(3)]}
    monkeypatch.setattr(market,'_get',fake_get)
    overview=client.get('/api/v1/markets/overview')
    assert overview.status_code==200
    result=overview.json()
    assert result['source']=='alpaca_iex'
    assert result['instruments'][0]['price']==123.4
    assert result['instruments'][0]['sparkline']==[]  # never invent a chart
    history=client.get('/api/v1/markets/history',params={'symbol':'SPY','range':'1M'})
    assert history.status_code==200
    assert len(history.json()['points'])==3
    assert history.json()['adjustment']=='raw'
    assert client.get('/api/v1/markets/history',params={'symbol':'BADINVALID','range':'1M'}).status_code==422
    assert client.get('/api/v1/markets/anomalies',params={'symbol':'SPY'}).json()['status']=='insufficient_history'
