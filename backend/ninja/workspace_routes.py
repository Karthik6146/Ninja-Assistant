import asyncio
import json
import time
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from . import adapters, db, tools, workspace as ws
from .config import DATA, ROOTS

router=APIRouter()


@router.get('/api/providers')
def providers():return adapters.provider_status()


class ModelSelection(BaseModel):
    model: str=Field(min_length=1,max_length=200)


@router.put('/api/providers/ollama')
def select_model(body:ModelSelection):
    if body.model not in adapters.provider_status()[0]['models']:raise ValueError('Choose an installed model; start Ollama if the list is empty')
    with db.connect() as c:c.execute("INSERT OR REPLACE INTO preferences VALUES('ollama_model',?)",(body.model,))
    return {'model':body.model}


@router.get('/api/workspaces')
def workspaces():
    with db.connect() as c:return [dict(r) for r in c.execute('SELECT * FROM workspaces ORDER BY name')]


class Name(BaseModel):
    name: str=Field(min_length=1,max_length=100)


@router.post('/api/workspaces')
def new_workspace(body:Name):
    id=uuid.uuid4().hex
    with db.connect() as c:c.execute('INSERT INTO workspaces VALUES(?,?)',(id,body.name))
    return {'id':id,'name':body.name}


@router.get('/api/tasks/{id}')
def task(id:str):return ws.task(id)


@router.get('/api/tasks/{id}/stream')
async def stream(id:str,request:Request):
    await asyncio.to_thread(ws.task,id)
    async def events():
        previous=None
        for _ in range(60):
            if await request.is_disconnected():break
            value=await asyncio.to_thread(ws.task,id)
            encoded=db.encode(value)
            if encoded!=previous:
                cursor=value['events'][-1]['id'] if value['events'] else 0
                yield f'id: {cursor}\ndata: {encoded}\n\n'
                previous=encoded
            else:yield ': keepalive\n\n'
            if value['state'] in ('completed','failed','cancelled','waiting_for_approval'):break
            await asyncio.sleep(.5)
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


class Retry(BaseModel):request_key:str=Field(min_length=8,max_length=100,pattern=r'^[\w-]+$')


@router.post('/api/tasks/{id}/retry')
def retry(id:str,body:Retry):return ws.retry(id,body.request_key)


@router.get('/api/tasks/{id}/output')
def output(id:str):
    task=ws.task(id)
    if task['state']!='completed' or task['kind']!='automation':raise ValueError('No completed report is available for this task')
    if not all(ch in 'abcdef0123456789' for ch in id) or len(id)!=32:raise ValueError('Invalid task ID')
    path=DATA/'outputs'/(id+'.md')
    if not path.is_file():raise ValueError('Report file is missing; the task result remains in Activity')
    return FileResponse(path,media_type='text/markdown',filename='ninja-report.md')


@router.get('/api/templates')
def templates():
    with db.connect() as c:return [dict(id=r['id'],**json.loads(r['body'])) for r in c.execute('SELECT * FROM templates')]


@router.get('/api/files')
def files():
    import re
    items=[]
    with db.connect() as c:
        projects=[json.loads(r[0]) for r in c.execute('SELECT body FROM projects')]
        outputs=c.execute("SELECT id,project,kind,result FROM jobs WHERE state='completed' AND result IS NOT NULL AND kind IN ('render','automation') ORDER BY created DESC LIMIT 500").fetchall()
    for project in projects:
        id=project['id']
        items.append({'name':project['name'],'kind':'Original video','url':f"/api/projects/{id}/files/{project['source']}"})
        if project.get('edl',{}):
            items.append({'name':project['name']+' captions','kind':'Current SRT','url':f'/api/projects/{id}/captions/srt'})
    for row in outputs:
        result=json.loads(row['result'])
        url=result.get('download') if row['kind']=='automation' else f"/api/projects/{row['project']}/files/{result['file']}"
        if url:items.append({'name':result.get('title') or result.get('file') or row['kind'],'kind':'Report' if row['kind']=='automation' else 'Rendered video','url':url,'task':row['id']})
    # Historical source notebooks remain downloadable after their old creation UI is retired.
    for path in sorted((DATA/'research').glob('*.md'))[-500:]:
        if re.fullmatch(r'[a-f0-9]{32}',path.stem):items.append({'name':'Source notebook '+path.stem[:8],'kind':'Legacy report','url':'/api/research/'+path.stem})
    return items


@router.post('/api/templates')
def create_template(body:ws.Template):
    id=uuid.uuid4().hex
    with db.connect() as c:c.execute('INSERT INTO templates VALUES(?,?)',(id,db.encode(body.model_dump())))
    return {'id':id,**body.model_dump()}


@router.put('/api/templates/{id}')
def edit_template(id:str,body:ws.Template):
    with db.connect() as c:
        if c.execute('UPDATE templates SET body=? WHERE id=?',(db.encode(body.model_dump()),id)).rowcount!=1:raise ValueError('Template not found')
    return {'id':id,**body.model_dump()}


class Run(Retry):
    template:ws.Template
    allow_cloud:bool=False


@router.post('/api/automations/run')
def run(body:Run):
    if body.template.kind!='diagnostics' and body.template.provider=='cloud' and not body.allow_cloud:raise ValueError('Explicit cloud sharing permission is required for this run')
    return {'job':db.queue(body.template.workspace or 'automations','automation',body.model_dump(exclude={'request_key'}),body.request_key)}


class CaptionConnection(BaseModel):
    url:str=Field(default='',max_length=1000)
    path:str=Field(default='',max_length=1000)


@router.get('/api/integrations')
def integrations():
    import shutil
    return {'caption':ws.caption_connection(),'tools':[{'name':t.name,'permission':t.permission,'timeout':t.timeout,'input_schema':t.input_schema.model_json_schema(),'output_schema':t.output_schema.model_json_schema()} for t in tools.REGISTRY.values()],
            'dependencies':{key:bool(shutil.which(key)) for key in ('ffmpeg','ffprobe','git')},
            'optional':[{'name':'Browser automation','status':'Not configured','capabilities':[],'message':'No browser automation runtime installed. Browser Use is a reference only.'},
                        {'name':'MCP','status':'Not configured','capabilities':[],'message':'No MCP server is connected; remote tools are not executed.'}],
            'roots':[str(p) for p in ROOTS]}


@router.put('/api/integrations/caption')
def caption(body:CaptionConnection):return ws.caption_connection(body.model_dump())
