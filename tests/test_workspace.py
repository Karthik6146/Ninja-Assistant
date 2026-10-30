import json
import sys
import threading
import time
import httpx
import pytest
from fastapi.testclient import TestClient
from ninja import adapters,db,media,worker,workspace as ws
from ninja.api import app

HEADERS={'X-Ninja-Token':'test-token'}








def test_interrupted_automation_not_automatically_replayed():
    job=db.queue('reports','automation',{})
    db.claim();db.update_job(job,heartbeat=time.time()-100)
    assert db.claim() is None
    assert ws.task(job)['state']=='failed' and ws.task(job)['error_code']=='INTERRUPTED'
    external=db.queue('external','youtube_execute',{})
    db.update_job(external,state='failed')
    with pytest.raises(ValueError,match='integration'):ws.retry(external,'retry-external')


def test_sse_reconnect_reconstructs_durable_state():
    job=db.queue('system','system_scan',{})
    db.update_job(job,step='Scanning approved folder')
    db.update_job(job,state='completed',result=db.encode({'files':[]}))
    client=TestClient(app)
    one=client.get('/api/tasks/'+job+'/stream',headers=HEADERS)
    two=client.get('/api/tasks/'+job+'/stream',headers={**HEADERS,'Last-Event-ID':'1'})
    assert one.status_code==200 and 'text/event-stream' in one.headers['content-type']
    for response in (one,two):
        snapshot=json.loads(next(line[6:] for line in response.text.splitlines() if line.startswith('data: ')))
        assert snapshot['state']=='completed' and snapshot['events'][-1]['type']=='completed'
        assert any(e['body']['summary']=='Scanning approved folder' for e in snapshot['events'])


def test_real_subprocess_cancellation():
    job=db.queue('system','system_scan',{})
    db.claim();result=[]
    def run():
        try:media.run([sys.executable,'-c','import time;time.sleep(30)'],job,timeout=40)
        except media.Cancelled:result.append('cancelled')
    thread=threading.Thread(target=run);thread.start();time.sleep(.4)
    response=TestClient(app).post('/api/jobs/'+job+'/cancel',headers=HEADERS,json={})
    assert response.status_code==200
    thread.join(timeout=5)
    assert not thread.is_alive() and result==['cancelled']


def test_automation_dedup_report_download_and_rerun(monkeypatch):
    monkeypatch.setattr(adapters,'provider_status',lambda:[{'name':'Ollama','message':'Ready'}])
    client=TestClient(app)
    template={'name':'Daily checks','kind':'diagnostics','checks':['providers']}
    saved=client.post('/api/templates',headers=HEADERS,json=template);assert saved.status_code==200
    body={'template':template,'request_key':'automation-key'}
    first=client.post('/api/automations/run',headers=HEADERS,json=body).json()['job']
    assert client.post('/api/automations/run',headers=HEADERS,json=body).json()['job']==first
    worker.execute(db.claim())
    assert ws.task(first)['state']=='completed'
    report=client.get('/api/tasks/'+first+'/output',headers=HEADERS)
    assert report.status_code==200 and 'Ollama: Ready' in report.text
    body['request_key']='rerun-automation'
    second=client.post('/api/automations/run',headers=HEADERS,json=body).json()['job']
    assert second!=first
    worker.execute(db.claim())
    assert ws.task(second)['state']=='completed'
    with db.connect() as c:assert c.execute('SELECT count(*) FROM publications').fetchone()[0]==0


def test_source_report_rejects_fabricated_citations(monkeypatch):
    monkeypatch.setattr(adapters,'extract',lambda url:{'url':url,'excerpt':'Supplied evidence','retrieved':'2026-10-05','status':'retrieved'})
    monkeypatch.setattr(adapters,'stream_chat',lambda *args:{'text':json.dumps({'text':'Claim [99]','citations':[99]})})
    body={'template':{'name':'Research','kind':'research','question':'Question','urls':['https://example.com']}}
    job=db.queue('automation','automation',body);worker.execute(db.claim())
    assert ws.task(job)['state']=='failed'
    assert not (db.DATA/'outputs'/(job+'.md')).exists()
    monkeypatch.setattr(adapters,'stream_chat',lambda *args:{'text':json.dumps({'text':'Evidence [1]','citations':[1]})})
    next=db.queue('automation','automation',body);worker.execute(db.claim())
    result=ws.task(next)
    assert result['state']=='completed' and 'https://example.com' in result['result']['text']


def test_migration_preserves_caption_outputs_and_marks_removed_work():
    first=db.queue('p','transcribe',{});second=db.queue('p','transcribe',{})
    db.update_job(second,state='waiting-review')
    db.init();db.init()
    assert ws.task(first)['state']=='failed'
    assert ws.task(second)['state']=='waiting_for_approval'


def test_caption_connection_is_local_and_does_not_transfer_files(monkeypatch,tmp_path):
    calls=[]
    def get(url,**kwargs):calls.append(url);return httpx.Response(200,text='<title>ClipX</title>')
    monkeypatch.setattr(httpx,'get',get)
    for url in ('https://example.com','http://example.com','http://user:pass@localhost:3000','file:///C:/Windows'):
        with pytest.raises(ValueError):ws.caption_connection({'url':url,'path':''})
    result=ws.caption_connection({'url':'http://127.0.0.1:3000','path':str(tmp_path)})
    assert result['available'] and result['mode']=='open' and calls==['http://127.0.0.1:3000']
    assert not ws.caption_connection({'url':'','path':''})['configured']


def test_provider_stream_failure_and_partial_answer(monkeypatch):
    class Stream:
        status_code=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_lines(self):return iter([json.dumps({'message':{'content':'Partial'},'done':False})])
    monkeypatch.setattr(httpx,'stream',lambda *args,**kwargs:Stream())
    partial=[]
    with pytest.raises(ValueError,match='without a complete answer'):
        adapters.stream_chat([{'role':'user','content':'Test'}],'ollama','fixture',partial.append)
    assert partial==['Partial']


def test_local_provider_rejects_remote_endpoint(monkeypatch):
    monkeypatch.setenv('OLLAMA_URL','http://example.com:11434')
    with pytest.raises(ValueError,match='loopback'):adapters.ollama_url()
    assert not adapters.provider_status()[0]['available']


def test_queued_cancellation_has_terminal_time_and_event():
    job=db.queue('system','system_scan',{})
    TestClient(app).post('/api/jobs/'+job+'/cancel',headers=HEADERS,json={})
    result=ws.task(job)
    assert result['state']=='cancelled' and result['finished']>=result['created']
    assert result['events'][-1]['type']=='cancelled'


def test_migration_snapshot_can_be_restored(tmp_path):
    import sqlite3
    job=db.queue('legacy','transcribe',{})
    db.update_job(job,state='waiting-review')
    with db.connect() as current, sqlite3.connect(tmp_path/'before.sqlite') as snapshot:
        current.backup(snapshot)
    db.init()
    assert ws.task(job)['state']=='waiting_for_approval'
    with sqlite3.connect(tmp_path/'before.sqlite') as snapshot,db.connect() as current:
        snapshot.backup(current)
    assert ws.task(job)['state']=='waiting-review'


def test_files_preserves_originals_and_legacy_reports():
    with db.connect() as c:
        c.execute('INSERT INTO projects VALUES(?,?,?,?)',('fixture','Original',db.encode({'id':'fixture','name':'Original','source':'source.mp4','edl':{'captions':[]}}),time.time()))
    folder=db.DATA/'research';folder.mkdir(exist_ok=True)
    report=folder/('a'*32+'.md');report.write_text('Historical source notebook',encoding='utf-8')
    try:
        rows=TestClient(app).get('/api/files',headers=HEADERS).json()
        assert any(r['kind']=='Original video' for r in rows)
        assert any(r['kind']=='Current SRT' for r in rows)
        assert any(r['kind']=='Legacy report' for r in rows)
    finally:report.unlink()
