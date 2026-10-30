import copy
import hashlib
import json
import os
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from ninja import content, db, youtube as yt, youtube_auth as auth
from ninja.config import artifact

VIDEO = 'abcdefghijk'
SESSION = 'https://www.googleapis.com/upload/youtube/v3/videos?upload_id=test-session'


@pytest.fixture
def vault(monkeypatch):
    values = {}
    def memory(name, value=None, delete=False):
        if delete:
            values.pop(name, None)
        elif value is not None:
            values[name] = copy.deepcopy(value)
        return copy.deepcopy(values.get(name))
    monkeypatch.setattr(auth, 'vault', memory)
    memory('client', {'client_id': 'test.apps.googleusercontent.com', 'client_secret': 'fixture'})
    memory('tokens', {'access_token': 'fixture', 'refresh_token': 'refresh', 'expires': time.time()+3600,
        'scope': ' '.join(auth.SCOPES.values()), 'channel': {'id': 'channel1', 'title': 'Test channel'}})
    return values


@pytest.fixture
def upload_plan(vault, monkeypatch):
    p = {'id': 'p', 'name': 'fixture', 'source': 'source.mp4', 'edl': {'revision': 1, 'captions': []}}
    with db.connect() as c:
        c.execute('INSERT INTO projects VALUES(?,?,?,?)', ('p','fixture',db.encode(p),time.time()))
        c.execute('INSERT INTO jobs(id,project,kind,payload,state,result,created) VALUES(?,?,?,?,?,?,?)',
            ('render','p','render','{}','completed',db.encode({'revision':1,'file':'final.mp4','preview':False}),time.time()))
    path = artifact('p', 'final.mp4');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'video-fixture')
    body = content.create('p')
    content.scenes(body['id'],0,[],'owned')
    content.edit_draft(body['id'],content.Draft(platform='youtube',account='channel1',title='Test video',copy='Test description',media='final.mp4'))
    content.review(body['id'],'youtube',1)
    monkeypatch.setattr(yt.media,'probe',lambda p:{'audio':True,'duration':3})
    job = db.queue(body['id'],'youtube_prepare',{})
    return yt.prepare(body['id'],job,{'made_for_kids':False,'synthetic_media':False})


def video(status=None):
    return {'id': VIDEO, 'snippet': {'channelId':'channel1','title':'Test video'},
            'status': status or {'privacyStatus':'private','selfDeclaredMadeForKids':False},
            'statistics': {'viewCount':'3'}}


def mock_remote(monkeypatch, data=None):
    monkeypatch.setattr(auth,'api',lambda *a,**k:{'items':[data or video()]})


def test_oauth_pkce_state_single_use(vault,monkeypatch):
    result=auth.begin(manage=True,analytics=True)
    query=parse_qs(urlsplit(result['url']).query)
    assert query['code_challenge_method']==['S256']
    assert query['redirect_uri']==[auth.REDIRECT]
    flow=copy.deepcopy(vault['flow'])
    with pytest.raises(ValueError,match='invalid sign-in'):auth.callback('wrong','code')
    assert vault['flow']==flow
    def request(method,url,**kwargs):
        if method=='POST':
            assert kwargs['data']['code_verifier']==flow['verifier']
            return httpx.Response(200,json={'access_token':'new','refresh_token':'newrefresh','scope':' '.join(auth.SCOPES.values())})
        return httpx.Response(200,json={'items':[{'id':'channel1','snippet':{'title':'Test channel'}}]})
    monkeypatch.setattr(auth,'request',request)
    assert auth.callback(flow['state'],'code')['connected']
    with pytest.raises(ValueError):auth.callback(flow['state'],'code')


def test_expired_oauth_and_missing_scope(vault,monkeypatch):
    auth.begin();vault['flow']['expires']=0
    with pytest.raises(ValueError):auth.callback(vault['flow']['state'],'code')
    auth.begin()
    monkeypatch.setattr(auth,'request',lambda *a,**k:httpx.Response(200,json={'access_token':'a','refresh_token':'r','scope':auth.SCOPES['read']}))
    with pytest.raises(ValueError,match='permissions'):auth.callback(vault['flow']['state'],'code')


@pytest.mark.skipif(os.name!='nt',reason='Windows credential protection')
def test_windows_dpapi_roundtrip():
    raw=b'nonsecret test fixture'
    encrypted=auth._crypt(raw)
    assert raw not in encrypted
    assert auth._crypt(encrypted,True)==raw


def test_exact_approval_and_dedup(upload_plan):
    op=upload_plan
    assert op['params']['metadata']['status']['privacyStatus']=='private'
    first=yt.approve(op['id'])
    with pytest.raises(ValueError):yt.approve(op['id'])
    assert first['job']
    repeat=yt.prepare(op['params']['snapshot']['package'],first['job'],{'made_for_kids':False,'synthetic_media':False})
    assert repeat['id']==op['id']


def test_changed_parameters_and_media_rejected(upload_plan):
    op=upload_plan;op['params']['metadata']['snippet']['title']='Tampered';yt.save(op)
    with pytest.raises(ValueError,match='approval'):yt.approve(op['id'])
    artifact('p','final.mp4').write_bytes(b'changed-file!')
    with pytest.raises(ValueError,match='media changed'):yt.validate(op['params'])


def test_source_change_invalidates_upload(upload_plan):
    p=db.project('p');p['edl']['revision']=2;db.save_project('p',p)
    with pytest.raises(ValueError):yt.approve(upload_plan['id'])


def test_interrupted_upload_resumes_existing_session(upload_plan,vault,monkeypatch):
    op=upload_plan;job=yt.approve(op['id'])['job'];calls=[]
    def request(method,url,**kwargs):
        calls.append((method,url,kwargs))
        if method=='POST':return httpx.Response(200,headers={'Location':SESSION})
        raise ValueError('connection interrupted')
    monkeypatch.setattr(auth,'request',request)
    with pytest.raises(ValueError):yt.execute(op['id'],job)
    assert vault['session-'+op['id']]['url']==SESSION
    assert yt.get(op['id'])['state']=='paused'
    mock_remote(monkeypatch)
    def recover(method,url,**kwargs):
        calls.append((method,url,kwargs))
        assert method=='PUT'
        if kwargs['headers']['Content-Range'].startswith('bytes */'):
            return httpx.Response(308,headers={'Range':'bytes=0-3'})
        assert kwargs['content']==b'video-fixture'[4:]
        return httpx.Response(201,json={'id':VIDEO})
    monkeypatch.setattr(auth,'request',recover)
    result=yt.execute(op['id'],job)
    assert result['state']=='private' and result['remote_id']==VIDEO
    assert sum(method=='POST' for method,_,_ in calls)==1
    # Retry after a successful remote write must only verify identity, never upload again.
    assert yt.execute(op['id'],job)['remote_id']==VIDEO
    assert sum(method=='POST' for method,_,_ in calls)==1


def test_ambiguous_initiation_never_restarts(upload_plan,monkeypatch):
    job=yt.approve(upload_plan['id'])['job'];calls=[]
    def failure(*args,**kwargs):calls.append(args);raise ValueError('interrupted')
    monkeypatch.setattr(auth,'request',failure)
    with pytest.raises(ValueError):yt.execute(upload_plan['id'],job)
    with pytest.raises(ValueError,match='duplicate upload'):yt.execute(upload_plan['id'],job)
    assert len(calls)==1
    assert yt.get(upload_plan['id'])['state']=='reconciliation_required'


def test_expired_session_and_missing_remote_id(upload_plan,vault,monkeypatch):
    job=yt.approve(upload_plan['id'])['job']
    vault['session-'+upload_plan['id']]={'url':SESSION}
    monkeypatch.setattr(auth,'request',lambda *a,**k:httpx.Response(404))
    with pytest.raises(ValueError,match='expired'):yt.execute(upload_plan['id'],job)
    assert yt.get(upload_plan['id'])['state']=='reconciliation_required'
    monkeypatch.setattr(auth,'request',lambda *a,**k:httpx.Response(200,json={}))
    with pytest.raises(ValueError,match='video ID'):yt.execute(upload_plan['id'],job)
    assert yt.get(upload_plan['id'])['remote_id'] is None


@pytest.mark.parametrize('url',['https://evil.example/upload/youtube/v3/videos','http://www.googleapis.com/upload/youtube/v3/videos','https://www.googleapis.com/other','https://user@www.googleapis.com/upload/youtube/v3/videos'])
def test_session_destination_allowlist(url):
    with pytest.raises(ValueError):yt.session_url(url)


def test_manual_reconcile_requires_channel_and_title(upload_plan,monkeypatch):
    op=upload_plan;op['state']='reconciliation_required';yt.save(op)
    wrong=video();wrong['snippet']['channelId']='other';mock_remote(monkeypatch,wrong)
    with pytest.raises(ValueError,match='another channel'):yt.reconcile(op['id'],VIDEO)
    wrong=video();wrong['snippet']['title']='different';mock_remote(monkeypatch,wrong)
    with pytest.raises(ValueError,match='title'):yt.reconcile(op['id'],VIDEO)
    mock_remote(monkeypatch)
    assert yt.reconcile(op['id'],VIDEO)['state']=='private'


def test_schedule_preserves_status_and_requires_separate_approval(upload_plan,monkeypatch):
    op=upload_plan;op.update(remote_id=VIDEO,state='private');yt.save(op)
    current=video({'privacyStatus':'private','embeddable':False,'selfDeclaredMadeForKids':False})
    calls=[]
    def api(method,resource,*args,**kwargs):
        calls.append(method)
        if method=='PUT':current['status']=kwargs['json']['status'];return current
        return {'items':[copy.deepcopy(current)]}
    monkeypatch.setattr(auth,'api',api)
    planned=yt.prepare_status(op['id'],'private','2099-01-01T18:00:00+05:30')
    assert planned['params']['desired']['publishAt']=='2099-01-01T12:30:00Z'
    assert planned['params']['desired']['embeddable'] is False
    assert 'PUT' not in calls
    job=yt.approve(planned['id'])['job']
    assert yt.execute(planned['id'],job)['state']=='confirmed'
    assert yt.get(op['id'])['state']=='scheduled'
    assert calls.count('PUT')==1
    yt.execute(planned['id'],job)
    assert calls.count('PUT')==1
    # Cancellation must remain possible even after local content has changed.
    p=db.project('p');p['edl']['revision']+=1;db.save_project('p',p)
    cancel=yt.prepare_status(op['id'],'private',None)
    yt.execute(cancel['id'],yt.approve(cancel['id'])['job'])
    assert 'publishAt' not in current['status']
    assert yt.get(op['id'])['state']=='private'


def test_stale_remote_status_blocks_publication(upload_plan,monkeypatch):
    op=upload_plan;op.update(remote_id=VIDEO,state='private');yt.save(op)
    mock_remote(monkeypatch)
    plan=yt.prepare_status(op['id'],'public',None)
    job=yt.approve(plan['id'])['job']
    mock_remote(monkeypatch,video({'privacyStatus':'unlisted'}))
    with pytest.raises(ValueError,match='status changed'):yt.execute(plan['id'],job)


def test_analytics_does_not_invent_missing_reports(upload_plan,vault,monkeypatch):
    op=upload_plan;op['remote_id']=VIDEO;yt.save(op)
    vault['tokens']['scope']=auth.SCOPES['read']
    mock_remote(monkeypatch)
    result=yt.analytics(op['id'],'2026-01-01','2026-02-01')
    assert result['statistics']=={'viewCount':'3'}
    assert result['analytics'] is None
    assert 'not connected' in result['availability']


def test_scene_repair_preserves_other_scenes(upload_plan,monkeypatch):
    package=content.load(upload_plan['params']['snapshot']['package'])
    package=content.scenes(package['id'],package['revision'],[{'id':'one','script':'old','rights':'owned'}, {'id':'two','script':'keep','rights':'owned'}],'owned')
    candidate={'title':'Test','description':'Test','scenes':[{'script':'new','source':'provided note'}]}
    monkeypatch.setattr(yt.adapters,'complete',lambda *a:{'text':json.dumps(candidate),'provider':'ollama','usage':{}})
    job=db.queue(package['id'],'youtube_generate',{})
    proposal=yt.generate(package['id'],job,{'scene':'one','brief':'repair'})
    assert content.load(package['id'])['scenes'][0]['script']=='old'
    applied=yt.apply_draft(proposal['id'])
    assert applied['scenes'][0]['script']=='new'
    assert applied['scenes'][0]['status']=='needs_rebuild'
    assert applied['scenes'][1]==package['scenes'][1]
    with pytest.raises(ValueError):yt.apply_draft(proposal['id'])


def test_routes_require_token_and_avoid_oauth_echo(vault):
    from ninja.api import app
    client=TestClient(app)
    assert client.get('/api/youtube').status_code==401
    assert client.get('/api/youtube',headers={'X-Ninja-Token':'test-token'}).status_code==200
    result=client.get('/oauth/youtube/callback?state=wrong&code=NEVER_ECHO')
    assert 'NEVER_ECHO' not in result.text
    assert result.headers['referrer-policy']=='no-referrer'

def test_cancelled_studio_origin_blocks_publication_status(upload_plan,monkeypatch):
    from ninja import studio,media
    mock_remote(monkeypatch)
    op=upload_plan; op['remote_id']=VIDEO;op['state']='private';yt.save(op)
    status=yt.prepare_status(op['id'],'public',None)
    upload_job=yt.approve(status['id'])['job']
    saved=studio.save(studio.Definition(mode='finished',rights='owned').model_dump())
    with db.connect() as c:
        run=studio.enqueue(c,saved,True,'cancelled-publication-origin')
        c.execute('INSERT INTO studio_uploads(channel,workflow,sha,override,run,operation,project) VALUES(?,?,?,?,?,?,?)',('channel1',saved['id'],'sha','',run['id'],op['id'],'p'))
        c.execute('UPDATE jobs SET cancel=1 WHERE id=?',(run['job'],))
    def forbidden(*a,**kw):raise AssertionError('Cancelled origin must never change remote status')
    monkeypatch.setattr(yt,'change_status',forbidden)
    with pytest.raises(media.Cancelled):yt.execute(status['id'],upload_job)
