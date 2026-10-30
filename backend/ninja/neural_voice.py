"""Persistent, offline CPU voice; isolated dependencies from Ninja and ClipX."""
import atexit,io,json,os,queue,re,subprocess,tempfile,threading,uuid,wave
from pathlib import Path
from .config import DATA,ROOT

VOICES={'Jarvis · British male (Hindi voice for Hindi)':'auto','Kokoro · Hindi male':'hm_omega','Kokoro · natural female (Hindi / English)':'hf_alpha','Kokoro · English male':'am_michael','Kokoro · English female':'af_heart'}

def voice_for(text,voice):
    # The frontend speaks one sentence per request, so each sentence gets the voice for its script.
    value=VOICES[voice]
    return value if value!='auto' else 'hm_omega' if re.search('[ऀ-ॿ]',text) else 'bm_george'
_engine=None
_lock=threading.Lock()

def home():return Path(os.getenv('JARVIS_VOICE_HOME') or DATA/'services/jarvis-voice')

def status():
    folder=home();ready=(folder/'venv/Scripts/python.exe').is_file() and all((folder/'models'/p).is_file() for p in ('kokoro-v1.0.onnx','voices-v1.0.bin'))
    return {'ready':ready,'voices':list(VOICES) if ready else [],'default_voice':next(iter(VOICES)) if ready else ''}

class Engine:
    def __init__(self):
        self.folder=tempfile.TemporaryDirectory(prefix='ninja-neural-voice-');self.output=Path(self.folder.name)/'reply.wav';self.responses=queue.Queue(maxsize=1)
        try:
            self.process=subprocess.Popen([str(home()/'venv/Scripts/python.exe'),str(ROOT/'scripts/neural-voice-resident.py'),str(home()/'models'),str(self.output)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env={**os.environ,'PYTHONIOENCODING':'utf-8'},creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        except Exception:self.folder.cleanup();raise
        self.reader=threading.Thread(target=self.read,daemon=True);self.reader.start()
    def read(self):
        try:
            while line:=self.process.stdout.readline(2049):
                if len(line)>2048 or not line.endswith(b'\n'):break
                self.responses.put_nowait(json.loads(line))
        except (ValueError,OSError,queue.Full):pass
        if self.responses.empty():self.responses.put_nowait({'error':'Local neural voice stopped. Retry.'})
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
        self.process.stdin.close();self.process.stdout.close();self.reader.join(timeout=1);self.folder.cleanup()

def shutdown():
    global _engine
    with _lock:
        if _engine is not None:
            engine,_engine=_engine,None;engine.close()

def speak(text,voice):
    global _engine
    if voice not in VOICES or not isinstance(text,str) or not 1<=len(text)<=3000:raise ValueError('Choose an installed neural voice and 1–3000 characters')
    if not status()['ready']:raise ValueError('Install local speech with scripts/setup-local-voice.py first')
    # A barged-in reply's sentence may still be synthesising; the next one waits for it instead of failing.
    if not _lock.acquire(timeout=20):raise ValueError('Jarvis is already preparing speech. Wait a moment and retry.')
    try:
        if _engine is None or _engine.process.poll() is not None:
            if _engine:_engine.close()
            _engine=Engine()
        id=uuid.uuid4().hex
        _engine.process.stdin.write((json.dumps({'id':id,'text':text,'voice':voice_for(text,voice)},ensure_ascii=False)+'\n').encode('utf-8'));_engine.process.stdin.flush()
        result=_engine.responses.get(timeout=60)
        if not isinstance(result,dict) or result.get('id')!=id or result.get('ok') is not True:raise ValueError('Neural voice failed. Retry or check the local speech installation.')
        if not 44<_engine.output.stat().st_size<=10*1024**2:raise ValueError('Invalid speech size')
        data=_engine.output.read_bytes()
        with wave.open(io.BytesIO(data)) as wav:
            if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or wav.getframerate()!=24000:raise ValueError('Invalid neural speech format')
        return data
    except Exception:
        if _engine:_engine.close();_engine=None
        raise ValueError('Local neural speech failed or timed out. Try a shorter reply, or check the voice installation.') from None
    finally:
        if _engine:_engine.output.unlink(missing_ok=True)
        _lock.release()

atexit.register(shutdown)
