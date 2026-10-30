import contextlib
import hashlib
import json
import sqlite3
import time
import uuid
from .config import DATA

def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

@contextlib.contextmanager
def connect():
    con = sqlite3.connect(DATA / 'ninja.sqlite', timeout=30)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

def init():
    with connect() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT,body TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,project TEXT,kind TEXT,payload TEXT,state TEXT,progress REAL DEFAULT 0,error TEXT,result TEXT,created REAL,heartbeat REAL,attempts INTEGER DEFAULT 0,cancel INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,event TEXT,body TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS preferences(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY,action TEXT,digest TEXT,state TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS publications(id TEXT PRIMARY KEY,platform TEXT,fingerprint TEXT UNIQUE,state TEXT,remote_id TEXT,body TEXT);
        CREATE TABLE IF NOT EXISTS packages(id TEXT PRIMARY KEY,body TEXT);
        CREATE TABLE IF NOT EXISTS chat_usage(job TEXT PRIMARY KEY,provider TEXT,model TEXT,input_tokens INTEGER,output_tokens INTEGER,reported REAL);
        CREATE TABLE IF NOT EXISTS video_workflows(id TEXT PRIMARY KEY,body TEXT,updated REAL);
        CREATE TABLE IF NOT EXISTS youtube_channels(id TEXT PRIMARY KEY,connection TEXT NOT NULL,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS studio_workflows(id TEXT PRIMARY KEY,body TEXT NOT NULL,updated REAL);
        CREATE TABLE IF NOT EXISTS studio_runs(id TEXT PRIMARY KEY,workflow TEXT NOT NULL,slot TEXT UNIQUE,body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS studio_files(workflow TEXT,path TEXT,signature TEXT,seen REAL,PRIMARY KEY(workflow,path));
        CREATE TABLE IF NOT EXISTS studio_uploads(channel TEXT,workflow TEXT,sha TEXT,override TEXT,run TEXT,project TEXT,operation TEXT,PRIMARY KEY(channel,workflow,sha,override));
        CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY,name TEXT);
        CREATE TABLE IF NOT EXISTS templates(id TEXT PRIMARY KEY,body TEXT);
        CREATE TABLE IF NOT EXISTS job_events(id INTEGER PRIMARY KEY AUTOINCREMENT,job TEXT,type TEXT,body TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS assistant_memory(id TEXT PRIMARY KEY,scope TEXT NOT NULL,body TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS assistant_memory_fts USING fts5(id UNINDEXED,scope UNINDEXED,text);
        CREATE TABLE IF NOT EXISTS whatsapp_messages(id TEXT PRIMARY KEY,chat TEXT,text TEXT,arrived REAL);
        CREATE TABLE IF NOT EXISTS assistant_reminders(id TEXT PRIMARY KEY,text TEXT,due REAL,state TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS agent_tasks(id TEXT PRIMARY KEY,body TEXT NOT NULL,updated REAL);
        CREATE TABLE IF NOT EXISTS agent_steps(task TEXT,step TEXT,state TEXT,payload TEXT,result TEXT,PRIMARY KEY(task,step));
        ''')
        c.execute('BEGIN IMMEDIATE')  # Serialize column inspection and migration across startup workers.
        columns={r[1] for r in c.execute('PRAGMA table_info(jobs)')}
        for name,kind in {'step':'TEXT','started':'REAL','finished':'REAL','error_code':'TEXT','request_key':'TEXT','retry_of':'TEXT','available':'REAL'}.items():
            if name not in columns: c.execute(f'ALTER TABLE jobs ADD COLUMN {name} {kind}')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS job_request_key ON jobs(request_key) WHERE request_key IS NOT NULL')
        c.execute('CREATE INDEX IF NOT EXISTS job_events_cursor ON job_events(job,id)')
        c.execute("UPDATE jobs SET state='waiting_for_approval' WHERE state='waiting-review'")
        c.execute("UPDATE jobs SET state='failed',error='Caption generation moved to ClipX. Open Caption Tool in Projects.',error_code='CAPTION_TOOL_REQUIRED',finished=? WHERE kind='transcribe' AND state IN ('queued','running')",(time.time(),))
    from . import youtube
    youtube.init()


def audit(event, body):
    with connect() as c:
        c.execute('INSERT INTO audit(event,body,created) VALUES(?,?,?)', (event, encode(body), time.time()))

def stopped():
    with connect() as c:
        row = c.execute("SELECT value FROM preferences WHERE key='stopped'").fetchone()
        return row is not None and row[0] == 'true'

def enqueue(c, project, kind, payload, request_key=None):
    row=c.execute("SELECT value FROM preferences WHERE key='stopped'").fetchone()
    if row and row[0]=='true':
        raise ValueError('Emergency stop is active')
    if request_key:
        existing=c.execute('SELECT * FROM jobs WHERE request_key=?',(request_key,)).fetchone()
        if existing:
            if existing['project']!=project or existing['kind']!=kind or existing['payload']!=encode(payload):
                raise ValueError('Request key already used for different inputs')
            return existing['id']
    id = uuid.uuid4().hex
    c.execute('INSERT INTO jobs(id,project,kind,payload,state,created,request_key,step) VALUES(?,?,?,?,?,?,?,?)', (id,project,kind,encode(payload),'queued',time.time(),request_key,'Waiting for worker'))
    c.execute('INSERT INTO job_events(job,type,body,created) VALUES(?,?,?,?)',(id,'queued',encode({'summary':'Task queued'}),time.time()))
    return id


def queue(project, kind, payload, request_key=None):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        id=enqueue(c,project,kind,payload,request_key)
    audit('job.queued', {'id':id, 'kind':kind})
    return id

def claim(lane='heavy'):
    if lane not in ('heavy','control'):raise ValueError('Unknown worker lane')
    lane_filter="kind='agent_turn'" if lane=='control' else "kind!='agent_turn'"
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        # Expired leases are retried at most twice; file outputs are deterministic per job.
        stale=c.execute("SELECT id,kind,cancel,attempts FROM jobs WHERE state='running' AND "+lane_filter+" AND (heartbeat IS NULL OR heartbeat<?)",(time.time()-60,)).fetchall()
        for old in stale:
            state='cancelled' if old['cancel'] else 'queued' if old['kind'] in ('probe','render','system_scan','youtube_execute','agent_turn') and old['attempts']<3 else 'failed'
            c.execute('UPDATE jobs SET state=?,error=?,error_code=?,finished=? WHERE id=?',(state,'Worker interrupted; retry safe work or use the integration recovery controls.','INTERRUPTED',None if state=='queued' else time.time(),old['id']))
            c.execute('INSERT INTO job_events(job,type,body,created) VALUES(?,?,?,?)',(old['id'],state,encode({'summary':'Worker interrupted; recovery policy applied'}),time.time()))
        if stopped():
            return None
        row = c.execute("SELECT * FROM jobs WHERE state='queued' AND cancel=0 AND (available IS NULL OR available<=?) AND "+lane_filter+" ORDER BY CASE WHEN kind='studio_steer' THEN 0 ELSE 1 END,created LIMIT 1",(time.time(),)).fetchone()
        if row:
            c.execute("UPDATE jobs SET state='running',attempts=attempts+1,heartbeat=?,started=COALESCE(started,?),finished=NULL,error=NULL,error_code=NULL,step='Starting task' WHERE id=?", (time.time(),time.time(),row['id']))
            c.execute('INSERT INTO job_events(job,type,body,created) VALUES(?,?,?,?)',(row['id'],'running',encode({'summary':'Worker started task'}),time.time()))
            return dict(row)|{'attempts':row['attempts']+1,'state':'running'}

def update_job(id, *, expected_attempt=None, **values):
    allowed = {'state','progress','error','result','heartbeat','cancel','step','started','finished','error_code','retry_of','available'}
    if not values.keys() <= allowed:
        raise ValueError('Invalid job update')
    with connect() as c:
        if values.get('state') in ('completed','failed','cancelled','waiting_for_approval'):
            values['finished']=time.time()
        result=c.execute('UPDATE jobs SET '+','.join(k+'=?' for k in values)+' WHERE id=?'+(" AND attempts=? AND state='running'" if expected_attempt is not None else ''), (*values.values(),id,*([expected_attempt] if expected_attempt is not None else [])))
        if expected_attempt is not None and result.rowcount!=1:raise ValueError('Job lease is no longer owned')
        if 'state' in values or 'step' in values:
            c.execute('INSERT INTO job_events(job,type,body,created) VALUES(?,?,?,?)',(id,values.get('state','step'),encode({'summary':values.get('step') or values.get('error') or values.get('state','Step updated')}),time.time()))


def event(job, kind, summary):
    with connect() as c:
        c.execute('INSERT INTO job_events(job,type,body,created) VALUES(?,?,?,?)',(job,kind,encode({'summary':summary}),time.time()))


def safe_error(error):
    import os
    from .config import TOKEN
    text=str(error)[-12000:]
    for secret in (TOKEN,os.getenv('CLOUD_API_KEY',''),os.getenv('NINJA_TOKEN','')):
        if len(secret)>=8:text=text.replace(secret,'[redacted]')
    return text

def cancel_jobs(c,id=None):
    rows=c.execute("SELECT id,state FROM jobs WHERE state IN ('queued','running','waiting_for_approval')"+(' AND id=?' if id else ''),(id,) if id else ()).fetchall()
    for row in rows:
        terminal=row['state']!='running'
        c.execute('UPDATE jobs SET cancel=1,state=?,finished=?,step=? WHERE id=?',('cancelled' if terminal else row['state'],time.time() if terminal else None,'Cancelled' if terminal else 'Cancellation requested',row['id']))
        c.execute('INSERT INTO job_events(job,type,body,created) VALUES(?,?,?,?)',(row['id'],'cancelled' if terminal else 'cancel_requested',encode({'summary':'Cancelled' if terminal else 'Cancellation requested'}),time.time()))


def cancelled(id):
    with connect() as c:
        row = c.execute('SELECT cancel FROM jobs WHERE id=?', (id,)).fetchone()
    return stopped() or not row or bool(row[0])

def project(id):
    with connect() as c:
        row = c.execute('SELECT body FROM projects WHERE id=?',(id,)).fetchone()
    if not row:
        raise ValueError('Project not found')
    return json.loads(row[0])

def save_project(id, body, expected=None):
    with connect() as c:
        if expected is None:
            c.execute('UPDATE projects SET body=? WHERE id=?',(encode(body),id))
        else:
            result=c.execute('UPDATE projects SET body=? WHERE id=? AND body=?',(encode(body),id,encode(expected)))
            if result.rowcount!=1: raise ValueError('Project changed concurrently; reload and retry')

def request_approval(action, params):
    id=uuid.uuid4().hex
    digest=hashlib.sha256(encode(params).encode()).hexdigest()
    with connect() as c:
        c.execute('INSERT INTO approvals VALUES(?,?,?,?,?)',(id,action,digest,'pending',time.time()))
    audit('approval.requested', {'id':id,'action':action,'params':params})
    return id

def consume_approval(id, action, params):
    digest=hashlib.sha256(encode(params).encode()).hexdigest()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM approvals WHERE id=?',(id,)).fetchone()
        if not row or row['state']!='approved' or row['action']!=action or row['digest']!=digest:
            raise ValueError('Approval absent, consumed, or parameters changed')
        c.execute("UPDATE approvals SET state='consumed' WHERE id=?",(id,))


def check_lease(job,attempt,c=None):
    if c is None:
        with connect() as connection:return check_lease(job,attempt,connection)
    row=c.execute('SELECT state,attempts,cancel FROM jobs WHERE id=?',(job,)).fetchone()
    if not row or row['state']!='running' or row['attempts']!=attempt:raise ValueError('Job lease is no longer owned')
    if row['cancel']:raise ValueError('Task cancelled')
