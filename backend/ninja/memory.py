"""Local factual memory with exact provenance and scope-filtered FTS retrieval."""
import json,re,time,uuid
from . import db
from .agent_models import Scope
SECRET=re.compile(r'password|api[ _-]?key|access[ _-]?token|client[ _-]?secret|private[ _-]?key|bearer\s',re.I)
SENSITIVE=re.compile(r'bank account|credit card|aadhar|aadhaar|passport|aadhar|aadhaar|ssn|social security|\bcard\b|\bpin\b|\bdiagnos|medical|health record|\bhiv\b|\bcancer\b|sexual|patient record',re.I)

def validate(text):
    text=text.strip()
    if not text or len(text)>2000:raise ValueError('Memory must contain 1–2000 characters')
    if SECRET.search(text):raise ValueError('Keep credentials in the vault, not searchable memory')
    if SENSITIVE.search(text) or re.search(r'(?:\d[ -]?){8,}',text):raise ValueError('This sensitive record needs protected storage and explicit confirmation; searchable memory cannot retain it')
    return text

def key(scope):return scope.kind+':'+scope.id
def index(c,value):
    c.execute('DELETE FROM assistant_memory_fts WHERE id=?',(value['id'],))
    c.execute('INSERT INTO assistant_memory_fts(id,scope,text) VALUES(?,?,?)',(value['id'],key(Scope(**value['scope'])),value['text']))

def remember(text,scope,*,source='',quotation='',context=None):
    text=validate(text);now=time.time()
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if context is not None:
            from .permissions import check_write
            check_write(c,'memory.remember',context)
        for row in c.execute('SELECT body FROM assistant_memory WHERE scope=?',(key(scope),)):
            old=json.loads(row[0])
            if old['text']==text:return old
        value={'id':uuid.uuid4().hex,'text':text,'scope':scope.model_dump(),'source':source,'quotation':quotation or text,'explicit':True,'confidence':1,'revision':0,'created':now,'updated':now}
        c.execute('INSERT INTO assistant_memory VALUES(?,?,?)',(value['id'],key(scope),db.encode(value)));index(c,value)
    return value

def listing(scopes):
    keys=[key(s) for s in scopes]
    if not keys:return []
    with db.connect() as c:return [json.loads(r[0]) for r in c.execute('SELECT body FROM assistant_memory WHERE scope IN ('+','.join('?' for _ in keys)+') ORDER BY rowid DESC',keys)]

def search(query,scopes,limit=5):
    words=re.findall(r'[^\W_]+',query,re.UNICODE)[:20];keys=[key(s) for s in scopes]
    if not words or not keys:return []
    match=' OR '.join('"'+w+'"' for w in words)
    with db.connect() as c:
        rows=c.execute('SELECT m.body FROM assistant_memory_fts f JOIN assistant_memory m ON m.id=f.id WHERE assistant_memory_fts MATCH ? AND m.scope IN ('+','.join('?' for _ in keys)+') ORDER BY bm25(assistant_memory_fts) LIMIT ?',(match,*keys,min(max(limit,1),10))).fetchall()
    return [json.loads(r[0]) for r in rows]

def correct(id,text,revision):
    text=validate(text)
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT body FROM assistant_memory WHERE id=?',(id,)).fetchone()
        if not row:raise ValueError('Memory not found')
        value=json.loads(row[0])
        if value['revision']!=revision:raise ValueError('Memory changed; reload before correcting')
        value['text']=text;value['revision']+=1;value['updated']=time.time()
        c.execute('UPDATE assistant_memory SET body=? WHERE id=?',(db.encode(value),id));index(c,value)
    return value

def forget(id):
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('DELETE FROM assistant_memory_fts WHERE id=?',(id,))
        c.execute('DELETE FROM assistant_memory WHERE id=?',(id,))
    return {'forgotten':id,'archive_notice':'Source tasks/chat and backups are separate records; remove those explicitly when needed.'}

def context(query,scopes,budget=1500):
    remaining=budget*4;result=[]
    for value in search(query,scopes):
        if len(value['text'])>remaining:continue
        compact={'id':value['id'],'text':value['text'],'scope':value['scope'],'source':value['source'],'revision':value['revision']}
        encoded=len(db.encode(compact))
        if encoded>remaining:continue
        result.append(compact);remaining-=encoded
    return result

