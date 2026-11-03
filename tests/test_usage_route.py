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
    assert value['day'][-1]['replies']>=2
    qwen=[m for m in value['models'] if m['model']=='qwen'][0]
    assert qwen['provider']=='ollama' and qwen['replies']>=2 and qwen['input']>=100

def test_model_info_measures_speed_from_recent_turns(monkeypatch):
    from ninja import adapters
    monkeypatch.setattr(adapters,'provider_status',lambda:[{'models':['speed-test']}])
    monkeypatch.setattr(adapters,'ollama_url',lambda:'http://127.0.0.1:9')
    with db.connect() as c:
        c.execute("INSERT OR REPLACE INTO jobs(id,project,kind,state) VALUES('s1','t-speed','agent_turn','completed')")
        c.execute('INSERT OR REPLACE INTO chat_usage VALUES(?,?,?,?,?,?)',('s1','ollama','speed-test',3000,90,time.time()))
        for n,(out,gen) in enumerate([(40,1.0),(50,1.5)]):
            c.execute('INSERT OR REPLACE INTO agent_steps VALUES(?,?,?,?,?)',('t-speed',f'model:s1:{n}','completed','{}',db.encode({'usage':{'input_tokens':1500,'output_tokens':out},'timing':{'generation_seconds':gen,'prompt_seconds':0.5,'model_seconds':2}})))
    info=assistant_routes.model_info('speed-test')
    assert info['speed']=={'turns':2,'output_per_second':36.0,'prompt_per_second':3000.0,'first_text_seconds':None,'turn_seconds':2.0,'load_seconds':None}
    assert info['loaded'] is None and info['details']=={}

def test_unload_refuses_while_the_model_is_busy(monkeypatch):
    import pytest
    from filelock import FileLock
    from ninja import adapters
    from ninja.config import DATA
    monkeypatch.setattr(adapters,'provider_status',lambda:[{'models':['speed-test']}])
    with pytest.raises(ValueError,match='installed'):assistant_routes.unload_model(assistant_routes.Unload(model='other'))
    with FileLock(DATA/'model.lock'):
        with pytest.raises(ValueError,match='busy'):assistant_routes.unload_model(assistant_routes.Unload(model='speed-test'))
