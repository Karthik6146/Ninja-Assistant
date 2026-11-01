"""Authenticated local assistant endpoints; scopes select server-authorized targets."""
from fastapi import APIRouter,Request as FastAPIRequest
from typing import Literal
from pydantic import Field
from . import agent,db,permissions,tools
from .agent_models import Request,Instruction,Strict
from . import assistant_tools
router=APIRouter(prefix='/api/assistant')

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
@router.post('/tasks/{id}/forget')
def forget_conversation(id:str):return agent.forget_task(id)

class DraftSave(Strict):
    revision:int=Field(ge=0)
@router.post('/tasks/{id}/draft')
def save_video_draft(id:str,body:DraftSave):return agent.save_video_draft(id,body.revision)
