from pathlib import Path
import json
import pytest
from ninja import db,agent,tools,studio,assistant_tools
from ninja.agent_models import Request,Scope,ToolContext

def ctx(task):
    with db.connect() as c:body=json.loads(c.execute('SELECT body FROM agent_tasks WHERE id=?',(task,)).fetchone()[0])
    return ToolContext(task_id=task,scopes=[Scope(**s) for s in body['scopes']],plan_revision=0,idempotency_key='stable-tool-key')

def test_workflow_start_reuses_run_key_and_does_not_render(monkeypatch):
    from ninja import assistant_tools
    definition=studio.Definition(mode='finished',projects=[],rights='owned')
    saved=studio.save(definition.model_dump())
    task=agent.create(Request(text='Test this workflow',request_key='workflow-agent'))
    result=tools.invoke('workflow.start',{'workflow_id':saved['id'],'test':True},set(),context=ctx(task['task']))
    again=tools.invoke('workflow.start',{'workflow_id':saved['id'],'test':True},set(),context=ctx(task['task']))
    assert result==again
    with db.connect() as c:
        assert c.execute('SELECT count(*) FROM studio_runs').fetchone()[0]==1
        assert c.execute('SELECT count(*) FROM youtube_operations').fetchone()[0]==0

def test_folder_reads_stay_in_granted_root_and_hide_secret_files(monkeypatch,tmp_path):
    from ninja import assistant_tools
    folder=tmp_path/'allowed';folder.mkdir();(folder/'hello.txt').write_text('Hello')
    (folder/'.env').write_text('secret')
    monkeypatch.setattr(assistant_tools,'allowed_roots',lambda:[folder])
    task=agent.create(Request(text='Read files',request_key='files-agent',documents=[str(folder/'hello.txt')]));context=ctx(task['task'])
    assert tools.invoke('file.read',{'path':str(folder/'hello.txt')},set(),context=context)['data']['text']=='Hello'
    with pytest.raises(ValueError,match='secret'):tools.invoke('file.read',{'path':str(folder/'.env')},set(),context=context)
    with pytest.raises(ValueError):tools.invoke('file.read',{'path':str(tmp_path/'outside')},set(),context=context)


def test_parent_stop_cancels_its_owned_workflow_child():
    saved=studio.save(studio.Definition(mode='finished',rights='owned').model_dump())
    task=agent.create(Request(text='Test this workflow',request_key='parent-stop'))
    child=tools.invoke('workflow.start',{'workflow_id':saved['id'],'test':True},set(),context=ctx(task['task']))['data']
    agent.cancel(task['task'])
    with db.connect() as c:assert c.execute('SELECT state FROM jobs WHERE id=?',(child['job'],)).fetchone()[0]=='cancelled'


def test_public_search_falls_back_and_returns_actionable_failure(monkeypatch):
    from ninja import adapters
    import httpx
    class Client:
        def __init__(self,*a,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,url,**kw):
            if 'wikipedia' in url:return httpx.Response(403,request=httpx.Request('GET',url))
            return httpx.Response(200,content=b'<rss><channel><item><title>Official documentation</title><link>https://example.com/docs</link></item></channel></rss>',request=httpx.Request('GET',url))
    monkeypatch.setattr(adapters.httpx,'Client',Client)
    value=adapters.search_sources('local AI');assert value['provider']=='Bing RSS' and value['sources'][0]['url']=='https://example.com/docs'

def test_automatic_memory_cannot_accept_freeform_personal_records():
    from ninja.assistant_tools import Remember
    for text in ('I have diabetes','My phone number is 9876543210','a-secret-without-label'):
        with pytest.raises(ValueError):Remember.model_validate({'text':text})


def test_cancel_between_authorization_and_memory_write_is_rejected(monkeypatch):
    from ninja import memory
    task=agent.create(Request(text='Remember English',request_key='late-memory'))
    context=ctx(task['task']); original=memory.remember
    def race(*a,**kw):
        agent.cancel(task['task'])
        return original(*a,**kw)
    monkeypatch.setattr(memory,'remember',race)
    with pytest.raises(ValueError,match='cancelled'):
        tools.invoke('memory.remember',{'kind':'language','value':'English'},set(),context=context)
    assert memory.listing(context.scopes)==[]

def test_linked_workflow_change_is_bound_and_replay_safe():
    from ninja import studio_assistant
    saved=studio.save(studio.Definition(mode='finished',rights='owned').model_dump())
    task=agent.create(Request(text='Test this workflow',request_key='parent-change'))
    context=ctx(task['task'])
    child=tools.invoke('workflow.start',{'workflow_id':saved['id'],'test':True},set(),context=context)['data']
    context.idempotency_key='change-bound-key'
    result=tools.invoke('workflow.change',{'run_id':child['run'],'text':'Change the description tone to concise'},set(),context=context)
    assert result==tools.invoke('workflow.change',{'run_id':child['run'],'text':'Change the description tone to concise'},set(),context=context)
    children=agent.get(task['task'])['children']
    assert any(c['job']==result['data']['job'] for c in children)
    agent.cancel(task['task'])
    with db.connect() as c:assert c.execute('SELECT state FROM jobs WHERE id=?',(result['data']['job'],)).fetchone()[0]=='cancelled'

def test_unselected_personal_document_never_reaches_model(monkeypatch,tmp_path):
    folder=tmp_path/'allowed';folder.mkdir();path=folder/'personal.txt';path.write_text('I have diabetes',encoding='utf-8')
    monkeypatch.setattr(assistant_tools,'allowed_roots',lambda:[folder])
    task=agent.create(Request(text='List my notes',request_key='unselected-sensitive'))
    with pytest.raises(ValueError,match='Select and review'):
        tools.invoke('file.read',{'path':str(path)},set(),context=ctx(task['task']))

def test_cancel_between_authorization_and_reminder_write_is_rejected(monkeypatch):
    import time
    from datetime import datetime,timezone
    from ninja import assistant_events
    task=agent.create(Request(text='Remind me soon',request_key='late-reminder'))
    context=ctx(task['task']);original=assistant_events.add
    def race(*a,**kw):
        agent.cancel(task['task'])
        return original(*a,**kw)
    monkeypatch.setattr(assistant_events,'add',race)
    with pytest.raises(ValueError,match='cancelled'):
        tools.invoke('assistant.remind',{'text':'Check preview','when':datetime.fromtimestamp(time.time()+60,timezone.utc).isoformat()},set(),context=context)
    assert assistant_events.listing()==[]

def test_selected_text_edit_is_undoable_and_recovery_does_not_overwrite_new_work(monkeypatch,tmp_path):
    import hashlib
    path=tmp_path/'note.txt';path.write_text('Before',encoding='utf-8')
    monkeypatch.setattr(assistant_tools,'allowed_roots',lambda:[tmp_path])
    task=agent.create(Request(text='Edit my note',documents=[str(path)],request_key='edit-note'))
    context=ctx(task['task'])
    args={'path':str(path),'text':'After','expected_sha256':hashlib.sha256(b'Before').hexdigest()}
    first=tools.invoke('file.write',args,set(),context=context)
    output=Path(first['data']['output']);assert output.read_text()=='After' and path.read_text()=='Before'
    assert tools.invoke('file.write',args,set(),context=context)==first
    output.write_text('My newer work',encoding='utf-8')
    with pytest.raises(ValueError,match='changed'):tools.invoke('file.undo',{'receipt':first['data']['receipt']},set(),context=context)
    assert output.read_text()=='My newer work' and path.read_text()=='Before'
    output.write_text('After',encoding='utf-8')
    tools.invoke('file.undo',{'receipt':first['data']['receipt']},set(),context=context)
    assert path.read_text()=='Before' and not output.exists()
