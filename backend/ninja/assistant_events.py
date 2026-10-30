"""Local reminders, claimed atomically; no unsolicited external messages."""
import time,uuid
from . import db

def add(text,due,key,context=None):
    if not text.strip() or len(text)>200:raise ValueError('Reminder needs 1–200 characters')
    if not 0<due<time.time()+366*86400:raise ValueError('Choose a reminder within the next year')
    id=uuid.uuid5(uuid.NAMESPACE_URL,key).hex
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if context is not None:
            from .permissions import check_write
            check_write(c,'assistant.remind',context)
        old=c.execute('SELECT * FROM assistant_reminders WHERE id=?',(id,)).fetchone()
        if old:
            if old['text']!=text or abs(old['due']-due)>.001:raise ValueError('Reminder key used for different inputs')
            return dict(old)
        c.execute('INSERT INTO assistant_reminders VALUES(?,?,?,?,?)',(id,text,due,'scheduled',time.time()))
    return {'id':id,'text':text,'due':due,'state':'scheduled'}

def listing():
    with db.connect() as c:return [dict(r) for r in c.execute("SELECT * FROM assistant_reminders WHERE state!='dismissed' ORDER BY due LIMIT 50")]

def tick(now=None):
    now=time.time() if now is None else now
    if db.stopped():return []
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        due=[r[0] for r in c.execute("SELECT id FROM assistant_reminders WHERE state='scheduled' AND due<=?",(now,))]
        c.execute("UPDATE assistant_reminders SET state='due' WHERE state='scheduled' AND due<=?",(now,))
    return due

def dismiss(id):
    with db.connect() as c:c.execute("UPDATE assistant_reminders SET state='dismissed' WHERE id=?",(id,))
    return {'dismissed':id}

