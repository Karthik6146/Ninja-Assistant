import json,time
import pytest
from ninja import db,agent,adapters
from ninja.agent_models import Request,AgentTurn,ToolCall

def test_lanes_recover_only_own_work_and_fence_old_attempt():
    heavy=db.queue('p','render',{});control=db.queue('a','agent_turn',{})
    old=db.claim('heavy');assert old['id']==heavy and old['attempts']==1
    assert db.claim('control')['id']==control
    db.update_job(heavy,heartbeat=time.time()-100)
    assert db.claim('control') is None
    newer=db.claim('heavy');assert newer['attempts']==2
    with pytest.raises(ValueError,match='lease'):db.check_lease(heavy,old['attempts'])
    with pytest.raises(ValueError,match='lease'):db.update_job(heavy,expected_attempt=1,state='completed')

def test_task_request_deduplicates_and_rejects_forged_scope():
    from ninja.agent_models import Scope
    body=Request(text='Check system',request_key='first-request')
    one=agent.create(body);assert agent.create(body)==one
    with pytest.raises(ValueError,match='different'):agent.create(Request(text='Different',request_key=body.request_key))
    with pytest.raises(ValueError,match='scope'):agent.create(Request(text='Check system',scopes=[Scope(kind='channel',id='missing')],request_key='forged-request'))

def test_tools_result_reply_and_usage_saved_once(monkeypatch):
    calls=[]
    def turn(*a,**kw):
        calls.append(1)
        return AgentTurn(calls=[ToolCall(id='1',name='assistant.today',arguments={})],usage={'input_tokens':10,'output_tokens':5}) if len(calls)==1 else AgentTurn(text='You have no tasks yet. What shall we do?',usage={'input_tokens':20,'output_tokens':10})
    monkeypatch.setattr(adapters,'agent_turn',turn)
    task=agent.create(Request(text='What are todays tasks?',request_key='today-request'))
    job=db.claim('control')
    value=agent.execute(task['task'],job['id'],job['attempts'])
    assert value['reply'].startswith('You have')
    assert len(agent.get(task['task'])['steps'])==3
    with db.connect() as c:
        usage=c.execute('SELECT input_tokens,output_tokens FROM chat_usage WHERE job=?',(job['id'],)).fetchone()
        assert tuple(usage)==(30,15)
    assert agent.execute(task['task'],job['id'],job['attempts'])['reply']==value['reply']
    assert len(calls)==2

def test_change_instructions_keeps_completed_steps_and_cancelled_tool_denied(monkeypatch):
    from ninja.agent_models import Instruction
    task=agent.create(Request(text='Old request',request_key='old-request'))
    revised=agent.revise(task['task'],Instruction(text='New instruction',expected_revision=0,request_key='changed-request'))
    assert revised['revision']==1
    with pytest.raises(ValueError,match='changed'):agent.revise(task['task'],Instruction(text='Other',expected_revision=0,request_key='another-request'))
    agent.cancel(task['task'])
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:pytest.fail('Cancelled task used model'))
    job=db.claim('control');assert job is None


def test_cancelled_context_cannot_execute_and_stale_save_cannot_overwrite_revision():
    from ninja import permissions
    from ninja.agent_models import Scope,ToolContext,Instruction
    task=agent.create(Request(text='Check tasks',request_key='cancel-context'))
    claimed=db.claim('control');snapshot=agent.get(task['task'])
    agent.revise(task['task'],Instruction(text='New request',expected_revision=0,request_key='replace-context'))
    ctx=ToolContext(task_id=task['task'],scopes=[Scope()],plan_revision=0,idempotency_key='old',lease_job=claimed['id'],lease_attempt=claimed['attempts'])
    with pytest.raises(ValueError):permissions.authorize('assistant.today',{},ctx)
    with db.connect() as c:
        with pytest.raises(ValueError,match='changed'):agent.save(c,snapshot,expected_job=claimed['id'],expected_revision=0)
    assert agent.get(task['task'])['revision']==1

def test_gpu_busy_releases_control_claim_without_consuming_turn(monkeypatch):
    from filelock import Timeout
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:(_ for _ in ()).throw(Timeout('model.lock')))
    task=agent.create(Request(text='Today',request_key='busy-request'));job=db.claim('control')
    assert agent.execute(task['task'],job['id'],job['attempts'])=={'deferred':True}
    assert db.claim('control') is None
    with db.connect() as c:
        assert json.loads(c.execute('SELECT body FROM agent_tasks WHERE id=?',(task['task'],)).fetchone()[0])['turns']==0


def test_revoked_memory_never_enters_model_context(monkeypatch):
    from ninja import memory
    from ninja.agent_models import Scope
    memory.remember('My favourite color is lavender',Scope(),source='fixture')
    with db.connect() as c:c.execute('INSERT INTO preferences VALUES(?,?)',('assistant.permissions',db.encode({'assistant.memory':False})))
    observed=[]
    def turn(messages,*a,**kw):
        observed.extend(messages);return AgentTurn(text='Memory access is disabled')
    monkeypatch.setattr(adapters,'agent_turn',turn)
    task=agent.create(Request(text='What is my favourite color?',request_key='revoked-memory'))
    job=db.claim('control');agent.execute(task['task'],job['id'],job['attempts'])
    assert 'lavender' not in db.encode(observed)


def test_stale_attempt_cannot_save_or_replace_steps():
    task=agent.create(Request(text='Today',request_key='lease-recovery'));old=db.claim('control')
    snapshot=agent.get(task['task'])
    db.update_job(old['id'],heartbeat=time.time()-100);new=db.claim('control')
    assert new['attempts']==2
    with db.connect() as c:
        with pytest.raises(ValueError,match='lease'):agent.save(c,snapshot,expected_job=old['id'],expected_revision=0,expected_attempt=1)
    with pytest.raises(ValueError,match='lease'):agent.record(task['task'],'tool','completed',{},job=old['id'],attempt=1,revision=0)
    assert agent.get(task['task'])['steps']==[]

def test_old_memory_outputs_not_used_after_correction():
    from ninja import assistant_tools,tools
    assert tools.REGISTRY['memory.remember'].replay_safe is False
    assert 'purple' not in db.encode(agent.safe_history([{'role':'tool','tool_name':'memory.search','content':'purple captions'}]))



def test_new_instruction_invalidates_old_video_draft():
    from ninja.agent_models import Instruction
    created=agent.create(Request(text='Make English video',request_key='stale-draft'))
    with db.connect() as c:
        task=agent.load(c,created['task']);task['draft']={'summary':'Old English plan'};agent.save(c,task)
    agent.revise(created['task'],Instruction(text='Make it Hindi',expected_revision=0,request_key='draft-change-key'))
    with pytest.raises(ValueError,match='prepare a video draft'):agent.save_video_draft(created['task'],1)

def test_initial_reply_without_action_gets_one_bounded_recovery(monkeypatch):
    answers=iter([AgentTurn(text='I added the task'),AgentTurn(calls=[ToolCall(id='saved',name='assistant.add_task',arguments={'text':'Actual priority'})]),AgentTurn(text='The priority is saved')])
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:next(answers))
    created=agent.create(Request(text='Add Actual priority',request_key='recover-missing-tool'))
    job=db.claim('control');result=agent.execute(created['task'],job['id'],job['attempts'])
    assert result['verified_actions'] is True
    assert len([s for s in agent.get(created['task'])['steps'] if s['name']=='assistant.add_task'])==1

def test_unverified_reply_never_gets_verified_completion_label(monkeypatch):
    from ninja import worker
    observed=[]
    def turn(messages,*a,**kw):
        observed.append(messages);return AgentTurn(text='I saved it')
    monkeypatch.setattr(adapters,'agent_turn',turn)
    created=agent.create(Request(text='Add a priority',request_key='no-verified-action'))
    job=db.claim('control');worker.execute(job)
    task=agent.get(created['task'])
    assert len(observed)==2
    assert 'No tool action was verified' in task['reply']
    assert task['step']=='Reply saved; no tool action verified'
    assert task['verified_actions'] is False



def test_revised_mixed_success_and_failed_action_does_not_certify_reply(monkeypatch):
    from ninja import worker,assistant_desk
    from ninja.agent_models import Instruction
    answers=iter([
        AgentTurn(calls=[ToolCall(id='old',name='assistant.add_task',arguments={'text':'Existing priority'})]),
        AgentTurn(text='Saved'),
        AgentTurn(calls=[ToolCall(id='read',name='assistant.today',arguments={}),ToolCall(id='bad',name='assistant.add_task',arguments={'text':''})]),
        AgentTurn(text='New priority has been saved')])
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:next(answers))
    created=agent.create(Request(text='Add existing priority',request_key='prior-completion'))
    worker.execute(db.claim('control'))
    agent.revise(created['task'],Instruction(text='Add new priority',expected_revision=0,request_key='mixed-revision'))
    worker.execute(db.claim('control'))
    task=agent.get(created['task'])
    assert task['step']=='Reply saved; tool receipts recorded'
    assert task['reply'].startswith('Some tool calls failed;')
    assert task['failed_actions'] is True
    assert len(assistant_desk.today()['tasks'])==1
    revised=agent.revise(created['task'],Instruction(text='Try again',expected_revision=1,request_key='clear-failure-revision'))
    assert revised['verified_actions'] is False and revised['failed_actions'] is False


def test_concurrent_startup_migrates_existing_jobs_once():
    from concurrent.futures import ThreadPoolExecutor
    with db.connect() as c:c.execute('ALTER TABLE jobs DROP COLUMN available')
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda _:db.init(),range(3)))
    with db.connect() as c:
        assert len([r for r in c.execute('PRAGMA table_info(jobs)') if r[1]=='available'])==1
