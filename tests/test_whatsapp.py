import sqlite3,time
from ninja import whatsapp

def toast(title,*lines):
    texts=''.join('<text>'+t+'</text>' for t in (title,*lines))
    return '<toast><visual><binding template="ToastGeneric">'+texts+'</binding></visual></toast>'

def fake_store(path,rows):
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE NotificationHandler(RecordId INTEGER,PrimaryId TEXT)')
        c.execute('CREATE TABLE Notification(HandlerId INTEGER,Type TEXT,Payload BLOB,ArrivalTime INTEGER)')
        c.executemany('INSERT INTO NotificationHandler VALUES(?,?)',[(1,'5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App'),(2,'Google.Play.Games')])
        c.executemany('INSERT INTO Notification VALUES(?,?,?,?)',rows)

def now_filetime():
    return int((time.time()+11644473600)*10_000_000)

def test_poll_copies_only_whatsapp_text_toasts_once(tmp_path,monkeypatch):
    path=tmp_path/'wpndatabase.db'
    fake_store(path,[(1,'toast',toast('Rahul','Kal milte hain').encode(),now_filetime()),
                     (1,'tile',toast('ignored','tile'),now_filetime()),
                     (2,'toast',toast('Game','Not WhatsApp'),now_filetime()),
                     (1,'toast','<toast>broken',now_filetime())])
    monkeypatch.setattr(whatsapp,'SOURCE',path)
    assert whatsapp.poll(path)==1 and whatsapp.poll(path)==0
    found=whatsapp.recent('rahul',24,10)
    assert [m['text'] for m in found['messages']]==['Kal milte hain'] and found['note']==whatsapp.UNTRUSTED
    assert whatsapp.recent('nobody',24,10)['messages']==[]

def test_parse_needs_a_title_and_text():
    assert whatsapp.parse(toast('Family','Mom: Khana kha liya?'))==('Family','Mom: Khana kha liya?')
    assert whatsapp.parse(toast('Only title')) is None and whatsapp.parse('x'*20001) is None
