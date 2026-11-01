"""Short intentional speech through the existing standalone transcription tool."""
import atexit,functools,json,math,os,queue,re,shutil,subprocess,tempfile,threading,time,unicodedata,uuid,wave
from pathlib import Path
from filelock import FileLock
from . import db,media
from .config import DATA,ROOT
from .video_sources import caption_config

VOICE_TIMEOUT=120
# English words the owner says inside Hindi sentences. As a recognition hint they lift Hindi key-word accuracy from
# 74% to 88% (English stays 100%) and come out in English ("Mera resume dhundho"). Hindi verbs are left out:
# as hints they loop ("बताओ, बताओ, …") on noise. A transcript that only echoes this list is rejected below.
VOCABULARY=['Jarvis','joke','resume','screenshot','volume','timer','reminder','YouTube','video','file','folder','WhatsApp','weather']
_engine=None

def _fingerprint(parts):
    root,python,script,model=parts
    files=[python,script,*script.parent.glob('speech_*.py'),*model.iterdir()]
    return tuple((str(p.resolve()),p.stat().st_size,p.stat().st_mtime_ns) for p in files if p.is_file())

class _Resident:
    def __init__(self,parts):
        root,python,script,model=parts
        self.fingerprint=_fingerprint(parts);self.folder=tempfile.TemporaryDirectory(prefix='ninja-voice-engine-')
        self.audio=Path(self.folder.name)/'utterance.wav';self.responses=queue.Queue(maxsize=1)
        env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PYTHONIOENCODING':'utf-8','NINJA_VOICE_VOCABULARY':json.dumps(VOCABULARY)}
        try:
            self.process=subprocess.Popen([str(python),str(ROOT/'scripts/voice-resident.py'),str(script),str(model),self.folder.name],cwd=root,
                env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        except Exception:self.folder.cleanup();raise
        self.reader=threading.Thread(target=self._read,daemon=True);self.reader.start();self.warm=False

    def _read(self):
        try:
            while line:=self.process.stdout.readline(256001):
                if len(line)>256000 or not line.endswith(b'\n'):raise ValueError('Invalid speech response')
                self.responses.put_nowait(json.loads(line))
        except (OSError,ValueError,queue.Full):pass
        if self.responses.empty():self.responses.put_nowait({'error':'Local speech helper stopped. Retry the recording.'})

    def recognize(self,language):
        id=uuid.uuid4().hex
        self.process.stdin.write(json.dumps({'id':id,'language':language}).encode()+b'\n');self.process.stdin.flush()
        try:value=self.responses.get(timeout=VOICE_TIMEOUT)
        except queue.Empty:raise TimeoutError('Local speech timed out. The helper was stopped; retry a shorter recording.') from None
        if not isinstance(value,dict):raise ValueError('Invalid local speech response; retry')
        if value.get('error'):raise ValueError(value['error'])
        if value.get('id')!=id or not isinstance(value.get('value'),dict):raise ValueError('Local speech response did not match the recording; retry')
        self.warm=True;return value

    def close(self):
        import psutil
        try:children=psutil.Process(self.process.pid).children(recursive=True)
        except psutil.Error:children=[]
        for child in children:
            try:child.terminate()
            except psutil.Error:pass
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        for child in children:
            try:
                if child.is_running():child.kill()
            except psutil.Error:pass
        for pipe in (self.process.stdin,self.process.stdout):pipe.close()
        self.reader.join(timeout=1);self.folder.cleanup()

def shutdown():
    global _engine
    if _engine is not None:
        engine,_engine=_engine,None;engine.close()

atexit.register(shutdown)

def components():
    root,python,script=caption_config()
    setting=os.getenv('JARVIS_VOICE_MODEL','')
    from .neural_voice import home
    installed=home()/'models/whisper-small'
    # ClipX's large-v3-turbo hears Hindi far better (74% vs 43% of key words on our benchmark, English 100% on both)
    # for ~0.3 s more per turn and ~0.9 GB more GPU memory; small is the fallback when ClipX lacks it.
    turbo=sorted((root/'.models/whisper/models--dropbox-dash--faster-whisper-large-v3-turbo/snapshots').glob('*/model.bin'))
    if setting:model=Path(setting).resolve()
    elif turbo:model=turbo[0].parent
    elif (installed/'model.bin').is_file():model=installed
    else:
        cached=Path.home()/'.cache/huggingface/hub/models--Systran--faster-whisper-tiny/snapshots'
        models=sorted(cached.glob('*/model.bin'))
        model=models[0].parent if models else DATA/'missing-voice-model'
    return root,python,script,model

def status():
    root,python,script,model=components()
    ready=python.is_file() and script.is_file() and (model/'model.bin').is_file()
    engine=_engine
    warm=bool(ready and engine is not None and engine.process.poll() is None and engine.fingerprint==_fingerprint((root,python,script,model)) and engine.warm)
    return {'ready':ready,'warm':warm,'model':model.parent.parent.name.split('--')[-1] if model.parent.name=='snapshots' else model.name,'engine':'Existing standalone ClipX  /  warm GPU (CPU fallback)  /  offline','message':'Local English and Hindi recognition, reused between turns; names and numbers may still need correction.' if ready else 'Voice is not configured. Set your standalone Caption Tool folder in Settings and JARVIS_VOICE_MODEL to an existing multilingual model folder. No model is downloaded automatically.'}

def native_wav(path):
    try:
        with wave.open(str(path),'rb') as source:return (source.getnchannels(),source.getsampwidth(),source.getframerate())==(1,2,16000)
    except (wave.Error,EOFError,OSError):return False

def transcribe(path,language):
    global _engine
    started=time.monotonic()
    if language not in ('auto','en','hi','hinglish'):raise ValueError('Choose English, Hindi, Hinglish or automatic language')
    # A short wait lets a turn queue behind warm-up instead of failing.
    with FileLock(DATA/'voice-cpu.lock',timeout=3):
        root,python,script,model=components()
        if not python.is_file() or not script.is_file() or not (model/'model.bin').is_file():
            shutdown();raise ValueError('Voice is not configured; open Settings')
        if not Path(path).is_file() or Path(path).stat().st_size>20*1024**2:raise ValueError('Speech upload exceeds 20 MiB or is not a regular file')
        parts=(root,python,script,model)
        if _engine is None or _engine.process.poll() is not None or _engine.fingerprint!=_fingerprint(parts):
            shutdown();_engine=_Resident(parts)
        audio=_engine.audio
        try:
            # Browser WebM may omit duration; measure bounded decoded audio instead.
            # The live listener already writes 16 kHz mono PCM; only browser uploads need ffmpeg (~0.27 s).
            if native_wav(path):shutil.copyfile(path,audio)
            else:media.run(['ffmpeg','-y','-v','error','-protocol_whitelist','file,pipe','-format_whitelist','matroska,webm,wav,ogg,mov,mp3','-i',str(path),'-t','61','-vn','-ar','16000','-ac','1','-c:a','pcm_s16le',str(audio)],timeout=20)
            with wave.open(str(audio),'rb') as decoded_audio:
                duration=decoded_audio.getnframes()/decoded_audio.getframerate()
                if decoded_audio.getnchannels()!=1 or decoded_audio.getsampwidth()!=2 or decoded_audio.getframerate()!=16000:raise ValueError('Speech decoder returned an unsupported audio format')
            if not math.isfinite(duration) or not 0<duration<=60:raise ValueError('Record one utterance between 0 and 60 seconds')
            decoded=time.monotonic()
            # The owner speaks English or Hindi: automatic detection is limited to those two (hi-latn), because open
            # detection wrote Hindi such as "आज मौसम कैसा है" in Urdu script.
            try:frame=_engine.recognize('hi-latn' if language in ('auto','hinglish') else language)
            except (TimeoutError,ValueError,OSError):shutdown();raise
            words=frame['value'].get('words',[])
            if not isinstance(words,list) or len(words)>3000 or any(not isinstance(w,dict) or not isinstance(w.get('text'),str) for w in words):raise ValueError('Invalid local speech transcript; retry')
            text=' '.join(str(v.get('text','')) for v in words).strip()
            if not text or len(text)>6000:raise ValueError('No usable speech detected. Try again closer to the microphone')
            return {'text':text,'language':language,'duration':duration,'uncertain':uncertain_transcript(words,language),'warm':frame['warm'],
                    'timing':{'total_ms':round((time.monotonic()-started)*1000),'decode_ms':round((decoded-started)*1000),'recognition_ms':frame['recognition_ms']},'device':frame.get('device','cpu'),
                    'message':'Review uncertain words, names or numbers before sending.'}
        finally:
            if audio.exists():audio.unlink()

@functools.lru_cache(maxsize=1)
def voices():
    """Installed Windows speech voices, the fallback when the neural voice is unavailable."""
    try:
        result=json.loads(media.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/narrate.ps1'),'-List'],timeout=20))
        return result if isinstance(result,list) else [result]
    except (ValueError,RuntimeError,OSError):return []

def speak(text,voice):
    from . import neural_voice
    # Citation markers such as [1] are for the screen; spoken they come out as "one".
    text=re.sub(r'\s*\[\d+\]','',text).strip() or text
    if voice in neural_voice.VOICES:return neural_voice.speak(text,voice)
    if not 1<=len(text)<=3000 or voice not in voices():raise ValueError('Choose an installed local voice and 1-3000 characters')
    with FileLock(DATA/'voice-tts.lock',timeout=0), tempfile.TemporaryDirectory(prefix='ninja-speech-') as temporary:
        folder=Path(temporary);source=folder/'text.txt';output=folder/'reply.wav'
        source.write_text(text,encoding='utf-8')
        media.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/narrate.ps1'),'-TextFile',str(source),'-OutputFile',str(output),'-Voice',voice],timeout=90)
        if output.stat().st_size>20*1024**2:raise ValueError('Speech response exceeds the size limit')
        return output.read_bytes()



def uncertain_transcript(words,language):
    text=' '.join(w['text'] for w in words)
    if language in ('en','hi','hinglish'):
        if any(c.isalpha() and not (unicodedata.name(c,'').startswith('LATIN ') or language!='en' and '\u0900'<=c<='\u097f') for c in text):return True
    tokens=re.findall(r"[\w]+",text.lower())
    # Noise read as the hint list: four or more of its words in the list's own order ("YouTube video file" is real speech).
    hints=[w.lower() for w in VOCABULARY]
    order=[hints.index(t) if t in hints else -1 for t in tokens]
    if any(-1<order[i]<order[i+1]<order[i+2]<order[i+3] for i in range(len(order)-3)):return True
    for size in range(1,5):
        for i in range(len(tokens)-size*4+1):
            if tokens[i:i+size]*4==tokens[i:i+size*4]:return True
    scores=[w.get('confidence') for w in words]
    if not scores or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in scores):return True
    # One imperfect word must not block an otherwise clear utterance.
    return sum(scores)/len(scores)<.60 or sum(v<.40 for v in scores)/len(scores)>.25
