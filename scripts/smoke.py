"""Real HTTP handlers plus an independent worker, actual FFmpeg and existing-caption compatibility.
Run after generating data/sample.wav with scripts/make-sample.ps1.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['NINJA_DATA']=str(ROOT/'data'/'smoke')
os.environ['NINJA_TOKEN']='smoke-local-token'
os.environ['LANGCHAIN_TRACING_V2']='false'
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
from ninja.api import app
from ninja import db

def main():
    sample=ROOT/'data'/'sample.mp4'; wav=ROOT/'data'/'sample.wav'
    if not wav.exists(): raise SystemExit('Run scripts/make-sample.ps1 first')
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=25','-i',str(wav),'-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(sample)],check=True,timeout=60)
    db.init()
    log=(ROOT/'data'/'smoke-worker.log').open('w')
    worker=subprocess.Popen([sys.executable,'-m','ninja.worker'],cwd=ROOT/'backend',env=os.environ.copy(),stdout=log,stderr=log)
    headers={'X-Ninja-Token':'smoke-local-token'}
    try:
        with TestClient(app) as client:
            def request(route,body):
                r=client.post('/api'+route,json=body,headers=headers);r.raise_for_status();return r.json()
            def wait(id,timeout=600):
                start=time.monotonic()
                while time.monotonic()-start<timeout:
                    if worker.poll() is not None: raise RuntimeError('Worker exited; see smoke-worker.log')
                    job=next(j for j in client.get('/api/jobs',headers=headers).json() if j['id']==id)
                    if job['state'] in ('completed','waiting_for_approval'): return job
                    if job['state'] in ('failed','cancelled'): raise RuntimeError(job['error'])
                    time.sleep(.5)
                raise TimeoutError(id)
            with sample.open('rb') as f:
                r=client.post('/api/import/upload',files={'file':('sample.mp4',f,'video/mp4')},headers=headers);r.raise_for_status();p=r.json()
            wait(p['job']); id=p['id']
            project=client.get('/api/projects/'+id,headers=headers).json()
            edl=project['edl'];edl['captions']=[{'start':0,'end':2,'text':'Existing caption fixture','words':[]}]
            edl['clips']=[{'start':0,'end':min(6,project['metadata']['duration'])}]
            edl['captions'][0]['text']='Ninja Assistant: reviewed caption';edl['captions'][0]['words']=[]
            r=client.put(f'/api/projects/{id}/edl',json=edl,headers=headers);r.raise_for_status();revision=r.json()['edl']['revision']
            preview=wait(request(f'/projects/{id}/render',{'preview':True,'revision':revision})['job'])
            request(f'/projects/{id}/review',{'revision':revision})
            final=wait(request(f'/projects/{id}/render',{'preview':False,'revision':revision})['job'])
            for kind in ('srt','vtt','json'): assert client.get(f'/api/projects/{id}/captions/{kind}',headers=headers).status_code==200
            file=final['result']['file'];response=client.get(f'/api/projects/{id}/files/{file}',headers=headers)
            assert response.status_code==200 and len(response.content)>1000
            report={'project':id,'captions':len(edl['captions']),'preview':preview['result'],'final':final['result'],'download_bytes':len(response.content),'captions':'existing-caption compatibility fixture; generation delegated to ClipX','worker':'separate process'}
            (ROOT/'data'/'smoke-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    finally:
        worker.terminate();worker.wait(timeout=15);log.close()

if __name__=='__main__':main()
