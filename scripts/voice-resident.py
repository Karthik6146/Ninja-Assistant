"""Pipe-only adapter reusing the installed ClipX CLI with one cached CPU model."""
import importlib.util,json,os,queue,re,sys,threading,time,wave
from contextlib import redirect_stdout
from pathlib import Path


def serve(script,model,folder):
    sys.path.insert(0,str(script.parent))
    import faster_whisper
    original=faster_whisper.WhisperModel;cached=None;device='cpu'
    def load(value,*args,**kwargs):
        nonlocal cached,device
        if (args or Path(value).resolve()!=model or (kwargs.get('device'),kwargs.get('compute_type')) not in (('cpu','int8'),('cuda','int8_float16'))
                or not kwargs.get('local_files_only')):
            raise ValueError('Unsupported speech model configuration')
        if cached is None:
            try:cached=original(value,**kwargs);device=kwargs['device']
            except Exception:
                # Missing CUDA libraries or no free GPU memory: keep voice working on CPU.
                if kwargs.get('device')!='cuda':raise
                cached=original(value,**{**kwargs,'device':'cpu','compute_type':'int8'});device='cpu'
        return cached
    # ClipX exposes a CLI, so retain its full main() and replace only model loading.
    faster_whisper.WhisperModel=load
    spec=importlib.util.spec_from_file_location('clipx_voice',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    incoming=queue.Queue(maxsize=1)
    def read():
        while True:
            line=sys.stdin.buffer.readline(1025)
            incoming.put(line)
            if not line:return
    threading.Thread(target=read,daemon=True).start()
    while True:
        try:line=incoming.get(timeout=600)
        except queue.Empty:return
        if not line:return
        started=time.monotonic();warm=cached is not None;request={};audio=folder/'utterance.wav'
        try:
            if len(line)>1024 or not line.endswith(b'\n'):raise ValueError('Invalid request size')
            request=json.loads(line)
            if (not isinstance(request,dict) or set(request)!={'id','language'} or not isinstance(request['id'],str) or not re.fullmatch(r'[0-9a-f]{32}',request['id'])
                    or request['language'] not in ('auto','en','hi','hi-latn')):
                raise ValueError('Invalid speech request')
            if audio.is_symlink():raise ValueError('Invalid audio file')
            with wave.open(str(audio),'rb') as stream:
                if (stream.getframerate()!=16000 or stream.getnchannels()!=1 or stream.getsampwidth()!=2
                        or not 0<stream.getnframes()<=960000):raise ValueError('Invalid bounded audio')
            sys.argv=[str(script),'--audio',str(audio),'--model',str(model),'--device',DEVICE,
                      '--language',request['language'],'--alignment','native']
            value=module.main()
            frame={'id':request['id'],'value':value,'warm':warm,'recognition_ms':round((time.monotonic()-started)*1000),'device':device}
            encoded=json.dumps(frame,ensure_ascii=True)
            if len(encoded)>256000:raise ValueError('Speech response is too large')
        except Exception:
            # No transcript or library exception text goes into logs or error replies.
            encoded=json.dumps({'id':request.get('id') if isinstance(request,dict) else None,'error':'ClipX speech recognition failed. Retry or check Caption Tool and the cached model in Settings.'})
        finally:audio.unlink(missing_ok=True)
        sys.__stdout__.write(encoded+'\n');sys.__stdout__.flush()


# GPU recognition is ~0.25 s per turn against ~2.2 s on CPU; JARVIS_VOICE_DEVICE=cpu opts out.
DEVICE='cpu' if os.environ.get('JARVIS_VOICE_DEVICE')=='cpu' else 'cuda'

if __name__=='__main__':
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONIOENCODING='utf-8')
    # pip-installed NVIDIA cuBLAS/cuDNN DLLs live in site-packages; CTranslate2 finds them only via PATH.
    nvidia=Path(sys.prefix)/'Lib'/'site-packages'/'nvidia'
    os.environ['PATH']=os.pathsep.join(str(d) for d in nvidia.glob('*/bin'))+os.pathsep+os.environ.get('PATH','')
    with open(os.devnull,'w') as quiet,redirect_stdout(quiet):
        serve(*(Path(value).resolve() for value in sys.argv[1:]))
