"""Bounded ingestion, evidence extraction and external ClipX transcription."""
import hashlib,json,math,os,re,shutil,time
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from filelock import FileLock
from . import db,media,workspace
from .config import DATA

def youtube_id(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443):raise ValueError('Use a public HTTPS YouTube video URL')
    if p.hostname in ('youtube.com','www.youtube.com','m.youtube.com'):
        value=parse_qs(p.query).get('v',[''])[0] if p.path=='/watch' else p.path.split('/')[-1] if p.path.startswith(('/shorts/','/live/')) else ''
    elif p.hostname=='youtu.be':value=p.path.strip('/')
    else:raise ValueError('Only user-supplied YouTube video URLs are supported')
    if not re.fullmatch(r'[\w-]{11}',value):raise ValueError('Supply a single video URL; choose playlist items explicitly as individual URLs')
    return value

def atomic(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(db.encode(value),encoding='utf-8');temporary.replace(path)

def download(url,job):
    import yt_dlp
    id=youtube_id(url);folder=DATA/'video-sources'/('yt-'+id);folder.mkdir(parents=True,exist_ok=True)
    manifest=folder/'source.json'
    with FileLock(folder/'download.lock',timeout=1):
        if manifest.exists():
            saved=json.loads(manifest.read_text(encoding='utf-8'))
            cached=(folder/saved['file']).resolve()
            if not cached.is_relative_to(folder.resolve()):raise ValueError('Source manifest path escaped its cache')
            if cached.is_file():
                metadata=media.probe(cached)
                if abs(metadata['duration']-saved['duration'])>.1:raise ValueError('Cached source changed; inspect the source cache before retrying')
                return saved|{'path':str(cached),'cached':True}
        def progress(item):
            if db.cancelled(job):raise media.Cancelled()
            total=item.get('total_bytes') or item.get('total_bytes_estimate') or 0
            if item.get('downloaded_bytes',0)>4*1024**3:raise ValueError('Download exceeds 4 GB limit')
            if shutil.disk_usage(folder).free<1024**3:raise ValueError('Less than 1 GB free during download')
            db.update_job(job,progress=min(.95,item.get('downloaded_bytes',0)/total) if total else 0)
        def allowed(info,*,incomplete):
            if info.get('is_live'):return 'Live streams are not supported; use a completed recording'
            if (info.get('duration') or 0)>14400:return 'Source exceeds four-hour limit'
        options={'outtmpl':str(folder/'source.%(ext)s'),'format':'bv*[height<=1080]+ba/b[height<=1080]',
                 'merge_output_format':'mp4','noplaylist':True,'retries':2,'fragment_retries':2,'extractor_retries':2,
                 'socket_timeout':20,'max_filesize':4*1024**3,'concurrent_fragment_downloads':1,
                 'progress_hooks':[progress],'match_filter':allowed,'quiet':True,'no_warnings':True,'noprogress':True,
                 'js_runtimes':{'node':{}},'remote_components':set(),'cachedir':str(DATA/'yt-dlp-cache')}
        try:
            with yt_dlp.YoutubeDL(options) as ydl:info=ydl.extract_info('https://www.youtube.com/watch?v='+id,download=True)
        except yt_dlp.utils.DownloadError as e:
            if db.cancelled(job):raise media.Cancelled() from None
            message=str(e).lower()
            reason='YouTube requires sign-in or access permission' if any(x in message for x in ('sign in','private','members-only','cookies','bot')) else 'Video unavailable, restricted, or download failed'
            raise ValueError(reason+'. No cookies or access bypass were attempted. Use an authorized local copy or retry later.') from None
        if not info:raise ValueError('Video does not meet the duration/live-stream limits')
        paths=[p for p in folder.glob('source.*') if p.suffix in ('.mp4','.webm','.mkv')]
        if len(paths)!=1:raise ValueError('Download did not produce one complete video')
        metadata=media.probe(paths[0]);saved={'id':'yt-'+id,'video_id':id,'url':url,'title':info.get('title',id),'duration':metadata['duration'],'metadata':metadata,'file':paths[0].name,'status':'downloaded','license':info.get('license'),'downloaded':time.time()}
        atomic(manifest,saved);return saved|{'path':str(paths[0]),'cached':False}

def retime_words(words,start,end,speed=1,offset=0):
    return [dict(text=w['text'],start=round(offset+(max(start,w['start'])-start)/speed,4),end=round(offset+(min(end,w['end'])-start)/speed,4)) for w in words if min(end,w['end'])>max(start,w['start'])]

def caption_config():
    with db.connect() as c:row=c.execute("SELECT value FROM preferences WHERE key='caption_tool'").fetchone()
    value=json.loads(row[0]) if row else {}
    # No built-in default: a guessed folder could be created by someone else and its python run as the owner.
    folder=value.get('path') or os.getenv('CAPTION_TOOL_PATH')
    if not folder:raise ValueError('Set the Caption Tool folder in Settings (your standalone ClipX folder).')
    root=Path(folder)
    return root,root/'.venv-whisper/Scripts/python.exe',root/'packages/ai/scripts/transcribe-local.py'

def transcribe(path,folder,job,language='auto'):
    root,python,script=caption_config()
    if not python.is_file() or not script.is_file():raise ValueError('ClipX CLI missing. Set Caption Tool path in Settings to your standalone ClipX folder.')
    models=sorted((root/'.models/whisper/models--dropbox-dash--faster-whisper-large-v3-turbo/snapshots').glob('*/model.bin'))
    if not models:raise ValueError('ClipX local model is not installed. Complete ClipX setup first; Ninja does not install another ASR model.')
    fingerprint=hashlib.sha256((str(path.resolve())+str(path.stat().st_size)+str(path.stat().st_mtime_ns)+str(script.stat().st_mtime_ns)+str(models[0])+language).encode()).hexdigest()
    cache=folder/('transcript-'+fingerprint[:16]+'.json')
    if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))
    audio=folder/'speech.wav'
    media.run(['ffmpeg','-y','-v','error','-protocol_whitelist','file,pipe','-i',str(path),'-vn','-ar','16000','-ac','1','-c:a','pcm_s16le',str(audio)],job,timeout=1800)
    env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PYTHONIOENCODING':'utf-8'}
    dlls=Path(os.getenv('CAPTION_CUDA_DLL_PATH',str(Path(os.getenv('LOCALAPPDATA',''))/'Programs/Ollama/lib/ollama/cuda_v12')))
    device=os.getenv('CAPTION_TOOL_DEVICE','cuda' if (dlls/'cublas64_12.dll').is_file() else 'cpu')
    if device not in ('cpu','cuda'):raise ValueError('CAPTION_TOOL_DEVICE must be cpu or cuda')
    if device=='cuda':env['PATH']=str(dlls)+os.pathsep+env.get('PATH','')
    from contextlib import nullcontext
    with FileLock(DATA/'model.lock',timeout=1) if device=='cuda' else nullcontext():
        if device=='cuda':
            from . import adapters
            adapters.unload_local_models()
        result=json.loads(media.run([str(python),str(script),'--audio',str(audio),'--model',str(models[0].parent),'--device',device,'--language','hi' if language=='hinglish' else language,'--alignment','native'],job,cwd=root,timeout=7200,env=env))
    result['device']=device
    if language=='hinglish':
        from .config import ROOT
        intermediate=folder/'hinglish-input.json';atomic(intermediate,result)
        loader=root/'node_modules/tsx/dist/loader.mjs'
        if not loader.is_file():raise ValueError('ClipX tsx runtime missing; complete the standalone tool setup for Hinglish')
        media.run(['node','--import',loader.as_uri(),str(ROOT/'scripts/clipx-hinglish.mjs'),str(root),str(intermediate)],job,cwd=root,timeout=60)
        result=json.loads(intermediate.read_text(encoding='utf-8'))
    words=result.get('words',[])
    if not isinstance(words,list) or len(words)>200000:raise ValueError('ClipX returned an invalid transcript')
    for w in words:
        if not isinstance(w.get('text'),str) or not w['text'].strip() or not all(type(w.get(k)) in (int,float) and math.isfinite(w[k]) for k in ('start','end')) or not 0<=w['start']<w['end']<=result['duration']+1:raise ValueError('ClipX returned invalid word timing')
    result['provider']='ClipX local CLI';result['cache_key']=fingerprint;atomic(cache,result);return result

def evidence(path,folder,job,metadata):
    fingerprint=hashlib.sha256((str(path.resolve())+str(path.stat().st_size)+str(path.stat().st_mtime_ns)).encode()).hexdigest()[:16]
    cache=folder/('evidence-'+fingerprint+'.json')
    if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))
    # Scene scores operate on downscaled video; save only timestamps and 12 review frames.
    scene=media.run(['ffmpeg','-hide_banner','-protocol_whitelist','file,pipe','-i',str(path),'-an','-vf',"scale=160:-2,select='gt(scene,0.35)',showinfo",'-vsync','vfr','-f','null','-'],job,timeout=3600,include_stderr=True)
    cuts=[float(x) for x in re.findall(r'pts_time:([\d.]+)',scene)]
    silence=[]
    if metadata['audio']:
        output=media.run(['ffmpeg','-hide_banner','-protocol_whitelist','file,pipe','-i',str(path),'-vn','-af','silencedetect=noise=-32dB:d=0.4','-f','null','-'],job,timeout=1800,include_stderr=True)
        silence=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',output)]
    interval=max(1,metadata['duration']/12)
    media.run(['ffmpeg','-v','error','-y','-protocol_whitelist','file,pipe','-i',str(path),'-vf',f'fps=1/{interval},scale=480:-2','-frames:v','12',str(folder/(fingerprint+'-%02d.jpg'))],job,timeout=900)
    value={'scene_boundaries':cuts,'speech_resumptions':silence,'sample_interval':interval,'frames':[p.name for p in sorted(folder.glob(fingerprint+'-*.jpg'))],'visual_analysis':'Sampled frames for model/manual review; no subject tracking inferred'}
    atomic(cache,value);return value

def select_candidates(duration,words,cuts,speech,count,seconds):
    if duration<30:return []
    length=min(seconds,duration);starts={0.0,*[round(t,3) for t in cuts+speech if 0<=t<=duration-30],*[float(t) for t in range(0,int(duration-length)+1,max(30,int(length)))]}
    # ponytail: deterministic evidence pool, cap at 2000 starts for long recordings.
    pool=[]
    for start in sorted(starts)[:2000]:
        near=[w['start'] for w in words if start<=w['start']<=start+2]
        if near:start=near[0]
        end=min(duration,start+length)
        ends=[w['end'] for w in words if end-3<=w['end']<=end+3 and 30<=w['end']-start<=180]
        if ends:end=min(ends,key=lambda t:abs(t-end))
        if not 30<=end-start<=180:continue
        selected=[w for w in words if start<=w['start']<end]
        scenes=sum(start<=t<end for t in cuts);resume=sum(start<=t<end for t in speech)
        score=min(.4,len(selected)/150*.4)+min(.25,scenes*.025)+min(.1,resume*.025)
        pool.append({'start':round(start,3),'end':round(end,3),'duration':round(end-start,3),'score':round(score,3),'confidence':round(.35+score/2,2),'reason':f'{len(selected)} spoken words, {scenes} scene changes, {resume} speech resumptions. Boundary-aligned heuristic; review setup and payoff.','excerpt':' '.join(w['text'] for w in selected)[:700]})
    output=[]
    for candidate in sorted(pool,key=lambda c:c['score'],reverse=True):
        if all(min(candidate['end'],other['end'])<=max(candidate['start'],other['start']) for other in output):output.append(candidate|{'id':str(len(output)+1)})
        if len(output)>=count:break
    return output
