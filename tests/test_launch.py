import os,secrets,time
from fastapi.testclient import TestClient
from ninja.api import app
from ninja.config import DATA

def test_launch_code_signs_in_once_and_expires():
    code=secrets.token_urlsafe(32)
    with TestClient(app) as client:
        (DATA/'launch-code').write_text(code,encoding='utf-8')
        first=client.post('/api/launch',json={'code':code})
        assert first.status_code==200 and first.json()['token']=='test-token' and 'ninja_session' in first.cookies
        assert client.post('/api/launch',json={'code':code}).status_code==401  # single use
        (DATA/'launch-code').write_text(code,encoding='utf-8')
        assert client.post('/api/launch',json={'code':'wrong'}).status_code==401
        assert not (DATA/'launch-code').exists()  # a wrong guess burns the code too
        (DATA/'launch-code').write_text(code,encoding='utf-8')
        old=time.time()-300;os.utime(DATA/'launch-code',(old,old))
        assert client.post('/api/launch',json={'code':code}).status_code==401
