from fastapi import APIRouter
from pydantic import Field
from . import db,studio,youtube_auth as auth
from .studio_models import Strict,Definition,Save,Run,Activation

router=APIRouter(prefix='/api/studio')

@router.get('/channels')
def channels():return auth.channels()

class Connect(Strict):
    manage:bool=True
    analytics:bool=False

@router.post('/connect')
def connect(body:Connect):return auth.begin(body.manage,body.analytics,additional=True)

class Disconnect(Strict):connection:str

@router.post('/disconnect')
def disconnect(body:Disconnect):
    auth.vault(auth.token_key(body.connection),delete=True)
    return auth.channels()

@router.put('/channels/{id}/defaults')
def defaults(id:str,body:Definition):
    if body.channel!=id:raise ValueError('Defaults must belong to the selected channel')
    auth.connection_for(id)
    with db.connect() as c:
        row=c.execute('SELECT body FROM youtube_channels WHERE id=?',(id,)).fetchone()
        value=__import__('json').loads(row[0]);value['defaults']=body.model_dump();c.execute('UPDATE youtube_channels SET body=? WHERE id=?',(db.encode(value),id))
    return value

@router.get('/folders')
def folders():return studio.roots()

class Folder(Strict):path:str=Field(min_length=1,max_length=1000)

@router.post('/folders')
def grant(body:Folder):return studio.grant(body.path)

@router.get('/workflows')
def workflows():return studio.listing()

@router.get('/workflows/{id}')
def workflow(id:str):return studio.get(id)

@router.post('/workflows')
def create(body:Save):return studio.save(body.definition)

@router.put('/workflows/{id}')
def save(id:str,body:Save):return studio.save(body.definition,id,body.revision)

@router.post('/preflight')
def preflight(body:Definition):return studio.preflight(body)

@router.post('/workflows/{id}/activation')
def activate(id:str,body:Activation):return studio.activate(id,body.revision,body.active,body.acknowledged)

@router.post('/workflows/{id}/run')
def run(id:str,body:Run):return studio.start(id,body.test,body.key,body.reupload)

@router.get('/runs')
def runs(workflow:str|None=None):return studio.runs(workflow)

@router.post('/runs/{id}/retry')
def retry(id:str):
    run=studio.load_run(id)
    if run.get('superseded_by'):raise ValueError('This task was revised; open its replacement')
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute("SELECT 1 FROM jobs WHERE project=? AND kind='studio_steer' AND state IN ('queued','running')",(id,)).fetchone():raise ValueError('An instruction change is pending; wait for the revised task')
        row=c.execute('SELECT state,attempts FROM jobs WHERE id=?',(run['job'],)).fetchone()
        if not row or row['state'] not in ('failed','cancelled'):raise ValueError('Only failed or cancelled runs can resume')
        c.execute("UPDATE jobs SET state='queued',cancel=0,error=NULL,error_code=NULL,finished=NULL WHERE id=?",(run['job'],))
    return {'job':run['job']}

class Item(Strict):index:int=Field(ge=0)

@router.post('/runs/{id}/prepare')
def prepare(id:str,body:Item):return studio.prepare_review(id,body.index)

@router.post('/runs/{id}/collect')
def collect(id:str):return studio.collect(id)

class Instruction(Strict):text:str=Field(min_length=1,max_length=4000)

@router.post('/draft-instructions')
def instructions(body:Instruction):
    from . import adapters
    import json
    result=adapters.complete('Return JSON fields name, mode (finished/clips/research/business), prompt, trigger (manual/daily/folder), time (HH:MM), timezone (IANA), folder, policy (review/private/public/schedule). Interpret user preferences only; no executable commands. Never invent a channel ID or source path. Return only fields you can establish. This is a draft, never activation. User: '+body.text)
    raw=result['text'].strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    value=Definition.model_validate(json.loads(raw));return {'definition':value.model_dump(),'usage':result['usage']}


from . import studio_assistant

@router.post('/assistant/draft')
def assistant_draft(body:studio_assistant.Brief):return studio_assistant.draft(body)

@router.post('/runs/{id}/instructions')
def instructions_for_run(id:str,body:studio_assistant.Change):return studio_assistant.steer(id,body)


from . import studio_profiles

@router.get('/profiles')
def profiles():return studio_profiles.listing()

@router.put('/profiles/{id}')
def profile_save(id:str,body:studio_profiles.Profile):return studio_profiles.save(id,body)

@router.post('/profile-batches')
def profile_batch(body:studio_profiles.Batch):return studio_profiles.queue(body)

@router.get('/profile-batches')
def profile_batches():return studio_profiles.batches()

@router.post('/profile-batches/{id}/retry')
def profile_batch_retry(id:str):return studio_profiles.retry(id,'studio_batch')

@router.get('/runs/{id}/progress')
def run_progress(id:str):return studio_profiles.progress(id)

@router.post('/instruction-jobs/{id}/retry')
def instruction_retry(id:str):return studio_profiles.retry(id,'studio_steer')
