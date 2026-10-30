from fastapi.testclient import TestClient
from ninja.api import app

def test_agent_routes_require_mutation_token_and_restore_tasks():
    with TestClient(app) as client:
        assert client.get('/api/assistant/tasks').status_code==401
        client.post('/api/session',json={'token':'test-token'})
        assert client.post('/api/assistant/tasks',json={'text':'Today','request_key':'test-first'}).status_code==403
        headers={'X-Ninja-Token':'test-token'}
        response=client.post('/api/assistant/tasks',headers=headers,json={'text':'Today','request_key':'test-first'})
        assert response.status_code==200
        id=response.json()['task']
        assert client.get('/api/assistant/tasks/'+id).json()['text']=='Today'
        assert client.post('/api/assistant/tasks',headers=headers,json={'text':'Today','request_key':'evil-test','shell':'cmd'}).status_code==422
        assert client.post('/api/assistant/tasks',headers=headers,json={'text':'Today','request_key':'scope-test','scopes':[{'kind':'channel','id':'missing'}]}).status_code==400
        assert client.post('/api/assistant/tasks/'+id+'/instructions',headers=headers,json={'text':'Add task','expected_revision':0,'request_key':'instruction-test'}).status_code==200
        assert client.post('/api/assistant/tasks/'+id+'/cancel',headers=headers,json={}).status_code==200


def test_private_question_leaves_no_task_job_memory_or_archive(monkeypatch):
    from ninja import db,adapters
    monkeypatch.setattr(adapters,'private_reply',lambda messages:{'text':'Private answer','usage':{'input_tokens':4,'output_tokens':2}})
    tables=['agent_tasks','agent_steps','jobs','job_events','assistant_memory','chat_usage']
    with db.connect() as c:before={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables}
    with TestClient(app) as client:
        client.post('/api/session',json={'token':'test-token'})
        result=client.post('/api/assistant/private',headers={'X-Ninja-Token':'test-token'},json={'messages':[{'role':'user','content':'A private question'}]})
        assert result.status_code==200
        assert result.json()['text']=='Private answer'
        assert result.headers['cache-control']=='no-store'
    with db.connect() as c:assert before=={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables}

def test_forget_task_removes_derived_memory_and_source_but_keeps_manual_preferences():
    from ninja import db,agent,memory
    from ninja.agent_models import Request,Scope
    task=agent.create(Request(text='Remember English',request_key='forget-source'))
    derived=memory.remember('Preferred language English',Scope(),source=task['task'])
    manual=memory.remember('I like concise replies',Scope(),source='manual')
    result=agent.forget_task(task['task'])
    assert result['forgotten']==task['task']
    with db.connect() as c:
        assert c.execute('SELECT 1 FROM agent_tasks WHERE id=?',(task['task'],)).fetchone() is None
        assert c.execute('SELECT 1 FROM jobs WHERE id=?',(task['job'],)).fetchone() is None
        assert c.execute('SELECT 1 FROM assistant_memory WHERE id=?',(derived['id'],)).fetchone() is None
        assert c.execute('SELECT 1 FROM assistant_memory WHERE id=?',(manual['id'],)).fetchone()


def test_task_stream_pushes_reply_and_closes_when_turn_finishes(monkeypatch):
    import json
    from ninja import adapters,db,worker
    from ninja.agent_models import AgentTurn
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:AgentTurn(text='Right away, sir.'))
    with TestClient(app) as client:
        client.post('/api/session',json={'token':'test-token'})
        id=client.post('/api/assistant/tasks',headers={'X-Ninja-Token':'test-token'},json={'text':'Hello','request_key':'stream-test'}).json()['task']
        worker.execute(db.claim('control'))
        body=client.get('/api/assistant/tasks/'+id+'/stream').text
    frames=[json.loads(line[6:]) for line in body.splitlines() if line.startswith('data: ')]
    assert frames[-1]['state']=='completed' and frames[-1]['reply'].endswith('Right away, sir.')
