import json
import httpx
import pytest
from ninja import adapters,assistant_routes,db

CLOUD={'CLOUD_ENABLED':'true','CLOUD_URL':'https://api.example.test/v1','CLOUD_MODEL':'gpt-test','CLOUD_API_KEY':'test-key'}

def test_history_converts_to_openai_tool_format():
    out=adapters.openai_messages([
        {'role':'user','content':'pause'},
        {'role':'assistant','content':'','tool_calls':[{'function':{'name':'media.control','arguments':{'action':'pause'}}},{'function':{'name':'note.add','arguments':{}}}]},
        {'role':'tool','tool_name':'media.control','content':'{"verified":true}'},
        {'role':'assistant','content':'Paused.'},
        {'role':'tool','tool_name':'web.open','content':'late'}])
    assert out[1]['tool_calls'][0]['function']=={'name':'media__control','arguments':'{"action": "pause"}'}
    assert len(out[1]['tool_calls'])==1  # the unanswered note.add call is dropped
    assert out[2]=={'role':'tool','tool_call_id':out[1]['tool_calls'][0]['id'],'content':'{"verified":true}'}
    assert out[4]['role']=='user' and out[4]['content'].startswith('Result of web.open')

def test_cloud_turn_maps_tool_names_and_usage(monkeypatch):
    for k,v in CLOUD.items():monkeypatch.setenv(k,v)
    sent={}
    def post(url,headers,json,timeout):
        sent.update(url=url,body=json)
        return httpx.Response(200,request=httpx.Request('POST',url),json={'choices':[{'message':{'content':'','tool_calls':[{'id':'c1','function':{'name':'media__play','arguments':'{"query":"Mine"}'}}]}}],'usage':{'prompt_tokens':50,'completion_tokens':7}})
    monkeypatch.setattr(adapters.httpx,'post',post)
    answer=adapters.cloud_turn([{'role':'user','content':'play Mine'}],[{'type':'function','function':{'name':'media.play','parameters':{}}}],256)
    assert sent['url']=='https://api.example.test/v1/chat/completions' and sent['body']['tools'][0]['function']['name']=='media__play'
    assert answer.calls[0].name=='media.play' and answer.calls[0].arguments=={'query':'Mine'}
    assert answer.usage=={'input_tokens':50,'output_tokens':7}

def test_cloud_choice_needs_env_and_falls_back(monkeypatch):
    monkeypatch.delenv('CLOUD_ENABLED',raising=False)
    with pytest.raises(ValueError):assistant_routes.choose_model(assistant_routes.ModelChoice(provider='cloud'))
    with db.connect() as c:c.execute("INSERT OR REPLACE INTO preferences VALUES('chat_provider','cloud')")
    assert adapters.chat_provider()=='ollama'  # .env no longer configures cloud
    for k,v in CLOUD.items():monkeypatch.setenv(k,v)
    assert adapters.chat_provider()=='cloud' and adapters.chat_model()=='gpt-test'
