import json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import Field
from . import db,video,video_sources as sources,youtube_auth
from .video_models import Strict,VideoRequest,EditPlan

router=APIRouter(prefix='/api/video')
from .video_publish import Policy

@router.put('/workflows/{id}/publish-policy')
def policy(id:str,body:Policy):
    from .video_publish import policy
    return policy(id,body)

@router.get('/workflows')
def listing():return [{'id':v['id'],'name':v['name'],'revision':v['revision']} for v in video.listing()]

@router.post('/workflows')
def create(body:VideoRequest):return video.create(body)

@router.get('/workflows/{id}')
def get(id:str):
    value=video.get(id)
    # A killed worker may not have reached its exception handler. Surface its durable job state.
    with db.connect() as c:
        for stage in value['stages'].values():
            if stage['state']=='running':
                row=c.execute('SELECT state,error FROM jobs WHERE id=?',(stage['job'],)).fetchone()
                if row and row['state'] in ('failed','cancelled'):stage.update(state=row['state'],error=row['error'])
    value['assets']=[{k:v for k,v in asset.items() if k not in ('transcript','evidence','path')} for asset in value['assets']]
    return value

class Stage(Strict):
    stage:str=Field(max_length=20)
    revision:int=Field(ge=0)
    key:str=Field(min_length=8,max_length=100)

@router.post('/workflows/{id}/stage')
def stage(id:str,body:Stage):return video.queue(id,body.stage,body.revision,body.key)

class Edits(Strict):
    revision:int=Field(ge=0)
    plans:list[EditPlan]=Field(min_length=1,max_length=10)

@router.put('/workflows/{id}/plans')
def edits(id:str,body:Edits):return video.edit(id,body.revision,[p.model_dump() for p in body.plans])

class Revision(Strict):revision:int=Field(ge=0)

class Regenerate(Revision):prompt:str=Field(max_length=4000)

@router.post('/workflows/{id}/regenerate')
def regenerate(id:str,body:Regenerate):return video.regenerate(id,body.revision,body.prompt)

@router.post('/workflows/{id}/approve')
def approve(id:str,body:Revision):return video.approve(id,body.revision)

@router.get('/workflows/{id}/outputs/{revision}/{index}/{kind}')
def output(id:str,revision:int,index:int,kind:str):
    value=video.get(id)
    if kind not in ('preview','render'):raise ValueError('Unknown output type')
    found=next((o for o in value['outputs'] if o['revision']==revision and o['index']==index and o['preview']==(kind=='preview')),None)
    if not found:raise ValueError('Verified output not found')
    path=Path(found['file']).resolve()
    if not path.is_relative_to(video.folder(id).resolve()) or not path.is_file():raise ValueError('Output unavailable')
    return FileResponse(path,media_type='video/mp4')

@router.get('/integrations')
def integrations():
    from .video_editor import health
    root,python,script=sources.caption_config()
    return {'caption':{'ready':python.is_file() and script.is_file(),'path':str(root),'provider':'Existing ClipX CLI; cached model, CUDA when configured'},'editor':health(),'youtube':youtube_auth.status(),'renderer':{'ready':bool(__import__('shutil').which('ffmpeg')),'name':'FFmpeg supported subset'}}
