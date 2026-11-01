"""Small assistant actions; no arbitrary commands or credentials."""
import uuid
from typing import Literal
from pydantic import Field
from . import tools,assistant_desk as desk,db
from .agent_models import Strict

class Empty(Strict):pass
class Result(Strict):
    data:dict
def today(params,timeout,context):return {'data':desk.today()}

class Add(Strict):text:str=Field(min_length=1,max_length=200)
def add(params,timeout,context):
    # Stable priority identity makes recovery of this reversible write safe.
    id=uuid.uuid5(uuid.NAMESPACE_URL,context.idempotency_key).hex
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if context.lease_job is not None:db.check_lease(context.lease_job,context.lease_attempt,c)
        state=desk.load_today(c,desk.day())
        if not any(v.id==id for v in state.tasks):
            if len(state.tasks)>=30:raise ValueError('Today already has 30 priorities')
            state.tasks.append(desk.Priority(id=id,text=params.text));state.revision+=1
            c.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('assistant-day:'+desk.day(),db.encode(state.model_dump())))
    return {'data':{'added':params.text,'id':id,'date':desk.day()}}

tools.REGISTRY['assistant.today']=tools.Tool('assistant.today',Empty,Result,'assistant.tasks',5,today,'routine',True,True)
tools.REGISTRY['assistant.add_task']=tools.Tool('assistant.add_task',Add,Result,'assistant.tasks',5,add,'routine',True,True)


class Recall(Strict):query:str=Field(min_length=1,max_length=500)
def recall(params,timeout,context):
    from . import memory
    return {'data':{'memories':memory.context(params.query,context.scopes)}}
class Remember(Strict):
    kind:Literal['language','tone','editing']
    value:Literal['English','Hindi','Hinglish','concise','detailed','friendly','formal','education','gaming','podcast','cinematic']
    scope_id:str=Field(default='me',max_length=100)
def remember(params,timeout,context):
    from . import memory
    scope=next((s for s in context.scopes if s.id==params.scope_id),None)
    if scope is None:raise ValueError('Memory scope is not part of this task')
    choices={'language':{'English','Hindi','Hinglish'},'tone':{'concise','detailed','friendly','formal'},'editing':{'education','gaming','podcast','cinematic'}}
    if params.value not in choices[params.kind]:raise ValueError('Unsupported preference combination. Save other non-sensitive facts manually in Settings.')
    value=memory.remember('Preferred '+params.kind+': '+params.value,scope,source=context.task_id,context=context)
    return {'data':{k:value[k] for k in ('id','text','scope','source','revision')}}
tools.REGISTRY['memory.search']=tools.Tool('memory.search',Recall,Result,'assistant.memory',5,recall,'routine',True,True)
tools.REGISTRY['memory.remember']=tools.Tool('memory.remember',Remember,Result,'assistant.memory',5,remember,'routine',True,False)


from typing import Literal
from pathlib import Path
import os,json,time,hashlib
from . import studio,adapters
from .config import ROOTS,DATA

def allowed_roots():return [Path(r).resolve() for r in ROOTS]
def file_path(value,folder=False):
    try:path=Path(value).resolve(strict=True)
    except OSError:raise ValueError('File or folder not found; check the path in Settings') from None
    if not any(path.is_relative_to(r) for r in allowed_roots()):raise ValueError('Path is outside approved folders. Set NINJA_ROOTS in Settings setup.')
    parts={p.lower() for p in path.parts}
    if any(p.startswith('.env') for p in parts) or parts&{'.git','.aws','youtube-secrets','access-token'} or path.suffix.lower() in ('.pem','.key','.pfx','.p12'):
        raise ValueError('Credential or secret files are not assistant-readable')
    if (not path.is_dir() if folder else not path.is_file()):raise ValueError('Choose a '+('folder' if folder else 'regular file'))
    return path
class PathInput(Strict):path:str=Field(min_length=1,max_length=2000)
def read_file(params,timeout,context):
    path=shared_file(params.path,context)
    if path.stat().st_size>1048576:raise ValueError('Text read exceeds 1 MiB; choose a smaller file')
    try:
        with path.open('rb') as source:raw=source.read(1048577)
        if len(raw)>1048576:raise ValueError('Text read exceeds 1 MiB; the file changed while reading')
        text=raw.decode('utf-8-sig')
    except UnicodeError:raise ValueError('This file is not supported UTF-8 text') from None
    # Reuse the memory secret boundary before giving a document to the model.
    from .memory import SECRET,SENSITIVE
    import re
    if SENSITIVE.search(text) or re.search(r'(?:\d[ -]?){8,}',text):raise ValueError('This may contain sensitive personal information. Use a sanitized document; protected sensitive-file handling is unavailable.')
    if SECRET.search(text):raise ValueError('This text appears to contain credentials; select a sanitized file')
    return {'data':{'path':str(path),'text':text[:10000],'sha256':hashlib.sha256(raw).hexdigest(),'truncated':len(text)>10000}}
def list_files(params,timeout,context):
    path=file_path(params.path,True);items=[]
    for p in path.iterdir():
        if len(items)>=200:break
        try:resolved=file_path(str(p),p.is_dir())
        except (ValueError,OSError):continue
        items.append({'name':resolved.name,'path':str(resolved),'folder':resolved.is_dir()})
    return {'data':{'items':items,'limit':200}}

class StartWorkflow(Strict):
    workflow_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    test:bool=False
def workflow_start(params,timeout,context):
    saved=studio.get(params.workflow_id);target=saved['definition']['channel']
    if target and not any(s.kind=='channel' and s.id==target for s in context.scopes):raise ValueError('Choose this exact target channel in the assistant selector first')
    # Existing snapshots, activation and publishing policies remain authoritative.
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if context.lease_job is not None:db.check_lease(context.lease_job,context.lease_attempt,c)
        body=json.loads(c.execute('SELECT body FROM studio_workflows WHERE id=?',(params.workflow_id,)).fetchone()[0])
        if body['definition']['channel']!=target:raise ValueError('Workflow target changed; reopen before running')
        from . import agent
        task=agent.load(c,context.task_id)
        if task['revision']!=context.plan_revision or task.get('state')=='cancelled':raise ValueError('Task changed or cancelled')
        run=studio.enqueue(c,body,params.test,'assistant:'+context.idempotency_key)
        if not any(v['run']==run['id'] for v in task.setdefault('children',[])):
            task['children'].append({'run':run['id'],'job':run['job'],'channel':run['definition']['channel']});agent.save(c,task)
    return {'data':{'run':run['id'],'job':run['job'],'channel':run['definition']['channel'],'test':run['test'],'policy':run['definition']['policy'],'state':'queued'}}
def workflows(params,timeout,context):
    targets={s.id for s in context.scopes if s.kind=='channel'}
    return {'data':{'workflows':[{'id':w['id'],'name':w['definition']['name'],'mode':w['definition']['mode'],'channel':w['definition']['channel'],'active':w['active'],'policy':w['definition']['policy']} for w in studio.listing() if not w['definition']['channel'] or w['definition']['channel'] in targets]}}

class URLInput(Strict):url:str=Field(min_length=1,max_length=2000)
def fetch(params,timeout,context):return {'data':adapters.extract(params.url)}
class Search(Strict):query:str=Field(min_length=1,max_length=200)
def search(params,timeout,context):
    value=adapters.search_sources(params.query)
    return {'data':value|{'retrieved':time.time(),'limitation':'Discovery results only. Fetch sources before citing claims; popularity is not guaranteed virality.'}}

for name,input,callback,permission in [
 ('file.read',PathInput,read_file,'file.read'),('file.list',PathInput,list_files,'file.read'),
 ('workflow.list',Empty,workflows,'assistant.workflows'),('workflow.start',StartWorkflow,workflow_start,'assistant.workflows'),
 ('research.fetch',URLInput,fetch,'research.read'),('research.search',Search,search,'research.read')]:
    tools.REGISTRY[name]=tools.Tool(name,input,Result,permission,20,callback,'routine',True,True)




from datetime import datetime
from zoneinfo import ZoneInfo
class Reminder(Strict):
    text:str=Field(min_length=1,max_length=200)
    when:str=Field(default='',max_length=60,description='ISO date/time for a clock time, e.g. 2026-10-31T19:00')
    in_minutes:float|None=Field(default=None,gt=0,le=10080,description='For timers and "in 20 minutes" / "2 ghante baad": minutes from now instead of when')
def remind(params,timeout,context):
    from . import assistant_events
    if params.in_minutes:
        # A replayed step computes a slightly later time; the saved reminder is the same one.
        return {'data':assistant_events.add(params.text,time.time()+params.in_minutes*60,context.idempotency_key,context=context,tolerance=600)}
    try:
        due=datetime.fromisoformat(params.when)
        if due.tzinfo is None:due=due.replace(tzinfo=ZoneInfo('Asia/Kolkata'))
    except ValueError:raise ValueError('Give when as an ISO date/time (Asia/Kolkata), or in_minutes for a timer.') from None
    return {'data':assistant_events.add(params.text,due.timestamp(),context.idempotency_key,context=context)}
tools.REGISTRY['assistant.remind']=tools.Tool('assistant.remind',Reminder,Result,'assistant.tasks',5,remind,'routine',True,True)


class ChangeWorkflow(Strict):
    run_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    text:str=Field(min_length=1,max_length=3000)

def workflow_change(params,timeout,context):
    from . import studio_assistant
    key=hashlib.sha256(context.idempotency_key.encode()).hexdigest()
    return {'data':studio_assistant.steer(params.run_id,studio_assistant.Change(text=params.text,key=key),context)}

tools.REGISTRY['workflow.change']=tools.Tool('workflow.change',ChangeWorkflow,Result,'assistant.workflows',20,workflow_change,'routine',True,True)

class DraftWorkflow(Strict):
    text:str=Field(min_length=1,max_length=3000)
    mode:Literal['auto','clips','edit','finished']='auto'
    source:str=Field(default='',max_length=2000)
    workflow_id:str=Field(default='',pattern=r'^(?:[a-f0-9]{32})?$')

def workflow_draft(params,timeout,context):
    from . import studio_assistant
    channels=[s.id for s in context.scopes if s.kind=='channel']
    if len(channels)>1:raise ValueError('Choose one target channel for this draft')
    channel=channels[0] if channels else ''
    if params.workflow_id:
        d=studio.get(params.workflow_id)['definition']
        if d['channel']!=channel:raise ValueError('Workflow belongs to another channel')
    planned=studio_assistant.draft(studio_assistant.Brief(text=params.text,mode=params.mode,channel=channel,source=params.source,workflow=params.workflow_id))
    # A proposed source/style must be reviewed; an existing policy never authorizes a changed source.
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        from . import agent,permissions
        permissions.check_write(c,'workflow.draft',context)
        task=agent.load(c,context.task_id);task['draft']=planned;agent.save(c,task)
    return {'data':planned}

tools.REGISTRY['workflow.draft']=tools.Tool('workflow.draft',DraftWorkflow,Result,'assistant.workflows',120,workflow_draft,'routine',True,True)

class WriteText(Strict):
    path:str=Field(min_length=1,max_length=2000)
    text:str=Field(max_length=2000)
    expected_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')
class UndoText(Strict):
    receipt:str=Field(pattern=r'^[a-f0-9]{64}$')

def shared_file(value,context):
    from . import permissions
    path=file_path(value);task=permissions.authority(context)
    if str(path) not in task['request'].get('documents',[]):raise ValueError('Select and review this exact non-sensitive document in the assistant prompt before sharing it with Qwen')
    return path

def replace_text(path,raw):
    import tempfile
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.ninja-',suffix='.tmp',delete=False) as output:
            temporary=Path(output.name);output.write(raw);output.flush();os.fsync(output.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def write_text(params,timeout,context):
    from . import permissions
    from .memory import validate
    from filelock import FileLock
    path=shared_file(params.path,context)
    if path.suffix.lower() not in ('.txt','.md'):raise ValueError('Reversible assistant edits support selected .txt and .md documents only')
    if params.text:validate(params.text)
    raw=params.text.encode('utf-8');new=hashlib.sha256(raw).hexdigest()
    receipt=hashlib.sha256((context.task_id+':'+context.idempotency_key).encode()).hexdigest()
    directory=DATA/'assistant-file-backups';directory.mkdir(exist_ok=True)
    saved=directory/(receipt+'.json');output=path.with_name(path.stem+'.jarvis-'+receipt[:12]+path.suffix)
    with FileLock(DATA/('assistant-file-'+receipt+'.lock'),timeout=0),db.connect() as c:
        c.execute('BEGIN IMMEDIATE');permissions.check_write(c,'file.write',context)
        backup=json.loads(saved.read_text(encoding='utf-8')) if saved.exists() else None
        if backup:
            if backup['task']!=context.task_id or backup['path']!=str(path) or backup['before']!=params.expected_sha256 or backup['after']!=new:raise ValueError('Edit receipt belongs to different inputs')
            if backup.get('undone'):raise ValueError('This edit was undone; give a new instruction for another edit')
        if not backup:
            with path.open('rb') as source:previous=source.read(10001)
            if len(previous)>10000:raise ValueError('Editable documents are limited to 10,000 bytes')
            if hashlib.sha256(previous).hexdigest()!=params.expected_sha256:raise ValueError('Document changed; read the current version before editing')
            backup={'task':context.task_id,'path':str(path),'output':str(output),'before':params.expected_sha256,'after':new}
            replace_text(saved,db.encode(backup).encode('utf-8'))
        if output.is_symlink():raise ValueError('Edited copy path must not be a link')
        if output.exists():
            with output.open('rb') as existing:value=existing.read(10001)
            if hashlib.sha256(value).hexdigest()!=new:raise ValueError('Edited copy changed or an interrupted write is incomplete; inspect it before retrying')
        else:
            # Exclusive creation preserves originals and concurrent editor saves.
            with output.open('xb') as destination:destination.write(raw);destination.flush();os.fsync(destination.fileno())
    return {'data':{'path':str(path),'output':str(output),'sha256':new,'receipt':receipt,'undo_available':True,'verification':'Edited copy created; original retained.'}}

def undo_text(params,timeout,context):
    from . import permissions
    from filelock import FileLock
    saved=DATA/'assistant-file-backups'/(params.receipt+'.json')
    if not saved.is_file():raise ValueError('Undo receipt not found')
    backup=json.loads(saved.read_text(encoding='utf-8'))
    if backup['task']!=context.task_id:raise ValueError('Undo receipt belongs to another task')
    path=shared_file(backup['path'],context);output=Path(backup['output']);archived=output.with_name('.ninja-undone-'+params.receipt+output.suffix)
    with FileLock(DATA/('assistant-file-'+params.receipt+'.lock'),timeout=0),db.connect() as c:
        c.execute('BEGIN IMMEDIATE');permissions.check_write(c,'file.undo',context)
        if output.is_symlink() or archived.is_symlink():raise ValueError('Edited copy or archive must not be a link')
        if not output.exists() and archived.is_file():
            with archived.open('rb') as source:value=source.read(10001)
            if hashlib.sha256(value).hexdigest()!=backup['after']:raise ValueError('Archived copy changed; inspect it before retrying')
        else:
            with output.open('rb') as source:value=source.read(10001)
            if hashlib.sha256(value).hexdigest()!=backup['after']:raise ValueError('Edited copy changed; undo will not replace newer work')
            if archived.exists():raise ValueError('Undo archive already exists; inspect it before retrying')
            # Same-directory rename retains even a concurrent save; source remains intact.
            output.rename(archived)
        backup['undone']=True;replace_text(saved,db.encode(backup).encode('utf-8'))
    return {'data':{'original':str(path),'archived_copy':str(archived)}}

tools.REGISTRY['file.write']=tools.Tool('file.write',WriteText,Result,'file.write',5,write_text,'routine',True,True)
tools.REGISTRY['file.undo']=tools.Tool('file.undo',UndoText,Result,'file.write',5,undo_text,'routine',True,True)


# Read-only research tools register themselves on import.
from . import research_tools,device_tools,gmail,whatsapp,watch  # noqa: E402,F401
