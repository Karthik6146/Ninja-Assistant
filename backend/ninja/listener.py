"""Resident live listener (Silero VAD, Smart Turn, wake word) in the isolated jarvis-voice environment."""
import atexit,json,os,struct,subprocess,tempfile,threading
from pathlib import Path
from .config import ROOT
from .neural_voice import home

_shared=None
_lock=threading.Lock()


def models():return home()/'models/listener'


def ready():
    return (home()/'venv/Scripts/python.exe').is_file() and all((models()/name).is_file() for name in
        ('silero_vad_v6.onnx','smart-turn-v3.2-cpu.onnx','melspectrogram.onnx','embedding_model.onnx','hey_jarvis_v0.1.onnx'))


class Listener:
    def __init__(self):
        self.folder=tempfile.TemporaryDirectory(prefix='ninja-listener-');self.sink=None;self.write=threading.Lock()
        try:
            self.process=subprocess.Popen([str(home()/'venv/Scripts/python.exe'),str(ROOT/'scripts/listener-resident.py'),str(models()),self.folder.name],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env={**os.environ,'PYTHONIOENCODING':'utf-8'},
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        except Exception:self.folder.cleanup();raise
        threading.Thread(target=self.read,daemon=True).start()

    def read(self):
        try:
            while line:=self.process.stdout.readline(4097):
                event=json.loads(line)
                # Turn files must stay inside this listener's own temporary folder.
                if event.get('path') and Path(event['path']).resolve().parent!=Path(self.folder.name).resolve():continue
                sink=self.sink
                if sink:sink(event)
        except (OSError,ValueError):pass
        sink=self.sink
        if sink:sink({'event':'error','message':'Listener stopped'})

    def attach(self,sink):self.sink=sink
    def detach(self,sink):
        if self.sink is sink:self.sink=None

    def record(self,kind,payload):
        with self.write:
            self.process.stdin.write(kind+struct.pack('<I',len(payload))+payload);self.process.stdin.flush()

    def send_audio(self,data):self.record(b'A',data)
    def mode(self,standby):self.record(b'M',json.dumps({'standby':bool(standby)}).encode())

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        for pipe in (self.process.stdin,self.process.stdout):
            try:pipe.close()
            except OSError:pass
        self.folder.cleanup()


def shared():
    global _shared
    if not ready():raise ValueError('Live listening is not installed; run scripts/setup-local-voice.py')
    with _lock:
        if _shared is None or _shared.process.poll() is not None:
            if _shared:_shared.close()
            _shared=Listener()
        return _shared


def shutdown():
    global _shared
    with _lock:
        if _shared:_shared.close();_shared=None

atexit.register(shutdown)
