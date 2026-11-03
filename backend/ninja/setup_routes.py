"""First-run setup: read this PC's specs, rank the Jarvis models it can run, and install Ollama, a model and the voice
models in the background with progress the wizard polls. Each install starts only from the user's click."""
import ctypes,json,os,shutil,subprocess,sys,threading,time,winreg
from pathlib import Path
import httpx
from fastapi import APIRouter
from pydantic import Field
from . import adapters,db,listener,neural_voice
from .agent_models import Strict
from .config import ROOT
router=APIRouter(prefix='/api/setup')

# Ollama's qwen3.5 tags (ollama.com/library/qwen3.5/tags, Q4_K_M, Nov 2026): download size in GB. In memory at Ninja's
# 8k context a model takes about its download size; qwen3.5:9b measured 5.6 GB loaded for a 6.6 GB download.
CATALOG=[
    {'model':'qwen3.5:0.8b','size':1.2,'label':'Tiny','note':'Runs anywhere; often misses tools and facts.'},
    {'model':'qwen3.5:2b','size':2.7,'label':'Small','note':'Quick chats on modest PCs; basic tool use.'},
    {'model':'qwen3.5:4b','size':3.3,'label':'Balanced','note':'Good tool use and replies; the pick for 6 GB GPUs.'},
    {'model':'qwen3.5:9b','size':6.6,'label':'Best for 8 GB GPUs','note':'Ninja is tuned on this model.'},
    {'model':'qwen3.5:27b','size':17,'label':'Large','note':'Smartest replies; needs a 24 GB GPU to be quick.'},
]
CREATE_NO_WINDOW=0x08000000 if os.name=='nt' else 0

def system():
    """RAM, CPU, disk and GPU as Windows reports them; any part that cannot be read is None."""
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','free','page_total','page_free','virtual_total','virtual_free','extended')]
    memory=Memory();memory.length=ctypes.sizeof(Memory)
    ram=memory.total if os.name=='nt' and ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)) else None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:cpu=winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
    except OSError:cpu=None
    from .assistant_routes import gpu
    nvidia=gpu()
    others=[]
    if not nvidia:
        # Ollama on Windows accelerates NVIDIA and some AMD cards; others are listed so the user sees why it runs on CPU.
        try:
            out=subprocess.run(['powershell','-NoProfile','-Command','(Get-CimInstance Win32_VideoController).Name'],capture_output=True,text=True,timeout=10,creationflags=CREATE_NO_WINDOW).stdout
            others=[line.strip() for line in out.splitlines() if line.strip()]
        except (OSError,subprocess.SubprocessError):pass
    return {'ram':ram,'cpu':cpu,'cores':os.cpu_count(),'disk_free':shutil.disk_usage(ROOT).free,
            'gpu':nvidia and {'name':nvidia['name'],'vram':nvidia['memory_total']},'other_gpus':others}

def fit(specs):
    """Each catalog model rated for this PC: gpu (all in VRAM, fast), cpu (spills to RAM, slow), no (does not fit).
    The recommendation is the largest model that fits the GPU; without one, the largest that fits RAM, up to 4b."""
    gib=2**30;vram=(specs['gpu'] or {}).get('vram') or 0;ram=specs['ram'] or 0;disk=specs['disk_free']
    rated=[]
    for m in CATALOG:
        need=m['size']*gib
        rating='no' if need+gib>disk else 'gpu' if vram and need+0.8*gib<=vram else 'cpu' if need+5*gib<=ram+vram else 'no'  # 5 GB left for Windows and the app
        rated.append({**m,'fit':rating})
    on_gpu=[m for m in rated if m['fit']=='gpu']
    on_cpu=[m for m in rated if m['fit']=='cpu' and m['size']<=3.3]
    pick=(on_gpu or on_cpu or [None])[-1]
    return rated,pick and pick['model']

def ollama_state():
    try:
        tags=httpx.get(adapters.ollama_url()+'/api/tags',timeout=3,trust_env=False).raise_for_status().json()
        return {'installed':True,'running':True,'models':[m['name'] for m in tags.get('models',[])]}
    except (httpx.HTTPError,ValueError):
        return {'installed':bool(ollama_exe()),'running':False,'models':[]}

def ollama_exe():
    found=shutil.which('ollama')
    default=Path(os.getenv('LOCALAPPDATA',''))/'Programs/Ollama/ollama.exe'
    return found or (str(default) if default.is_file() else None)

# Background tasks: one of each kind at a time, kept in memory; the wizard polls GET /api/setup.
TASKS:dict[str,dict]={}
LOCK=threading.Lock()

def run(kind,work):
    with LOCK:
        if TASKS.get(kind,{}).get('state')=='running':raise ValueError('That step is already running')
        TASKS[kind]={'state':'running','progress':None,'message':'Starting…','started':time.time()}
    def body():
        try:
            work(TASKS[kind]);TASKS[kind].update(state='done',progress=1)
        except Exception as e:  # Shown in the wizard; the user can retry.
            TASKS[kind].update(state='failed',message=db.safe_error(e) if isinstance(e,ValueError) else str(e)[:300])
    threading.Thread(target=body,daemon=True).start()

def install_ollama(task):
    if not ollama_exe():
        if not shutil.which('winget'):raise ValueError('winget is missing. Install Ollama from ollama.com/download, then press Check again')
        task['message']='Installing Ollama with winget…'
        done=subprocess.run(['winget','install','--id','Ollama.Ollama','-e','--silent','--accept-source-agreements','--accept-package-agreements'],
                            capture_output=True,text=True,timeout=1800,creationflags=CREATE_NO_WINDOW)
        detail=(done.stdout or done.stderr or '').strip().splitlines()
        if not ollama_exe():raise ValueError('winget could not install Ollama'+(' ('+detail[-1][:160]+')' if detail else '')+'. Install it from ollama.com/download')
    if not ollama_state()['running']:
        task['message']='Starting Ollama…'
        subprocess.Popen([ollama_exe(),'serve'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=CREATE_NO_WINDOW)
        for _ in range(60):
            if ollama_state()['running']:break
            time.sleep(1)
        else:raise ValueError('Ollama is installed but did not start. Open Ollama from the Start menu, then press Check again')
    task['message']='Ollama is running'

def pull(model):
    def work(task):
        task['message']='Connecting to Ollama…'
        with httpx.Client(timeout=httpx.Timeout(60,read=600),trust_env=False) as client,client.stream('POST',adapters.ollama_url()+'/api/pull',json={'model':model,'stream':True}) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:continue
                event=json.loads(line)
                if event.get('error'):raise ValueError('Ollama: '+event['error'][:200])
                total,completed=event.get('total'),event.get('completed')
                if total and completed is not None:task.update(progress=completed/total,message=f"Downloading {model}: {completed/2**30:.1f} of {total/2**30:.1f} GB")
                else:task['message']=str(event.get('status','Working…')).capitalize()
        with db.connect() as c:
            c.execute("INSERT OR REPLACE INTO preferences VALUES('chat_provider','ollama')")
            c.execute("INSERT OR REPLACE INTO preferences VALUES('ollama_model',?)",(model,))
        task['message']=model+' is ready and selected for Jarvis'
    return work

def install_voice(task):
    task['message']='Downloading speech models (about 1.5 GB)…'
    process=subprocess.Popen([sys.executable,str(ROOT/'scripts/setup-local-voice.py'),'--project',str(ROOT)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                             text=True,encoding='utf-8',errors='replace',creationflags=CREATE_NO_WINDOW)
    last=''
    for line in process.stdout:
        line=line.strip()
        if line:last=line;task['message']=line[:160]
    if process.wait():raise ValueError('Voice setup stopped: '+last[:200])
    task['message']='Voice is ready'

class Pull(Strict):
    model:str=Field(min_length=1,max_length=100)

@router.get('')
def state():
    specs=system();models,pick=fit(specs)
    return {'system':specs,'models':models,'recommended':pick,'ollama':ollama_state(),'current':adapters.local_model(),
            'voice':{'ready':neural_voice.status()['ready'] and listener.ready()},'tasks':TASKS}

@router.post('/ollama')
def setup_ollama():run('ollama',install_ollama);return {'started':True}

@router.post('/pull')
def setup_pull(body:Pull):
    # Only catalog models: the wizard is not a general downloader.
    if body.model not in {m['model'] for m in CATALOG}:raise ValueError('Choose one of the listed models')
    if not ollama_state()['running']:raise ValueError('Start Ollama first')
    run('pull',pull(body.model));return {'started':True}

@router.post('/voice')
def setup_voice():run('voice',install_voice);return {'started':True}
