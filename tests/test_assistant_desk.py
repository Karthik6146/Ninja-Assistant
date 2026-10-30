import copy,json,time
import pytest
from fastapi.testclient import TestClient
from ninja import db,assistant_desk as desk,studio_assistant as planner,studio,adapters,youtube_auth as auth,studio_metadata
from ninja.api import app

def model(monkeypatch):
    monkeypatch.setattr(adapters,'complete',lambda *a,**kw:{'text':json.dumps({'reply':'Work on the first priority.','question':'Which audience is this for?','suggestions':[{'text':'Plan an educational video','mode':'clips'}]}),'usage':{'input_tokens':20,'output_tokens':10}})

def test_daily_priorities_are_persisted_isolated_and_revision_checked(monkeypatch):
    monkeypatch.setattr(desk,'day',lambda:'2026-10-13')
    assert desk.today()['tasks']==[]
    task=desk.Priority(text='Prepare a Short');value=desk.save_today(desk.Today(tasks=[task]));assert value['revision']==1 and value['tasks'][0]['text']=='Prepare a Short'
    with pytest.raises(ValueError,match='changed'):desk.save_today(desk.Today(tasks=[]))
    task.done=True;desk.save_today(desk.Today(revision=1,tasks=[task]));assert '0 unfinished' in desk.today()['greeting']
    monkeypatch.setattr(desk,'day',lambda:'2026-10-14');assert desk.today()['tasks']==[]

def test_daily_advice_worker_is_idempotent_and_never_runs_content(monkeypatch):
    model(monkeypatch)
    body=desk.Ask(text='What should I do next?',key='daily-first-request');job=desk.talk(body)['job'];assert desk.talk(body)['job']==job
    with pytest.raises(ValueError,match='another'):desk.talk(desk.Ask(text='Other',key=body.key))
    from ninja import worker
    worker.execute(db.claim());value=desk.today()['messages'][0];assert value['state']=='completed' and value['advice']['question']=='Which audience is this for?'
    with db.connect() as c:
        assert c.execute('SELECT count(*) FROM studio_runs').fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM youtube_operations').fetchone()[0]==0

def test_idea_research_validates_evidence_and_keeps_connection(monkeypatch):
    captured=[]
    profile={'revision':0,'name':'Channel','audience':'Students','instructions':'Be concise','workflow':''}
    monkeypatch.setattr(auth,'connection_for',lambda channel:'authorized')
    monkeypatch.setattr(desk.studio_profiles,'listing',lambda:[{'id':'channel','title':'Channel','connected':True,'profile':profile}])
    def research(run,value):captured.append(run);return {'retrieved':time.time(),'limitations':'Counts do not prove virality','videos':[{'url':'https://youtube.com/watch?v=abcdefghijk','title':'Reference','views':'1000','evidence':'related'}]}
    monkeypatch.setattr(studio_metadata,'research',research)
    monkeypatch.setattr(adapters,'complete',lambda *a,**kw:{'text':json.dumps({'ideas':[{'title':'Original topic','hook':'Learn this','brief':'Create an explainer','reason':'Relevant audience','evidence':[1]}]})})
    job=desk.ideas(desk.Research(channel='channel',topic='AI tools',key='ideas-first-request'))['job']
    with db.connect() as c:payload=json.loads(c.execute('SELECT payload FROM jobs WHERE id=?',(job,)).fetchone()[0])
    value=desk.research(payload,job);assert value['sources'][0]['views']=='1000' and captured[0]['connection']=='authorized' and value['channel']=='channel'
    monkeypatch.setattr(adapters,'complete',lambda *a,**kw:{'text':json.dumps({'ideas':[{'title':'Topic','hook':'Hook','brief':'Brief','reason':'Reason','evidence':[99]}]})})
    with pytest.raises(ValueError,match='unsupported'):desk.research(payload,job)


def test_assistant_endpoints_keep_token_and_mutation_checks():
    with TestClient(app) as client:
        assert client.get('/api/assistant/today').status_code==401
        client.post('/api/session',json={'token':'test-token'})
        assert client.put('/api/assistant/today',json={'tasks':[]}).status_code==403
        assert client.put('/api/assistant/today',headers={'X-Ninja-Token':'test-token'},json={'tasks':[]}).status_code==200
        assert client.post('/api/assistant/talk',headers={'X-Ninja-Token':'test-token'},json={'text':'x','key':'valid-key','shell':'cmd'}).status_code==422






def test_edit_url_has_actionable_guidance():
    with pytest.raises(ValueError,match="Use Create clips"):
        planner.draft(planner.Brief(text="Edit it",mode="edit",source="https://youtube.com/watch?v=abcdefghijk"))
