from app import market

def create(client, headers, name='Momentum rules',rules=None):
    r=client.post('/api/v1/strategies',headers=headers,json={'title':name,'summary':'Transparent test research',
        'symbol':'SPY',**(rules or {})})
    assert r.status_code==201,r.text
    return r.json()

def test_health_and_empty_feed(client):
    assert client.get('/health').json()['status']=='ok'
    assert client.get('/ready').status_code==200
    assert client.get('/api/v1/feed').json()['items']==[]
    assert client.get('/api/v1/markets/overview').status_code==503
    assert client.get('/api/v1/markets/anomalies').status_code==503

def test_auth_and_revocation(client,register):
    headers=register('alice')
    assert client.get('/api/v1/auth/me',headers=headers).json()['handle']=='@alice'
    assert client.post('/api/v1/auth/login',json={'email':'alice@example.org','password':'bad'}).status_code==401
    assert client.post('/api/v1/auth/register',json={'email':'alice@example.org','handle':'alice','display_name':'a','password':'very-secure-passphrase!'}).status_code==409
    assert client.post('/api/v1/auth/logout',headers=headers).status_code==200
    assert client.get('/api/v1/auth/me',headers=headers).status_code==401

def test_strategy_comment_bookmark_follow_and_fork(client,register):
    alice=register('alice');bob=register('bob')
    s=create(client,alice)
    assert s['evidence_status']=='untested' and s['metrics'] is None
    assert client.get('/api/v1/feed').json()['items'][0]['id']==s['id']
    assert client.post(f"/api/v1/strategies/{s['id']}/bookmark",headers=bob).json()['bookmarked']
    assert not client.post(f"/api/v1/strategies/{s['id']}/bookmark",headers=bob).json()['bookmarked']
    assert client.post('/api/v1/users/alice/follow',headers=bob).json()['following']
    assert client.post('/api/v1/users/bob/follow',headers=bob).status_code==422
    c=client.post(f"/api/v1/strategies/{s['id']}/comments",headers=bob,json={'body':'Have you considered fees?'})
    assert c.status_code==201
    reply=client.post(f"/api/v1/strategies/{s['id']}/comments",headers=alice,
                      json={'body':'Fees matter','parent_id':c.json()['id']})
    assert reply.status_code==201
    invalid=client.post(f"/api/v1/strategies/{s['id']}/comments",headers=alice,
                        json={'body':'Wrong parent','parent_id':'missing'})
    assert invalid.status_code==422
    fork=client.post(f"/api/v1/strategies/{s['id']}/forks",headers=bob,json={
        'fast_sma':10,'slow_sma':50,'volume_filter':True})
    assert fork.status_code==201
    assert fork.json()['parent_version_id']==s['id']
    assert fork.json()['author']['handle']=='@bob'
    assert client.post(f"/api/v1/strategies/{s['id']}/forks",headers=bob,json={
        'fast_sma':60,'slow_sma':50}).status_code==422
    assert client.delete(f"/api/v1/strategies/{s['id']}",headers=bob).status_code==403
    assert client.delete(f"/api/v1/strategies/{s['id']}",headers=alice).status_code==200
    assert client.get(f"/api/v1/strategies/{s['id']}").status_code==404

def test_social_requires_auth_and_safe_metadata(client,register):
    alice=register('alice')
    s=create(client,alice)
    assert client.post('/api/v1/strategies',json={'title':'x'}).status_code==401
    assert client.post(f"/api/v1/strategies/{s['id']}/like").status_code==401
    assert client.post(f"/api/v1/strategies/{s['id']}/report",headers=alice,json={'reason':'Misleading returns'}).status_code==201
    assert client.get('/api/v1/feed',params={'search':'Momentum'}).json()['items'][0]['id']==s['id']

def test_free_communities_and_isolation(client,register):
    alice=register('alice');bob=register('bob')
    forbidden=client.post('/api/v1/communities',headers=alice,json={
        'name':'private circle','visibility':'private'})
    assert forbidden.status_code==422
    paid=client.post('/api/v1/communities',headers=alice,json={'name':'Paid signal','is_paid':True})
    assert paid.status_code==403
    group=client.post('/api/v1/communities',headers=alice,json={'name':'Open researchers'})
    assert group.status_code==201,group.text
    cid=group.json()['id']
    assert client.post(f'/api/v1/communities/{cid}/join',headers=bob).json()['joined']
    assert len(client.get('/api/v1/communities').json()['items'])==1

def test_paper_ledger_is_user_scoped(client,register):
    alice=register('alice');bob=register('bob')
    assert client.get('/api/v1/portfolio/paper',headers=alice).json()['virtual_cash']==10000
    buy=client.post('/api/v1/portfolio/paper/orders',headers=alice,json={
        'symbol':'SPY','side':'buy','quantity':2,'price':100,'fee':1})
    assert buy.status_code==201,buy.text
    assert client.get('/api/v1/portfolio/paper',headers=alice).json()['virtual_cash']==9799
    assert client.get('/api/v1/portfolio/paper',headers=bob).json()['holdings']=={}
    assert client.post('/api/v1/portfolio/paper/orders',headers=alice,json={
        'symbol':'SPY','side':'sell','quantity':3,'price':100}).status_code==422
    assert client.post('/api/v1/portfolio/paper/orders',headers=alice,json={
        'symbol':'SPY','side':'sell','quantity':1,'price':105}).status_code==201
    assert client.get('/api/v1/portfolio/paper',headers=alice).json()['holdings']['SPY']==1

def test_external_integrations_fail_closed(client,register):
    auth=register('alice')
    assert client.post('/api/v1/assistant/messages',headers=auth,json={'message':'Hi'}).json()['mode']=='local_research'
    assert client.get('/api/v1/markets/history').status_code==503
    assert client.post('/api/v1/backtests',headers=auth,json={'symbol':'SPY'}).status_code==503


def test_account_social_state_is_persistent_and_private(client, register):
    alice=register('alice'); bob=register('bob')
    strategy=create(client,alice)
    url=f"/api/v1/strategies/{strategy['id']}"
    assert client.get('/api/v1/me/activity').status_code==401
    assert client.get('/api/v1/me/strategies').status_code==401
    assert client.post(url+'/bookmark',headers=bob).json()['bookmarked']
    assert client.post(url+'/like',headers=bob).json()['liked']
    assert client.post('/api/v1/users/alice/follow',headers=bob).json()['following']
    state=client.get('/api/v1/me/activity',headers=bob)
    assert state.status_code==200
    assert state.json()['bookmarked_strategy_ids']==[strategy['id']]
    assert state.json()['liked_strategy_ids']==[strategy['id']]
    assert state.json()['following_handles']==['@alice']
    assert client.get('/api/v1/me/activity',headers=alice).json()['bookmarked_strategy_ids']==[]
    assert client.get('/api/v1/me/strategies',headers=alice).json()['items'][0]['id']==strategy['id']
    assert client.get('/api/v1/me/strategies',headers=bob).json()['items']==[]
    assert client.post(url+'/bookmark',headers=bob).json()['bookmarked'] is False
    assert client.get('/api/v1/me/activity',headers=bob).json()['bookmarked_strategy_ids']==[]


def test_local_assistant_only_cites_authorized_or_public_records(client,register):
    alice=register('alice'); bob=register('bob')
    owned=create(client,alice,name='My unique strategy')
    hidden=create(client,alice,name='Secret unpublished thesis')
    assert client.delete(f"/api/v1/strategies/{hidden['id']}",headers=alice).status_code==200
    r=client.post('/api/v1/assistant/messages',headers=bob,json={'message':'What are my strategies?'})
    assert r.status_code==200
    assert r.json()['sources']==[]
    public=client.post('/api/v1/assistant/messages',headers=bob,json={'message':'Show research ideas'})
    assert public.status_code==200
    assert {s['id'] for s in public.json()['sources']}=={owned['id']}
    assert hidden['id'] not in public.text
    author=client.post('/api/v1/assistant/messages',headers=alice,json={'message':'Summarize my research'})
    assert {s['id'] for s in author.json()['sources']}=={owned['id'],hidden['id']}
    assert author.json()['generative_ai'] is False
    assert client.post('/api/v1/assistant/messages',json={'message':'My paper portfolio'}).status_code==401
    assert client.post('/api/v1/assistant/messages',headers=alice,json={'message':'x'}).status_code==422


def test_local_assistant_paper_ledger_isolation(client,register):
    alice=register('alice'); bob=register('bob')
    client.post('/api/v1/portfolio/paper/orders',headers=alice,json={
        'symbol':'SPY','side':'buy','quantity':2,'price':100,'fee':1})
    a=client.post('/api/v1/assistant/messages',headers=alice,json={'message':'Show my paper portfolio'})
    b=client.post('/api/v1/assistant/messages',headers=bob,json={'message':'Show my paper portfolio'})
    assert '2 SPY' in a.json()['answer'] and '$9,799.00' in a.json()['answer']
    assert '2 SPY' not in b.json()['answer'] and '$10,000.00' in b.json()['answer']
    assert b.json()['sources'][0]['id']!=a.json()['sources'][0]['id']
