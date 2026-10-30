"""Library organisation is separate from render plans and approved publication metadata."""
import json,re,subprocess,uuid
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from filelock import FileLock
from pydantic import Field,field_validator
from . import db
from .config import artifact
from .studio_models import Strict
router=APIRouter(prefix='/api/library')

class Details(Strict):
    revision:int=Field(default=0,ge=0)
    name:str=Field(default='',max_length=180)
    labels:list[str]=Field(default_factory=list,max_length=20)
    notes:str=Field(default='',max_length=2000)
    favourite:bool=False
    archived:bool=False

class Edit(Strict):
    name:str|None=Field(default=None,min_length=1,max_length=180)
    labels:list[str]|None=Field(default=None,max_length=20)
    notes:str|None=Field(default=None,max_length=2000)
    favourite:bool|None=None
    archived:bool|None=None
    @field_validator('name')
    @classmethod
    def title(cls,v):
        if v is not None and not v.strip():raise ValueError('Enter a media name')
        return v.strip() if v is not None else v
    @field_validator('labels')
    @classmethod
    def tags(cls,v):
        if v is None:return v
        result=[]
        for text in v:
            text=text.strip()
            if not text or len(text)>32:raise ValueError('Labels must contain 1–32 characters')
            if text.casefold() not in {x.casefold() for x in result}:result.append(text)
        return result

class Batch(Strict):
    revisions:dict[str,int]=Field(min_length=1,max_length=100)
    changes:Edit

def check_id(id):
    if not re.fullmatch(r'[a-f0-9]{32}',id):raise ValueError('Invalid media ID')
    return id

def details(c,id):
    row=c.execute('SELECT value FROM preferences WHERE key=?',('media-library:'+id,)).fetchone()
    return Details.model_validate_json(row[0]) if row else Details()

def update(revisions,edits,label=''):
    if not edits and not label:raise ValueError('Choose an organisation change')
    if 'name' in edits and len(revisions)>1:raise ValueError('Rename one video at a time')
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE');result=[]
        for id,revision in revisions.items():
            check_id(id)
            if not c.execute('SELECT 1 FROM projects WHERE id=?',(id,)).fetchone():raise ValueError('Media no longer exists; refresh the library')
            current=details(c,id)
            if revision<0 or current.revision!=revision:raise ValueError('Library details changed; reload before saving')
            change=Edit(labels=current.labels if label.casefold() in {x.casefold() for x in current.labels} else current.labels+[label]).model_dump(exclude_none=True) if label else edits
            changed=Details.model_validate(current.model_dump()|change|{'revision':revision+1})
            c.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('media-library:'+id,db.encode(changed.model_dump())))
            result.append({'id':id,'library':changed.model_dump()})
    return result

@router.post('/organise')
def organise(body:Batch):return update(body.revisions,body.changes.model_dump(exclude_none=True))

class LabelBatch(Strict):
    revisions:dict[str,int]=Field(min_length=1,max_length=100)
    label:str=Field(min_length=1,max_length=32)
    @field_validator('label')
    @classmethod
    def valid_label(cls,v):return Edit.tags([v])[0]

@router.post('/labels')
def add_label(body:LabelBatch):return update(body.revisions,{},body.label)

@router.get('')
def listing():
    with db.connect() as c:
        projects=c.execute('SELECT id,body,created FROM projects ORDER BY created DESC').fetchall()
        operations=[json.loads(r[0]) for r in c.execute('SELECT body FROM youtube_operations ORDER BY rowid DESC')]
        channels={r['id']:json.loads(r['body'])['title'] for r in c.execute('SELECT id,body FROM youtube_channels')}
        by_project={}
        for op in operations:
            if op['kind']!='upload':continue
            params=op['params'];project=params.get('snapshot',{}).get('project')
            if not project:continue
            related=next((x for x in operations if x['params'].get('upload')==op['id']),None)
            state=related['state'] if related and related['state']!='confirmed' else op['state']
            by_project.setdefault(project,[]).append({'state':state,'channel':channels.get(params.get('channel'),params.get('channel','')),'remote_id':op.get('remote_id')})
        exports={}
        for r in c.execute("SELECT project,result FROM jobs WHERE kind='render' AND state='completed' ORDER BY created DESC"):
            output=json.loads(r['result']) if r['result'] else {}
            if output.get('file') and not output.get('preview'):exports.setdefault(r['project'],[]).append({'file':output['file'],'revision':output.get('revision',0)})
        result=[]
        for row in projects:
            p=json.loads(row['body']);info=details(c,p['id']).model_dump()
            try:source=artifact(p['id'],p['source']);size=source.stat().st_size if source.is_file() else None
            except (ValueError,OSError):size=None
            result.append(p|{'original_name':p['name'],'name':info['name'] or p['name'],'created':row['created'],'library':info,'size':size,'missing':size is None,'kind':'Rendered' if p.get('video_workflow') else 'Imported','publications':by_project.get(p['id'],[]),'exports':list({x['file']:x for x in exports.get(p['id'],[])}.values())})
        return result

@router.get('/{id}/thumbnail')
def thumbnail(id:str):
    check_id(id);p=db.project(id);source=artifact(id,p['source'])
    if not p['metadata'] or not source.is_file():raise HTTPException(404,'Media not ready for a thumbnail')
    target=artifact(id,'library-thumbnail.jpg')
    with FileLock(artifact(id,'library-thumbnail.lock'),timeout=2):
        if not target.is_file() or target.stat().st_mtime_ns<source.stat().st_mtime_ns:
            temporary=target.with_name('thumbnail-'+uuid.uuid4().hex+'.jpg')
            try:
                subprocess.run(['ffmpeg','-nostdin','-v','error','-protocol_whitelist','file,pipe','-ss',str(min(1,p['metadata']['duration']/3)),'-i',str(source),'-frames:v','1','-vf','scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2','-pix_fmt','yuvj420p','-threads','1',str(temporary)],check=True,capture_output=True,timeout=15)
                if not temporary.is_file() or temporary.stat().st_size<100:raise ValueError('Thumbnail frame unavailable')
                temporary.replace(target)
            except (OSError,subprocess.SubprocessError,ValueError):raise HTTPException(503,'Thumbnail unavailable; verify FFmpeg or open the video preview')
            finally:temporary.unlink(missing_ok=True)
    return FileResponse(target,media_type='image/jpeg')
