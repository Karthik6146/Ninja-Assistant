import json
import os
import secrets
import shutil
import uuid
import copy
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from filelock import Timeout as LockTimeout
from . import db, media, workflow, content, tools
from .config import ROOT, DATA, ORIGINS, ROOTS, SESSIONS, approved_path, artifact, new_session, session_ok, token_ok
from . import youtube_auth
from .youtube_routes import router as youtube_router
from .workspace_routes import router as workspace_router
from .schemas import EDL, RenderRequest
from .assistant_routes import router as assistant_router

@asynccontextmanager
async def lifespan(app):
    from . import voice
    db.init()
    from . import whatsapp
    whatsapp.start()
    try:yield
    finally:
        from . import neural_voice,listener
        whatsapp.stop();voice.shutdown();neural_voice.shutdown();listener.shutdown()

app=FastAPI(title='Ninja Assistant',lifespan=lifespan)
app.include_router(assistant_router)
app.add_middleware(CORSMiddleware,allow_origins=ORIGINS,allow_methods=['GET','POST','PUT'],allow_headers=['Content-Type','X-Ninja-Token'],allow_credentials=True)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])

@app.middleware('http')
async def guard(request: Request, call_next):
    if request.url.path.startswith('/api'):
        origin=request.headers.get('origin')
        if origin and origin not in ORIGINS: return JSONResponse({'detail':'Origin denied'},403)
        if request.url.path!='/api/session' and not (token_ok(request.headers.get('x-ninja-token')) or session_ok(request.cookies.get('ninja_session'))):
            return JSONResponse({'detail':'Local access token required'},401)
        if request.method not in ('GET','HEAD','OPTIONS') and request.url.path!='/api/session':
            if not token_ok(request.headers.get('x-ninja-token')): return JSONResponse({'detail':'Mutation token required'},403)
            if db.stopped() and request.url.path!='/api/emergency': return JSONResponse({'detail':'Emergency stop active'},409)
    return await call_next(request)

@app.middleware('http')
async def headers(request: Request, call_next):
    response=await call_next(request)
    response.headers.setdefault('X-Content-Type-Options','nosniff')
    response.headers.setdefault('X-Frame-Options','DENY')
    response.headers.setdefault('Referrer-Policy','no-referrer')
    return response

@app.exception_handler(ValueError)
async def invalid(request,exc): return JSONResponse({'detail':db.safe_error(exc),'error':{'code':'INVALID_REQUEST','message':db.safe_error(exc)}},400)

@app.exception_handler(LockTimeout)
async def locked(request,exc):return JSONResponse({'detail':'This workflow or local model is busy. Wait for its active task or cancel it before retrying.'},409)

class Session(BaseModel): token: str
@app.post('/api/session')
def session(body: Session):
    if not token_ok(body.token): raise HTTPException(401,'Invalid token')
    response=JSONResponse({'connected':True})
    response.set_cookie('ninja_session',new_session(),httponly=True,samesite='strict',max_age=86400)
    return response

@app.post('/api/session/logout')
def logout(request: Request):
    SESSIONS.pop(request.cookies.get('ninja_session',''),None)
    response=JSONResponse({'connected':False})
    response.delete_cookie('ninja_session')
    return response

@app.get('/api/status')
def status():
    return {'stopped':db.stopped(),'ffmpeg':bool(shutil.which('ffmpeg')),'ffprobe':bool(shutil.which('ffprobe')),'ollama':'configured' if os.getenv('OLLAMA_MODEL') else 'disconnected','cloud':'enabled' if os.getenv('CLOUD_ENABLED')=='true' else 'disabled','youtube':'connected' if youtube_auth.status()['connected'] else 'disconnected','instagram':'disconnected','threads':'disconnected','search':'disconnected','roots':[str(r) for r in ROOTS],'timezone':'Asia/Kolkata','caption_generation':'external-tool'}

@app.get('/api/projects')
def projects():
    with db.connect() as c: return [dict(r)|{'body':json.loads(r['body'])} for r in c.execute('SELECT * FROM projects ORDER BY created DESC')]

@app.get('/api/projects/{id}')
def get_project(id: str): return db.project(id)

def create_project(id,name,source):
    import time
    body={'id':id,'name':name,'source':source,'metadata':None,'edl':None,'suggestions':[]}
    with db.connect() as c: c.execute('INSERT INTO projects VALUES(?,?,?,?)',(id,name,db.encode(body),time.time()))
    return {'id':id,'job':db.queue(id,'probe',{})}

ALLOWED={'.mp4','.mov','.mkv','.webm','.avi','.m4v'}
@app.post('/api/import/upload')
async def upload(file: UploadFile):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in ALLOWED: raise ValueError('Unsupported video extension')
    id=uuid.uuid4().hex; destination=artifact(id,'source'+suffix); destination.parent.mkdir(parents=True)
    count=0
    try:
        with destination.open('wb') as output:
            while chunk:=await file.read(1024*1024):
                count+=len(chunk)
                if count>4*1024**3: raise ValueError('Upload exceeds 4 GB limit')
                if shutil.disk_usage(destination.parent).free<100_000_000+len(chunk): raise ValueError('Insufficient disk space')
                output.write(chunk)
        return create_project(id,Path(file.filename).name,destination.name)
    except Exception:
        destination.unlink(missing_ok=True); raise
    finally: await file.close()

class LocalImport(BaseModel): path: str
@app.post('/api/import/path')
def local_import(body: LocalImport):
    source=approved_path(body.path)
    if source.suffix.lower() not in ALLOWED: raise ValueError('Unsupported video extension')
    if source.stat().st_size>4*1024**3: raise ValueError('Import exceeds 4 GB limit')
    if shutil.disk_usage(DATA).free<source.stat().st_size+100_000_000: raise ValueError('Insufficient disk space')
    id=uuid.uuid4().hex; destination=artifact(id,'source'+source.suffix.lower()); destination.parent.mkdir(parents=True)
    shutil.copyfile(source,destination)
    return create_project(id,source.name,destination.name)

@app.put('/api/projects/{id}/edl')
def edit(id: str,edl: EDL):
    p=db.project(id)
    original=copy.deepcopy(p)
    if not p['metadata']: raise ValueError('Inspection is pending')
    if edl.revision!=p['edl']['revision']: raise HTTPException(409,'Edits changed; reload project')
    if any(c.end>p['metadata']['duration']+.01 for c in edl.clips) or any(c.end>p['metadata']['duration']+.01 for c in edl.captions): raise ValueError('Timing exceeds source duration')
    if edl.music and edl.music!=p.get('music'): raise ValueError('Use the project music upload')
    edl.revision+=1; p['edl']=edl.model_dump(); p.pop('reviewed_revision',None)
    artifact(id,f'edl-v{edl.revision}.json').write_text(db.encode(p['edl']),encoding='utf-8')
    db.save_project(id,p,expected=original); workflow.begin(id,edl.revision)
    db.audit('edl.saved',{'project':id,'revision':edl.revision})
    return p

@app.post('/api/projects/{id}/review')
def review(id: str,body: dict):
    p=db.project(id); original=copy.deepcopy(p); revision=body.get('revision')
    if not p['edl'] or revision!=p['edl']['revision']: raise ValueError('Stale review')
    result=workflow.resume(id,revision)
    if result.get('reviewed_revision')!=revision: raise ValueError('Workflow review failed')
    p['reviewed_revision']=revision; db.save_project(id,p,expected=original)
    with db.connect() as c: c.execute("UPDATE jobs SET state='completed' WHERE project=? AND state='waiting_for_approval'",(id,))
    return {'reviewed_revision':revision}

@app.post('/api/projects/{id}/render')
def render(id: str,body: RenderRequest):
    p=db.project(id)
    if not p['edl'] or body.revision!=p['edl']['revision']: raise ValueError('Save current edits first')
    if not body.preview:
        if p.get('reviewed_revision')!=body.revision: raise ValueError('Review exact edits first')
        with db.connect() as c:
            rows=c.execute("SELECT result FROM jobs WHERE project=? AND kind='render' AND state='completed'",(id,)).fetchall()
        if not any(json.loads(r[0])['revision']==body.revision and json.loads(r[0])['preview'] for r in rows): raise ValueError('Generate current revision preview first')
    return {'job':db.queue(id,'render',body.model_dump()|{'edl':p['edl']})}

@app.post('/api/projects/{id}/music')
async def music(id: str,file: UploadFile):
    p=db.project(id); original=copy.deepcopy(p); suffix=Path(file.filename or '').suffix.lower()
    if suffix not in {'.wav','.mp3','.m4a','.ogg'}: raise ValueError('Unsupported music format')
    name='music-'+uuid.uuid4().hex+suffix; destination=artifact(id,name); count=0
    try:
        with destination.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                count+=len(chunk)
                if count>100_000_000: raise ValueError('Music exceeds 100 MB')
                out.write(chunk)
        p['music']=name; db.save_project(id,p,expected=original)
        return {'file':name}
    except Exception:
        destination.unlink(missing_ok=True); raise
    finally: await file.close()

@app.get('/api/projects/{id}/captions/{kind}')
def export(id: str,kind: str):
    if kind not in ('srt','vtt','json'): raise ValueError('Unsupported format')
    p=db.project(id)
    return Response(media.caption_export(p['edl']['captions'],kind),media_type='text/plain; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="captions.{kind}"'})

@app.get('/api/projects/{id}/files/{name}')
def file(id: str,name: str):
    p=db.project(id)
    with db.connect() as c: rows=c.execute("SELECT result FROM jobs WHERE project=? AND kind='render' AND state='completed'",(id,)).fetchall()
    allowed={p['source']}|{json.loads(r[0])['file'] for r in rows}
    if name not in allowed: raise HTTPException(404,'Artifact unavailable')
    path=artifact(id,name)
    if not path.is_file(): raise HTTPException(404,'Artifact missing')
    return FileResponse(path,media_type='video/mp4' if name.endswith('.mp4') else None)

@app.get('/api/jobs')
def jobs():
    with db.connect() as c:
        return [dict(r)|{'payload':json.loads(r['payload']),'result':json.loads(r['result']) if r['result'] else None} for r in c.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 200')]

@app.post('/api/jobs/{id}/cancel')
def cancel(id: str):
    with db.connect() as c:
        db.cancel_jobs(c,id)
    db.audit('job.cancelled',{'id':id}); return {'requested':True}

@app.post('/api/emergency')
def emergency(body: dict):
    value=bool(body.get('stopped',True))
    with db.connect() as c:
        c.execute("INSERT OR REPLACE INTO preferences VALUES('stopped',?)",('true' if value else 'false',))
        if value: db.cancel_jobs(c)
    db.audit('emergency',{'stopped':value}); return {'stopped':value}

@app.get('/api/system')
def system():
    return tools.invoke('system.monitor',{},granted={'system.read'})

class ScanRequest(BaseModel): root: str
@app.post('/api/system/large-files')
def scan_files(body: ScanRequest):
    root=Path(body.root).resolve(strict=True)
    if root not in ROOTS or not root.is_dir():raise ValueError('Select a configured folder')
    return {'job':db.queue('system','system_scan',{'root':str(root)})}

class LogRequest(BaseModel): path: str
@app.post('/api/system/log')
def read_log(body: LogRequest):
    path=approved_path(body.path)
    if path.suffix.lower() not in ('.log','.txt'):raise ValueError('Only .log and .txt files are supported')
    with path.open('rb') as file:
        file.seek(0,2);size=file.tell();file.seek(max(0,size-32000));tail=file.read(32000).decode('utf-8',errors='replace')
    return {'path':str(path),'tail':'\n'.join(tail.splitlines()[-200:]),'truncated':size>32000}

@app.get('/api/encoders')
def encoders():
    output=media.run(['ffmpeg','-hide_banner','-encoders'],timeout=10)
    return {'encoders':[e for e in ('libx264','h264_nvenc','h264_qsv','h264_amf') if e in output],'note':'Listed hardware encoders may lack a usable device. Render falls back to CPU.'}

@app.get('/api/research/{id}')
def report(id: str):
    if not id.isalnum(): raise ValueError('Invalid report ID')
    path=DATA/'research'/f'{id}.md'
    if not path.is_file(): raise HTTPException(404)
    return FileResponse(path,filename='research.md')

@app.get('/api/approvals')
def approvals():
    with db.connect() as c: return [dict(r) for r in c.execute('SELECT * FROM approvals ORDER BY created DESC')]

@app.get('/api/audit')
def audit():
    with db.connect() as c: return [dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]

class NewPackage(BaseModel): project: str
@app.post('/api/packages')
def new_package(body: NewPackage):return content.create(body.project)

@app.get('/api/packages')
def packages():
    with db.connect() as c:ids=[r[0] for r in c.execute('SELECT id FROM packages')]
    return [content.load(id) for id in ids]

@app.get('/api/packages/{id}')
def get_package(id: str):
    body=content.load(id)
    return {'package':body,'outputs':content.outputs(body),'capabilities':{'publishing':True,'analytics':True,'accounts':'youtube-oauth','schedule_execution':'youtube-after-approval'}}

@app.put('/api/packages/{id}/draft')
def edit_draft(id: str,body:content.Draft):return content.edit_draft(id,body)

@app.post('/api/packages/{id}/review/{platform}')
def review_draft(id: str,platform: str,body: dict):return content.review(id,platform,body.get('revision'))

class Manifest(BaseModel):
    revision: int
    scenes: list[content.Scene]=Field(max_length=100)
    rights: str=Field(pattern='^(unknown|owned|licensed)$')
@app.put('/api/packages/{id}/manifest')
def edit_manifest(id: str,body: Manifest):return content.scenes(id,body.revision,[s.model_dump() for s in body.scenes],body.rights)

@app.get('/api/packages/{id}/export')
def export_package(id: str):
    body=content.load(id)
    return Response(json.dumps(body,ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="content-package.json"'})

app.include_router(youtube_router)
app.include_router(workspace_router)
from .video_routes import router as video_router
app.include_router(video_router)
from .studio_routes import router as studio_router
app.include_router(studio_router)

from .media_library import router as library_router
app.include_router(library_router)

from .assistant_desk import router as assistant_router
app.include_router(assistant_router)

dist=ROOT/'frontend'/'dist'
if dist.exists(): app.mount('/',StaticFiles(directory=dist,html=True),name='dashboard')
