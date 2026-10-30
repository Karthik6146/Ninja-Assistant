import copy
import json
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal
from . import db
from .schemas import Caption

PLATFORMS=('youtube','instagram','threads')

class Draft(BaseModel):
    platform: Literal['youtube','instagram','threads']
    revision: int=Field(default=0,ge=0)
    account: str=Field(default='',max_length=200)
    title: str=Field(default='',max_length=100)
    copy: str=Field(default='',max_length=5000)
    tags: list[str]=Field(default_factory=list,max_length=30)
    chapters: str=Field(default='',max_length=5000)
    thumbnail_brief: str=Field(default='',max_length=2000)
    media: str|None=None
    schedule: str|None=None
    review: Literal['draft','reviewed']='draft'
    remote_id: str|None=None

class Scene(BaseModel):
    id: str=Field(default_factory=lambda:uuid.uuid4().hex)
    revision: int=Field(default=0,ge=0)
    script: str=Field(default='',max_length=8000)
    narration_asset: str|None=None
    visual_asset: str|None=None
    start: float|None=Field(default=None,ge=0)
    end: float|None=Field(default=None,gt=0)
    source: str=Field(default='',max_length=2000)
    rights: Literal['unknown','owned','licensed']='unknown'
    provider: str|None=None
    provider_task: str|None=None
    status: Literal['draft','needs_rebuild']='draft'

def create(project_id,package_id=None):
    p=db.project(project_id)
    if not p['edl']: raise ValueError('Project inspection pending')
    id=package_id or uuid.uuid4().hex
    body={'id':id,'project':project_id,'name':p['name'],'revision':0,'source_revision':p['edl']['revision'],'transcript':p['edl']['captions'],'timezone':'Asia/Kolkata','rights':'unknown','provenance':[{'source':p['source'],'origin':'user-provided','rights':'unknown'}],'scenes':[],'platforms':{platform:Draft(platform=platform).model_dump() for platform in PLATFORMS}}
    with db.connect() as c:
        c.execute('INSERT OR IGNORE INTO packages VALUES(?,?)',(id,db.encode(body)))
        existing=json.loads(c.execute('SELECT body FROM packages WHERE id=?',(id,)).fetchone()[0])
        if existing['project']!=project_id:raise ValueError('Package ID belongs to another project')
    return existing

def load(id):
    with db.connect() as c:row=c.execute('SELECT body FROM packages WHERE id=?',(id,)).fetchone()
    if not row:raise ValueError('Content package not found')
    body=json.loads(row[0]);p=db.project(body['project'])
    if body['source_revision']!=p['edl']['revision']:
        body['source_revision']=p['edl']['revision'];body['transcript']=p['edl']['captions'];body['revision']+=1
        for draft in body['platforms'].values():draft['review']='draft';draft['media']=None;draft['revision']+=1
        save(body,expected=json.loads(row[0]))
    return body

def save(body,expected):
    with db.connect() as c:
        result=c.execute('UPDATE packages SET body=? WHERE id=? AND body=?',(db.encode(body),body['id'],db.encode(expected)))
        if result.rowcount!=1:raise ValueError('Content package changed; reload')

def outputs(body):
    with db.connect() as c:rows=c.execute("SELECT result FROM jobs WHERE project=? AND kind='render' AND state='completed'",(body['project'],)).fetchall()
    result=[json.loads(r[0]) for r in rows if r[0] and json.loads(r[0])['revision']==body['source_revision']]
    p=db.project(body['project'])
    if p.get('finished_media') and body['source_revision']==0:
        result.append({'file':p['finished_media']['file'],'revision':0,'preview':False,'kind':'finished_original','metadata':p['metadata']})
    return result

def edit_draft(id, draft):
    body=load(id);original=copy.deepcopy(body);current=body['platforms'][draft.platform]
    if draft.revision!=current['revision']:raise ValueError('Stale platform draft')
    if draft.remote_id:raise ValueError('Remote IDs may only be recorded by API-confirmed publication')
    if draft.media and draft.media not in {o['file'] for o in outputs(body) if not o['preview']}:raise ValueError('Select a completed final render of the current revision')
    if draft.schedule:
        date=datetime.fromisoformat(draft.schedule)
        if date.tzinfo is None:raise ValueError('Schedule needs an explicit timezone offset; Asia/Kolkata is +05:30')
    draft.revision+=1;draft.review='draft';body['platforms'][draft.platform]=draft.model_dump();body['revision']+=1
    save(body,expected=original);db.audit('content.draft-edited',{'package':id,'platform':draft.platform,'revision':draft.revision})
    return body

def review(id,platform,revision):
    if platform not in PLATFORMS:raise ValueError('Unsupported platform')
    body=load(id);original=copy.deepcopy(body);draft=body['platforms'][platform]
    if draft['revision']!=revision:raise ValueError('Stale review')
    if not draft['account'] or not draft['copy']:raise ValueError('Review requires an exact account label and content')
    if platform in ('youtube','instagram') and not draft['media']:raise ValueError('Select a final render before review')
    if body['rights']=='unknown':raise ValueError('Resolve recording/music rights before review')
    draft['review']='reviewed';save(body,expected=original)
    db.audit('content.reviewed',{'package':id,'platform':platform,'revision':revision})
    return body

def scenes(id,revision,items,rights):
    body=load(id);original=copy.deepcopy(body)
    if body['revision']!=revision:raise ValueError('Stale scene manifest')
    old={s['id']:s for s in body['scenes']};result=[];names=set()
    for item in items:
        scene=Scene.model_validate(item).model_dump()
        if scene['id'] in names:raise ValueError('Duplicate scene ID')
        names.add(scene['id'])
        # Assets must be local project artifacts, not URLs or arbitrary host paths.
        for field in ('narration_asset','visual_asset'):
            if scene[field]:
                from .config import artifact
                path=artifact(body['project'],scene[field])
                if not path.is_file():raise ValueError('Scene asset missing')
        previous=old.get(scene['id'])
        if previous and any(previous.get(k)!=scene.get(k) for k in ('script','visual_asset','start','end')):
            scene['revision']=previous['revision']+1;scene['narration_asset']=None;scene['start']=None;scene['end']=None;scene['status']='needs_rebuild'
        if scene['start'] is not None and scene['end'] is not None and scene['end']<=scene['start']:raise ValueError('Invalid scene timing')
        result.append(scene)
    body['scenes']=result;body['rights']=rights;body['revision']+=1
    body['provenance'][0]['rights']=rights
    for draft in body['platforms'].values():draft['review']='draft'
    save(body,expected=original)
    return body
