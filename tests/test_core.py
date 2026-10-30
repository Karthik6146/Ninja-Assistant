import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from ninja import db, media, workflow, adapters
from ninja.api import app
from ninja.config import approved_path, artifact
from ninja.schemas import Caption, EDL

def test_path_traversal_and_symlink(tmp_path):
    root=tmp_path/'allowed'; root.mkdir(); inside=root/'video.mp4'; inside.write_text('media')
    outside=tmp_path/'secret'; outside.write_text('secret')
    assert approved_path(str(inside),[root])==inside
    with pytest.raises(ValueError): approved_path(str(root/'..'/'secret'),[root])
    link=root/'escape'
    try: link.symlink_to(outside)
    except OSError: return # Windows symlinks require developer mode.
    with pytest.raises(ValueError): approved_path(str(link),[root])

def test_artifact_escape():
    with pytest.raises(ValueError): artifact('safe','../../access-token')
    with pytest.raises(ValueError): artifact('../../','access-token')

def test_exact_single_use_approval():
    params={'account':'channel-1','file':'abc.mp4','privacy':'private'}
    id=db.request_approval('upload',params)
    with pytest.raises(ValueError): db.consume_approval(id,'upload',params)
    with db.connect() as c: c.execute("UPDATE approvals SET state='approved' WHERE id=?",(id,))
    with pytest.raises(ValueError): db.consume_approval(id,'upload',params|{'privacy':'public'})
    db.consume_approval(id,'upload',params)
    with pytest.raises(ValueError): db.consume_approval(id,'upload',params)

def test_job_recovery_bounded_and_cancelled():
    id=db.queue('p','render',{}); assert db.claim()['id']==id
    db.update_job(id,heartbeat=time.time()-100)
    assert db.claim()['id']==id
    db.update_job(id,heartbeat=time.time()-100)
    assert db.claim()['id']==id
    db.update_job(id,heartbeat=time.time()-100)
    assert db.claim() is None
    with db.connect() as c: assert c.execute('SELECT state FROM jobs WHERE id=?',(id,)).fetchone()[0]=='failed'
    id=db.queue('p','probe',{}); db.claim(); db.update_job(id,cancel=1,heartbeat=time.time()-100)
    assert db.claim() is None
    with db.connect() as c: assert c.execute('SELECT state FROM jobs WHERE id=?',(id,)).fetchone()[0]=='cancelled'

def test_remap_caption_bounds_and_clip_order():
    captions=[{'start':1,'end':4,'text':'hello','words':[{'start':2,'end':3,'word':'hello'}]}]
    result=media.remap(captions,[{'start':2.5,'end':5},{'start':0,'end':2}])
    assert result[0]['start']==0 and result[0]['end']==1.5
    assert result[0]['words'][0]['end']==.5
    assert result[1]['start']==3.5 and result[1]['end']==4.5
    assert media.stamp(59.9996)=='00:01:00,000'
    assert media.caption_export(result,'vtt').startswith('WEBVTT')

def test_invalid_timings():
    with pytest.raises(ValueError): Caption(start=2,end=1,text='bad')
    with pytest.raises(ValueError): Caption(start=0,end=1,text='bad',words=[{'start':0,'end':2,'word':'bad'}])
    with pytest.raises(ValueError): EDL(clips=[{'start':0,'end':0}])

def test_persistent_graph_review():
    result=workflow.begin('p',2); assert result['stage']=='waiting_review'
    with pytest.raises(ValueError): workflow.resume('p',1)
    result=workflow.resume('p',2); assert result['reviewed_revision']==2

def test_private_dns_and_rebinding_guard(monkeypatch):
    monkeypatch.setattr(adapters.socket,'getaddrinfo',lambda *a,**kw:[(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError): adapters.public_addresses('https://example.org')
    for url in ('file:///etc/passwd','http://example.org','https://user:pass@example.org','https://example.org:8000'):
        with pytest.raises(ValueError): adapters.public_addresses(url)

def test_origin_token_emergency():
    with TestClient(app) as client:
        assert client.get('/api/projects').status_code==401
        assert client.post('/api/session',json={'token':'test-token'},headers={'Origin':'https://evil.example'}).status_code==403
        assert client.post('/api/session',json={'token':'test-token'}).status_code==200
        assert client.post('/api/emergency',json={'stopped':True}).status_code==403
        headers={'X-Ninja-Token':'test-token'}
        assert client.post('/api/emergency',json={'stopped':True},headers=headers).status_code==200
        assert client.post('/api/import/path',json={'path':'anything'},headers=headers).status_code==409
        with pytest.raises(ValueError): db.queue('p','render',{})
        assert client.post('/api/emergency',json={'stopped':False},headers=headers).status_code==200

def test_final_requires_matching_review_and_preview():
    with TestClient(app) as client:
        with db.connect() as c: c.execute('INSERT INTO projects VALUES(?,?,?,?)',('p','test',db.encode({'edl':{'revision':2,'clips':[{'start':0,'end':1}]}}),time.time()))
        headers={'X-Ninja-Token':'test-token'}
        response=client.post('/api/projects/p/render',json={'preview':False,'revision':2},headers=headers)
        assert response.status_code==400 and 'Review' in response.json()['detail']
        p=db.project('p'); p['reviewed_revision']=2; db.save_project('p',p)
        response=client.post('/api/projects/p/render',json={'preview':False,'revision':2},headers=headers)
        assert response.status_code==400 and 'preview' in response.json()['detail']

def test_concurrent_project_save_does_not_overwrite_edits():
    original={'edl':{'revision':1}}
    with db.connect() as c: c.execute('INSERT INTO projects VALUES(?,?,?,?)',('p','test',db.encode(original),time.time()))
    db.save_project('p',{'edl':{'revision':2}},expected=original)
    with pytest.raises(ValueError): db.save_project('p',{'edl':{'revision':3}},expected=original)
    assert db.project('p')['edl']['revision']==2

def test_removed_caption_generation_preserves_existing_captions():
    captions=[{'start':1,'end':3,'text':'Existing caption','words':[]}]
    body={'edl':{'revision':1,'captions':captions}}
    with db.connect() as c:
        c.execute('INSERT INTO projects VALUES(?,?,?,?)',('p','test',db.encode(body),time.time()))
        c.execute('INSERT INTO preferences VALUES(?,?)',('caption_presets',db.encode({'My style':{'font':'Arial'}})))
    headers={'X-Ninja-Token':'test-token'}
    with TestClient(app) as client:
        for route in ('/api/projects/p/hinglish','/api/projects/p/transcribe','/api/presets'):
            assert client.post(route,json={},headers=headers).status_code in (404,405)
        exported=client.get('/api/projects/p/captions/json',headers=headers)
        assert exported.status_code==200 and exported.json()==captions
        assert db.project('p')['edl']['captions']==captions
    db.init()
    with db.connect() as c:
        assert json.loads(c.execute("SELECT value FROM preferences WHERE key='caption_presets'").fetchone()[0])=={'My style':{'font':'Arial'}}


def test_tool_permissions_and_validated_arguments():
    from ninja import tools
    with pytest.raises(ValueError,match='Permission'):tools.invoke('system.monitor',{},set())
    with pytest.raises(ValueError):tools.invoke('system.monitor',{'process_limit':1000},{'system.read'})
    result=tools.invoke('system.monitor',{'process_limit':2},{'system.read'})
    assert len(result['processes'])<=2 and 0<=result['cpu_percent']<=100

def test_large_file_scan_restricted_and_sorted(tmp_path,monkeypatch):
    from ninja import tools, config
    root=tmp_path/'approved';root.mkdir()
    (root/'small.txt').write_text('small')
    (root/'large.txt').write_text('large'*100)
    monkeypatch.setattr(config,'ROOTS',[root])
    result=tools.invoke('system.large_files',{'root':str(root)},{'system.read'})
    assert result['files'][0]['path'].endswith('large.txt') and result['visited']==2
    with pytest.raises(ValueError):tools.invoke('system.large_files',{'root':str(tmp_path)},{'system.read'})
