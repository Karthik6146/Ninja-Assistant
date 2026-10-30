"""Launch the built dashboard on a temporary localhost port and verify real HTTP."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1]
with socket.socket() as s:
    s.bind(('127.0.0.1',0));port=s.getsockname()[1]
env=os.environ.copy();env['NINJA_DATA']=str(root/'data'/'http-smoke');env['NINJA_TOKEN']='http-smoke-only'
with (root/'data'/'http-smoke.log').open('w') as log:
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','ninja.api:app','--host','127.0.0.1','--port',str(port)],cwd=root/'backend',env=env,stdout=log,stderr=log)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=10) as client:
            for _ in range(50):
                try:
                    r=client.get('/');break
                except httpx.ConnectError:
                    if proc.poll() is not None:raise RuntimeError('API failed; see http-smoke.log')
                    time.sleep(.2)
            else:raise RuntimeError('API did not start')
            assert r.status_code==200 and 'Ninja Assistant' in r.text
            assert client.get('/api/projects').status_code==401
            assert client.post('/api/session',json={'token':'wrong'}).status_code==401
            assert client.post('/api/session',json={'token':'http-smoke-only'}).status_code==200
            assert client.get('/api/status').json()['ffmpeg']
            for file in (root/'frontend'/'dist'/'assets').iterdir():
                assert client.get('/assets/'+file.name).status_code==200
            print('PASS: real localhost API, dashboard/assets, token login, authenticated status')
    finally:
        proc.terminate();proc.wait(timeout=10)
