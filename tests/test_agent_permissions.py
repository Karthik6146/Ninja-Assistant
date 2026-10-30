import json,time
import pytest
from pydantic import BaseModel
from ninja import db,tools,permissions
from ninja.agent_models import ToolContext,Scope

def context(revision=0):
    with db.connect() as c:
        c.execute("INSERT OR REPLACE INTO agent_tasks VALUES(?,?,?)",('task',db.encode({'revision':0,'scopes':[{'kind':'personal','id':'me'}]}),time.time()))
    return ToolContext(task_id='task',scopes=[Scope(kind='personal',id='me')],plan_revision=revision,idempotency_key='step')

def test_unknown_and_legacy_new_tool_never_execute(monkeypatch):
    called=[]
    class Input(BaseModel): value:int=1
    class Output(BaseModel): value:int
    monkeypatch.setitem(tools.REGISTRY,'test.security',tools.Tool('test.security',Input,Output,'security.change',5,lambda *a,**k:called.append(1),'security'))
    with pytest.raises(ValueError,match='Unknown'):tools.invoke('missing',{},set())
    with pytest.raises(ValueError,match='context'):tools.invoke('test.security',{}, {'security.change'})
    assert called==[]

def test_scope_forgery_revision_and_revocation():
    ctx=context()
    assert permissions.decide('system.monitor',{},ctx)=='allow'
    forged=ctx.model_copy(update={'scopes':[Scope(kind='channel',id='other')]})
    with pytest.raises(ValueError,match='scope'):permissions.decide('system.monitor',{},forged)
    with pytest.raises(ValueError,match='changed'):permissions.decide('system.monitor',{},context(1))
    with db.connect() as c:c.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('assistant.permissions',db.encode({'system.read':False})))
    assert permissions.decide('system.monitor',{},context())=='deny'

def test_sensitive_confirmation_exact_expiring_and_single_use(monkeypatch):
    class Input(BaseModel): value:int
    class Output(BaseModel): value:int
    monkeypatch.setitem(tools.REGISTRY,'test.security',tools.Tool('test.security',Input,Output,'security.change',5,lambda p,timeout:{'value':p.value},'security'))
    ctx=context()
    assert permissions.decide('test.security',{'value':1},ctx)=='confirm'
    approval=permissions.request('test.security',{'value':1},ctx)
    with db.connect() as c:c.execute("UPDATE approvals SET state='approved' WHERE id=?",(approval,))
    approved=ctx.model_copy(update={'approval_id':approval})
    with pytest.raises(ValueError):permissions.authorize('test.security',{'value':2},approved)
    permissions.authorize('test.security',{'value':1},approved)
    with pytest.raises(ValueError):permissions.authorize('test.security',{'value':1},approved)
    expired=permissions.request('test.security',{'value':1},ctx)
    with db.connect() as c:c.execute("UPDATE approvals SET state='approved',created=? WHERE id=?",(time.time()-601,expired))
    with pytest.raises(ValueError,match='expired'):permissions.authorize('test.security',{'value':1},ctx.model_copy(update={'approval_id':expired}))


def test_revoked_sensitive_capability_denies_even_with_approval(monkeypatch):
    called=[]
    class Input(BaseModel):value:int
    class Output(BaseModel):value:int
    monkeypatch.setitem(tools.REGISTRY,'test.security',tools.Tool('test.security',Input,Output,'security.change',5,lambda p,timeout:called.append(1) or {'value':p.value},'security'))
    ctx=context();approval=permissions.request('test.security',{'value':1},ctx)
    with db.connect() as c:
        c.execute("UPDATE approvals SET state='approved' WHERE id=?",(approval,))
        c.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('assistant.permissions',db.encode({'security.change':False})))
    with pytest.raises(ValueError,match='Permission denied'):tools.invoke('test.security',{'value':1},set(),context=ctx.model_copy(update={'approval_id':approval}))
    assert called==[]

def test_invalid_arguments_do_not_consume_sensitive_confirmation(monkeypatch):
    class Input(BaseModel):value:int
    class Output(BaseModel):value:int
    monkeypatch.setitem(tools.REGISTRY,'test.security',tools.Tool('test.security',Input,Output,'security.change',5,lambda p,timeout:{'value':p.value},'security'))
    ctx=context();approval=permissions.request('test.security',{'value':1},ctx)
    with db.connect() as c:c.execute("UPDATE approvals SET state='approved' WHERE id=?",(approval,))
    with pytest.raises(ValueError):tools.invoke('test.security',{'value':'invalid'},set(),context=ctx.model_copy(update={'approval_id':approval}))
    with db.connect() as c:assert c.execute('SELECT state FROM approvals WHERE id=?',(approval,)).fetchone()[0]=='approved'

