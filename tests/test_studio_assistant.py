import json
import pytest
from ninja import db,studio,studio_assistant as assistant,adapters
from ninja.studio_models import Definition,Reference

def model(monkeypatch,**overrides):
    value=assistant.Plan(**{'name':'Shorts from my brief','summary':'Three vertical clips','mode':'clips','count':3,'seconds':60,'aspect':'9:16','preset':'education','captions':True,'language':'auto',**overrides}).model_dump()
    monkeypatch.setattr(adapters,'complete',lambda *a,**kw:{'text':json.dumps(value)})

def test_planner_preserves_channel_policy_and_treats_references_separately(monkeypatch):
    model(monkeypatch)
    flow=studio.save({'channel':'my-channel','policy':'public','rights':'licensed','automatic':True,'made_for_kids':False,'synthetic_media':False})
    monkeypatch.setattr(studio,'preflight',lambda d:{'ready':True,'issues':[]})
    result=assistant.draft(assistant.Brief(text='Create three shorts',workflow=flow['id'],source='https://www.youtube.com/watch?v=abcdefghijk',references=[Reference(kind='tool',url='https://example.com/editor')]))
    d=result['definition']
    assert d['channel']=='my-channel' and d['policy']=='public' and d['rights']=='licensed'
    assert d['urls']==['https://www.youtube.com/watch?v=abcdefghijk']
    assert d['references'][0]['kind']=='tool' and d['trigger']=='manual'
    assert not studio.get(flow['id'])['active']

def test_model_cannot_inject_authority_and_private_links_fail(monkeypatch):
    monkeypatch.setattr(adapters,'complete',lambda *a,**kw:{'text':json.dumps({'name':'bad','summary':'bad','channel':'stolen','policy':'public'})})
    with pytest.raises(ValueError):assistant.draft(assistant.Brief(text='anything'))
    for url in ['http://example.com','https://127.0.0.1/a','https://localhost/a','https://user:password@example.com']:
        with pytest.raises(ValueError):Reference(url=url)
    with pytest.raises(ValueError):Reference(kind='video',url='https://example.com')

def test_stop_revise_is_idempotent_and_retains_old_snapshot(monkeypatch):
    model(monkeypatch,seconds=45)
    flow=studio.save({'mode':'finished','projects':[],'prompt':'Original brief','channel':'channel-1','policy':'public'})
    run=studio.start(flow['id'],True,'original-run')
    body=assistant.Change(text='Make it 45 seconds',key='instruction-one')
    requested=assistant.steer(run['id'],body)
    assert assistant.steer(run['id'],body)==requested
    with db.connect() as c:
        assert c.execute('SELECT state FROM jobs WHERE id=?',(run['job'],)).fetchone()[0]=='cancelled'
        job=dict(c.execute('SELECT * FROM jobs WHERE id=?',(requested['job'],)).fetchone())
    monkeypatch.setattr(studio,'execute',lambda id,job:studio.load_run(id))
    revised=assistant.revise(json.loads(job['payload']),job['id'])
    assert revised['id']==requested['run'] and revised['definition']['seconds']==45
    assert revised['definition']['channel']=='channel-1' and revised['definition']['policy']=='public'
    assert revised['test'] and revised['definition']['mode']=='finished'
    old=studio.load_run(run['id']);assert old['definition']['prompt']=='Original brief' and old['superseded_by']==revised['id']
    assert assistant.revise(json.loads(job['payload']),job['id'])['id']==revised['id']
    assert len(studio.runs())==2

def test_publishing_task_and_pending_instruction_are_locked():
    flow=studio.save({});run=studio.start(flow['id'],True,'publishing-run')
    run['items']=[{'operation':'bound-upload'}];studio.checkpoint(run)
    with pytest.raises(ValueError,match='Publishing'):assistant.steer(run['id'],assistant.Change(text='Change',key='locked-run'))
    run['items']=[];studio.checkpoint(run)
    assistant.steer(run['id'],assistant.Change(text='Change',key='first-pending'))
    with pytest.raises(ValueError,match='pending'):assistant.steer(run['id'],assistant.Change(text='Another',key='second-pending'))

def test_reference_text_is_cached_and_never_becomes_footage(monkeypatch):
    calls=[]
    monkeypatch.setattr(adapters,'extract',lambda url:calls.append(url) or {'url':url,'excerpt':'Untrusted site text','retrieved':'now'})
    flow=studio.save({'references':[{'kind':'website','url':'https://example.com/style'}]});run=studio.start(flow['id'],True,'reference-run')
    assistant.references(run,run['job']);assistant.references(run,run['job'])
    assert calls==['https://example.com/style'] and not run['definition']['urls']
    assert studio.load_run(run['id'])['reference_evidence'][0]['excerpt']=='Untrusted site text'


def test_worker_dispatches_instruction_with_job_id(monkeypatch):
    from ninja import worker
    job=db.queue('old-run','studio_steer',{'run':'old-run','text':'Change','next':'new-run'})
    seen=[]
    monkeypatch.setattr(assistant,'revise',lambda payload,id:seen.append(id) or {'run':payload['next']})
    worker.execute(db.claim())
    assert seen==[job]
    with db.connect() as c:assert c.execute('SELECT state FROM jobs WHERE id=?',(job,)).fetchone()[0]=='completed'


def test_pending_instruction_prevents_retry_of_old_run():
    from ninja.studio_routes import retry
    flow=studio.save({});run=studio.start(flow['id'],True,'old-retry')
    assistant.steer(run['id'],assistant.Change(text='Change',key='pending-blocks-retry'))
    with pytest.raises(ValueError,match='pending'):retry(run['id'])
    run['superseded_by']='replacement';studio.checkpoint(run)
    with pytest.raises(ValueError,match='revised'):studio.execute(run['id'],run['job'])


def test_planner_schema_requires_numeric_choices():
    required=assistant.Plan.model_json_schema()['required']
    assert all(field in required for field in ('count','seconds','preset','captions'))
