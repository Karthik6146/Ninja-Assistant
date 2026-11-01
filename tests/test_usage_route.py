import time
from ninja import assistant_routes,db

def test_usage_groups_by_day_and_month():
    with db.connect() as c:
        c.execute('INSERT OR REPLACE INTO chat_usage VALUES(?,?,?,?,?,?)',('u1','ollama','qwen',100,20,time.time()))
        c.execute('INSERT OR REPLACE INTO chat_usage VALUES(?,?,?,?,?,?)',('u2','ollama','qwen',None,5,time.time()))
    value=assistant_routes.usage()
    assert len(value['day'])==30 and len(value['month'])==12
    assert value['day'][-1]['input']>=100 and value['day'][-1]['output']>=25
    assert value['month'][-1]['input']>=100 and value['day'][0]['period']<value['day'][-1]['period']
