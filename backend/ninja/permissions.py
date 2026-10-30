"""Backend-held grants and parameter-bound sensitive approvals."""
import hashlib,json,time,uuid
from contextlib import nullcontext
from . import db
from .agent_models import ToolContext

DEFAULT_GRANTS={'system.read':True,'assistant.tasks':True,'assistant.memory':True,'file.read':True,'file.write':True,'assistant.workflows':True,'research.read':True,'app.open':True,'device.control':True,'files.personal':True,'email.read':True,'messages.read':True}
SENSITIVE={'financial','security','privacy','destructive'}
# Tools that only read. Once email or web text is in a conversation, every other tool needs the user's confirmation,
# so instructions hidden in that text cannot act on their own.
READS={'system.monitor','system.large_files','assistant.today','memory.search','file.find','file.list','file.read',
       'research.search','research.deep','research.fetch','weather.now','youtube.search','gmail.list','gmail.read','whatsapp.recent','workflow.list'}
# file.read: shared documents can be written by anyone (downloads, attachments).
UNTRUSTED={'email.read','messages.read','research.read','file.read'}

def grants(connection=None):
    with (db.connect() if connection is None else nullcontext(connection)) as c:row=c.execute("SELECT value FROM preferences WHERE key='assistant.permissions'").fetchone()
    return DEFAULT_GRANTS| (json.loads(row[0]) if row else {})

def authority(context:ToolContext,connection=None):
    with (db.connect() if connection is None else nullcontext(connection)) as c:row=c.execute('SELECT body FROM agent_tasks WHERE id=?',(context.task_id,)).fetchone()
    if not row:raise ValueError('Assistant task not found')
    task=json.loads(row[0])
    if context.plan_revision!=task['revision']:raise ValueError('Task changed; reload its instructions')
    if [s.model_dump() for s in context.scopes]!=task['scopes']:raise ValueError('Task scope does not match server authorization')
    if task.get('state')=='cancelled':raise ValueError('Task cancelled')
    if context.lease_job is not None:
        if task.get('job')!=context.lease_job:raise ValueError('Task changed')
        db.check_lease(context.lease_job,context.lease_attempt,connection)
        if db.cancelled(context.lease_job):raise ValueError('Task cancelled')
    if context.private:raise ValueError('Private task execution is not enabled')
    return task

def decide(name,args,context,connection=None):
    from .tools import REGISTRY
    authority(context,connection)
    tool=REGISTRY.get(name)
    if not tool:raise ValueError('Unknown tool')
    grant=grants(connection).get(tool.permission)
    if grant is False:return 'deny'
    if tool.effect in SENSITIVE or grant=='ask' or (context.tainted and name not in READS):return 'confirm'
    if tool.effect!='routine':return 'deny'
    return 'allow' if grant is True else 'deny'

def bound(name,args,context):
    return {'task':context.task_id,'revision':context.plan_revision,'scopes':[s.model_dump() for s in context.scopes],'tool':name,'arguments':args}

def request(name,args,context):
    from .tools import REGISTRY
    args=REGISTRY[name].input_schema.model_validate(args).model_dump()
    if decide(name,args,context)!='confirm':raise ValueError('This tool does not need sensitive confirmation')
    id=uuid.uuid4().hex
    digest=hashlib.sha256(db.encode(bound(name,args,context)).encode()).hexdigest()
    with db.connect() as c:c.execute('INSERT INTO approvals VALUES(?,?,?,?,?)',(id,'assistant.tool',digest,'pending',time.time()))
    db.audit('assistant.confirmation-requested',{'id':id,'tool':name,'task':context.task_id})
    return id

def authorize(name,args,context):
    decision=decide(name,args,context)
    if decision=='deny':raise ValueError('Permission denied; enable the supported capability in Settings')
    if decision=='confirm':
        digest=hashlib.sha256(db.encode(bound(name,args,context)).encode()).hexdigest()
        with db.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM approvals WHERE id=?',(context.approval_id,)).fetchone()
            if not row or row['action']!='assistant.tool' or row['state']!='approved' or row['digest']!=digest:raise ValueError('Sensitive confirmation absent, consumed or changed')
            if time.time()-row['created']>600:raise ValueError('Sensitive confirmation expired')
            c.execute("UPDATE approvals SET state='consumed' WHERE id=?",(row['id'],))
    return decision


def check_write(c,name,context):
    if decide(name,{},context,c)!='allow':raise ValueError('Routine permission revoked; open Settings')
