"""Authenticated local assistant endpoints; scopes select server-authorized targets."""
import os
from fastapi import APIRouter,Request as FastAPIRequest
from typing import Literal
from pydantic import Field
from . import agent,db,permissions,tools
from .agent_models import Request,Instruction,Strict
from . import assistant_tools
router=APIRouter(prefix='/api/assistant')

class ModelChoice(Strict):
    provider:Literal['ollama','cloud']
    model:str=Field(default='',max_length=200)

@router.get('/models')
def models():
    """What the composer's model picker offers: installed Ollama models and the .env cloud model, if configured."""
    from . import adapters
    from urllib.parse import urlsplit
    import httpx
    # Per installed model: bytes on disk, and bytes in VRAM when Ollama has it loaded.
    memory={}
    try:
        with httpx.Client(base_url=adapters.ollama_url(),timeout=3,trust_env=False) as client:
            memory={m['name']:{'disk':m.get('size'),'vram':None} for m in client.get('/api/tags').raise_for_status().json().get('models',[])}
            for m in client.get('/api/ps').raise_for_status().json().get('models',[]):
                if m.get('name') in memory:memory[m['name']]['vram']=m.get('size_vram')
    except (httpx.HTTPError,ValueError,KeyError):pass  # Ollama stopped; the menu shows names only.
    return {'provider':adapters.chat_provider(),'model':adapters.chat_model(),'local':adapters.provider_status()[0]['models'],'memory':memory,
            'cloud':{'model':os.getenv('CLOUD_MODEL',''),'host':urlsplit(os.getenv('CLOUD_URL','')).hostname or '','ready':adapters.cloud_ready()}}

@router.put('/models')
def choose_model(body:ModelChoice):
    from . import adapters
    if body.provider=='cloud' and not adapters.cloud_ready():raise ValueError('Cloud API is not set up. Add CLOUD_ENABLED=true, CLOUD_URL, CLOUD_MODEL and CLOUD_API_KEY to .env')
    if body.provider=='ollama' and body.model not in adapters.provider_status()[0]['models']:raise ValueError('Choose an installed Ollama model')
    with db.connect() as c:
        c.execute("INSERT OR REPLACE INTO preferences VALUES('chat_provider',?)",(body.provider,))
        if body.provider=='ollama':c.execute("INSERT OR REPLACE INTO preferences VALUES('ollama_model',?)",(body.model,))
    return models()

def gpu():
    """The first NVIDIA GPU's live name, load, VRAM and temperature, or None without an NVIDIA driver."""
    import subprocess
    try:
        out=subprocess.run(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu','--format=csv,noheader,nounits'],
                           capture_output=True,text=True,timeout=3,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0).stdout.splitlines()[0].split(', ')
        return {'name':out[0],'load':int(out[1]),'memory_used':int(out[2])*2**20,'memory_total':int(out[3])*2**20,'temperature':int(out[4])}
    except (OSError,subprocess.SubprocessError,IndexError,ValueError):return None

def speed(model):
    """Speeds over the model's last 20 replies, from Ollama's own token counts and durations; None before its first reply."""
    import json
    with db.connect() as c:
        # Each model turn's result keeps Ollama's own token counts and durations.
        steps=c.execute("""SELECT json_extract(s.result,'$.usage') AS usage,json_extract(s.result,'$.timing') AS timing FROM
            (SELECT job,reported FROM chat_usage WHERE provider='ollama' AND model=? ORDER BY reported DESC LIMIT 20) u
            JOIN jobs j ON j.id=u.job JOIN agent_steps s ON s.task=j.project AND s.step LIKE 'model:'||u.job||':%' AND s.state='completed'""",(model,)).fetchall()
    turns=[(json.loads(r['usage'] or '{}'),json.loads(r['timing'] or '{}')) for r in steps]
    def rate(tokens,seconds):
        pairs=[(u.get(tokens),t.get(seconds)) for u,t in turns if type(u.get(tokens))==int and t.get(seconds)]
        return round(sum(a for a,_ in pairs)/sum(b for _,b in pairs),1) if pairs else None
    def mean(key):
        values=[t[key] for _,t in turns if type(t.get(key)) in (int,float)]
        return round(sum(values)/len(values),2) if values else None
    if not turns:return None
    return {'turns':len(turns),'output_per_second':rate('output_tokens','generation_seconds'),'prompt_per_second':rate('input_tokens','prompt_seconds'),
            'first_text_seconds':mean('first_text_seconds'),'turn_seconds':mean('model_seconds'),'load_seconds':mean('load_seconds')}

@router.get('/gpu')
def gpu_status():
    """Polled by the composer bar's chip; cheaper than the full model card. Speed only for a local chat model."""
    from . import adapters
    measured=speed(adapters.chat_model()) if adapters.chat_provider()=='ollama' else None
    return {'gpu':gpu(),'tokens_per_second':measured and measured['output_per_second']}

class Unload(Strict):
    model:str=Field(max_length=200)

@router.post('/models/unload')
def unload_model(body:Unload):
    """Free one model's VRAM now. Refused while a reply or media job holds the model lock; the next chat loads it again."""
    import httpx
    from filelock import FileLock,Timeout
    from . import adapters
    from .config import DATA
    if body.model not in adapters.provider_status()[0]['models']:raise ValueError('Choose an installed Ollama model')
    try:
        with FileLock(DATA/'model.lock',timeout=0),httpx.Client(base_url=adapters.ollama_url(),timeout=30,trust_env=False) as client:
            client.post('/api/generate',json={'model':body.model,'keep_alive':0}).raise_for_status()
    except Timeout:raise ValueError('The model is busy with a reply or a media job; try again when it finishes') from None
    except httpx.HTTPError:raise ValueError('Ollama could not unload the model; check that it is running') from None
    return models()

@router.get('/models/info')
def model_info(model:str):
    """The picker's info card: what Ollama reports about an installed model, whether it sits in VRAM, the GPU's live load and speeds measured over recent replies."""
    import httpx
    from . import adapters
    if model not in adapters.provider_status()[0]['models']:raise ValueError('Choose an installed Ollama model')
    info={'model':model,'details':{},'capabilities':[],'parameters':None,'context_max':None,'disk_bytes':None,'loaded':None,'gpu':None,'speed':None}
    try:
        with httpx.Client(base_url=adapters.ollama_url(),timeout=5,trust_env=False) as client:
            shown=client.post('/api/show',json={'model':model}).raise_for_status().json()
            info['details']={k:shown.get('details',{}).get(k) for k in ('family','parameter_size','quantization_level','format')}
            info['capabilities']=shown.get('capabilities') or []
            facts=shown.get('model_info') or {}
            info['parameters']=facts.get('general.parameter_count')
            info['context_max']=next((v for k,v in facts.items() if k.endswith('.context_length')),None)
            info['disk_bytes']=next((m.get('size') for m in client.get('/api/tags').raise_for_status().json().get('models',[]) if m.get('name')==model),None)
            running=next((m for m in client.get('/api/ps').raise_for_status().json().get('models',[]) if m.get('name')==model),None)
            if running:info['loaded']={k:running.get(k) for k in ('size','size_vram','context_length')}
    except (httpx.HTTPError,ValueError):pass  # Ollama stopped; the card shows what it can.
    info['gpu']=gpu()
    info['speed']=speed(model)
    return info

@router.get('/usage')
def usage():
    """Chat tokens per day (last 30) and per month (last 12), local time; empty periods are zero. Each reply is one row, dated when it finished."""
    import datetime
    today=datetime.date.today()
    days=[(today-datetime.timedelta(days=n)).isoformat() for n in range(29,-1,-1)]
    months=[f'{(today.year*12+today.month-1-n)//12}-{(today.month-1-n)%12+1:02d}' for n in range(11,-1,-1)]
    with db.connect() as c:
        rows=c.execute("SELECT strftime('%Y-%m-%d',reported,'unixepoch','localtime') AS day,SUM(COALESCE(input_tokens,0)) AS input,SUM(COALESCE(output_tokens,0)) AS output,COUNT(*) AS replies FROM chat_usage WHERE day>=? GROUP BY day",(months[0]+'-01',)).fetchall()
        by_model=c.execute("SELECT provider,model,SUM(COALESCE(input_tokens,0)) AS input,SUM(COALESCE(output_tokens,0)) AS output,COUNT(*) AS replies FROM chat_usage WHERE strftime('%Y-%m-%d',reported,'unixepoch','localtime')>=? GROUP BY provider,model ORDER BY input+output DESC",(days[0],)).fetchall()
    def group(keys,width):
        totals={k:{'period':k,'input':0,'output':0,'replies':0} for k in keys}
        for r in rows:
            if r['day'][:width] in totals:
                for key in ('input','output','replies'):totals[r['day'][:width]][key]+=r[key]
        return list(totals.values())
    return {'day':group(days,10),'month':group(months,7),'models':[dict(r) for r in by_model]}

@router.get('/tasks')
def listing():return agent.listing()
@router.post('/tasks')
def create(body:Request):return agent.create(body)
@router.get('/tasks/{id}')
def get(id:str):return agent.get(id)
@router.get('/tasks/{id}/stream')
async def stream(id:str,request:FastAPIRequest):
    """Push the task as it changes so drafts reach the voice player without client polling."""
    import asyncio
    from fastapi.responses import StreamingResponse
    await asyncio.to_thread(agent.get,id)
    async def events():
        previous=None;started=asyncio.get_running_loop().time()
        # Trade-off: 100 ms server-side check of one row; switch to change notifications if many clients stream.
        while not await request.is_disconnected() and asyncio.get_running_loop().time()-started<agent.MAX_SECONDS+30:
            value=await asyncio.to_thread(agent.get,id);encoded=db.encode(value)
            if encoded!=previous:yield 'data: '+encoded+'\n\n';previous=encoded
            if value['state'] not in ('queued','running'):break
            await asyncio.sleep(.1)
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
@router.post('/tasks/{id}/instructions')
def instruct(id:str,body:Instruction):return agent.revise(id,body)
class Decision(Strict):
    approval:str=Field(pattern=r'^[a-f0-9]{32}$')
    allow:bool
@router.post('/tasks/{id}/confirm')
def decide(id:str,body:Decision):return agent.confirm(id,body.approval,body.allow)
@router.post('/tasks/{id}/cancel')
def cancel(id:str):return agent.cancel(id)
@router.get('/permissions')
def access():
    return {'grants':permissions.grants(),'tools':[{'name':t.name,'permission':t.permission,'effect':t.effect} for t in tools.REGISTRY.values()],'sensitive':'Spending, security changes and sensitive personal information require exact confirmation; unsupported tools remain unavailable.'}
class Grants(Strict):grants:dict[str,bool|Literal['ask']]
@router.put('/permissions')
def save_access(body:Grants):
    allowed={t.permission for t in tools.REGISTRY.values()}
    if body.grants.keys()-allowed:raise ValueError('Unknown capability; model-generated permissions are not accepted')
    with db.connect() as c:c.execute("INSERT OR REPLACE INTO preferences VALUES('assistant.permissions',?)",(db.encode(body.grants),))
    return access()


from . import memory
from .agent_models import Scope
class MemoryInput(Strict):
    text:str=Field(min_length=1,max_length=2000)
    scope:Scope=Field(default_factory=Scope)
class Correction(Strict):
    text:str=Field(min_length=1,max_length=2000)
    revision:int=Field(ge=0)
@router.get('/memory')
def memories(scope_kind:str='personal',scope_id:str='me',q:str=''):
    scopes=[Scope(kind=scope_kind,id=scope_id)];agent.valid_scopes(scopes)
    return memory.search(q,scopes) if q else memory.listing(scopes)
@router.post('/memory')
def remember(body:MemoryInput):
    agent.valid_scopes([body.scope])
    return memory.remember(body.text,body.scope,source='manual')
@router.put('/memory/{id}')
def correct(id:str,body:Correction):return memory.correct(id,body.text,body.revision)
@router.post('/memory/{id}/forget')
def forget(id:str):return memory.forget(id)


import tempfile
from pathlib import Path
from fastapi import UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from . import voice
@router.get('/voice')
def speech_status():
    from . import neural_voice,listener
    neural=neural_voice.status()
    return voice.status()|{'voices':neural['voices']+voice.voices(),'default_voice':neural['default_voice'],'neural_ready':neural['ready'],'live_ready':listener.ready()}
from fastapi import WebSocket,WebSocketDisconnect
from . import listener
@router.websocket('/voice/live')
async def live_voice(websocket:WebSocket):
    """Browser streams 16 kHz int16 audio; the listener ends turns and the transcript is pushed back."""
    import asyncio,json,secrets
    from .config import ORIGINS,session_ok
    # The HTTP guard middleware does not see WebSockets, so the session cookie and origin are checked here.
    origin=websocket.headers.get('origin')
    if origin and origin not in ORIGINS or not session_ok(websocket.cookies.get('ninja_session')):
        await websocket.close(code=1008);return
    await websocket.accept()
    try:engine=await asyncio.to_thread(listener.shared)
    except ValueError as error:
        await websocket.send_json({'type':'error','message':str(error)});await websocket.close();return
    loop=asyncio.get_running_loop();events=asyncio.Queue();language={'value':'auto'}  # recognition auto-detects English or Hindi; the reply language is per conversation
    def sink(event):loop.call_soon_threadsafe(events.put_nowait,event)
    async def forward():
        while True:
            event=await events.get()
            if event['event']=='turn':
                try:result=await asyncio.to_thread(voice.transcribe,event['path'],language['value'])
                except Exception as error:
                    await websocket.send_json({'type':'error','message':db.safe_error(error)});continue
                await websocket.send_json({'type':'transcript',**result})
            elif event['event'] in ('speech','wake','discard'):await websocket.send_json({'type':event['event']})
            elif event['event']=='error':await websocket.send_json({'type':'error','message':'Live listener stopped; start the conversation again.'})
    engine.attach(sink);task=asyncio.create_task(forward())
    try:
        while True:
            message=await websocket.receive()
            if message['type']=='websocket.disconnect':break
            if message.get('bytes') is not None:
                data=message['bytes']
                # Whole 512-sample int16 frames only, at most ~1 s per message.
                if not data or len(data)%1024 or len(data)>32768:
                    await websocket.send_json({'type':'error','message':'Invalid audio frame'});continue
                await asyncio.to_thread(engine.send_audio,data)
            elif message.get('text'):
                mode=json.loads(message['text'])
                if not isinstance(mode,dict):continue
                await asyncio.to_thread(engine.mode,mode.get('standby') is True)
    except (WebSocketDisconnect,RuntimeError):pass
    finally:
        engine.detach(sink);task.cancel()

@router.post('/warm')
def warm_chat():
    """Opening Jarvis preloads the local chat model in the background, so the first typed reply skips the ~9 s load."""
    import threading
    from . import adapters
    if adapters.chat_provider()=='ollama':threading.Thread(target=adapters.warm_local_model,daemon=True).start()
    return {'warming':adapters.chat_provider()=='ollama'}

@router.post('/voice/warm')
def warm():
    import threading
    from . import adapters,neural_voice
    def voices():
        # Start the resident speech, recognition and listening helpers so the first turn skips model loading.
        try:neural_voice.speak('Ready.',next(iter(neural_voice.VOICES)))
        except ValueError:pass
        try:
            import wave
            with tempfile.TemporaryDirectory(prefix='ninja-warm-') as folder:
                silence=Path(folder)/'warm.wav'
                with wave.open(str(silence),'wb') as out:out.setparams((1,2,16000,0,'NONE','NONE'));out.writeframes(b'\0\0'*8000)
                voice.transcribe(silence,'hinglish')
        except Exception:pass  # Silence has no words; loading the model is the point.
        try:listener.shared()
        except ValueError:pass
    threading.Thread(target=voices,daemon=True).start()
    return {'warm':adapters.warm_local_model()}
@router.post('/voice/transcribe')
async def transcribe(file:UploadFile,language:str='auto'):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in ('.webm','.wav','.ogg','.m4a','.mp3','.mp4'):raise ValueError('Unsupported speech recording format')
    with tempfile.TemporaryDirectory(prefix='ninja-upload-speech-') as folder:
        path=Path(folder)/('utterance'+suffix);count=0
        try:
            with path.open('wb') as output:
                while chunk:=await file.read(1024*1024):
                    count+=len(chunk)
                    if count>20*1024**2:raise ValueError('Speech upload exceeds 20 MiB')
                    output.write(chunk)
            return await run_in_threadpool(voice.transcribe,path,language)
        finally:await file.close()
class Speech(Strict):
    text:str=Field(min_length=1,max_length=3000)
    voice:str=Field(min_length=1,max_length=100)
@router.post('/voice/speak')
def speak(body:Speech):
    return Response(voice.speak(body.text,body.voice),media_type='audio/wav',headers={'Cache-Control':'no-store'})


from . import assistant_events
@router.get('/reminders')
def reminders():return {'timezone':'Asia/Kolkata','items':assistant_events.listing()}
@router.post('/reminders/{id}/dismiss')
def dismiss_reminder(id:str):return assistant_events.dismiss(id)


from typing import Literal
class PrivateMessage(Strict):
    role:Literal['user','assistant']
    content:str=Field(min_length=1,max_length=6000)
class PrivateQuestion(Strict):
    messages:list[PrivateMessage]=Field(min_length=1,max_length=12)
@router.post('/private')
def private_question(body:PrivateQuestion):
    from fastapi.responses import JSONResponse
    from . import adapters
    if body.messages[-1].role!='user':raise ValueError('End with your question')
    return JSONResponse(adapters.private_reply([m.model_dump() for m in body.messages]),headers={'Cache-Control':'no-store'})
@router.post('/tasks/forget-all')
def forget_all_conversations():return agent.forget_all()

@router.post('/tasks/{id}/forget')
def forget_conversation(id:str):return agent.forget_task(id)

class DraftSave(Strict):
    revision:int=Field(ge=0)
@router.post('/tasks/{id}/draft')
def save_video_draft(id:str,body:DraftSave):return agent.save_video_draft(id,body.revision)
