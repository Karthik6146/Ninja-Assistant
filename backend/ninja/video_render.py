"""Validated FFmpeg subset; keeps editable plans and portable source bundles."""
import copy,hashlib,json,os,shutil,time,uuid
from pathlib import Path
from . import db,media,content,video_sources as sources
from .config import DATA,artifact
from .schemas import Style,EDL

def captions_for(value,plan):
    assets={a['id']:a for a in value['assets']};words=[];offset=0
    for s in plan['segments']:
        words+=sources.retime_words(assets[s['asset']].get('transcript',{}).get('words',[]),s['start'],s['end'],s['speed'],offset)
        offset+=(s['end']-s['start'])/s['speed']
    captions=[];group=[]
    for w in words:
        if group and (len(group)>=7 or w['start']-group[-1]['end']>.6 or w['end']-group[0]['start']>3):
            captions.append(group);group=[]
        group.append(w)
    if group:captions.append(group)
    return [{'start':g[0]['start'],'end':max(w['end'] for w in g),'text':' '.join(w['text'] for w in g),'words':[{'word':w['text'],'start':w['start'],'end':w['end']} for w in g]} for g in captions]

def one(value,plan,job,work,preview):
    output=work/'video.mp4';receipt=work/'verified.json'
    if receipt.exists() and output.is_file():
        cached=json.loads(receipt.read_text(encoding='utf-8'))
        with output.open('rb') as handle:sha=hashlib.file_digest(handle,'sha256').hexdigest()
        if cached['sha256']==sha:return cached
        raise ValueError('Previously verified output changed on disk; save a new edit revision before rebuilding')
    assets={a['id']:a for a in value['assets']};w,h={'9:16':(720,1280),'16:9':(1280,720),'1:1':(720,720)}[plan['aspect']]
    if preview:w//=2;h//=2
    duration=sum((s['end']-s['start'])/s['speed'] for s in plan['segments'])
    if shutil.disk_usage(work).free<duration*2_000_000+512*1024**2:raise ValueError('Insufficient render space')
    captions=captions_for(value,plan) if plan['captions'] else []
    style=Style(size=max(12,round(32*w/720))).model_dump()
    overlay=media.ass(captions,style,w,h)
    if plan['title']:
        title_style=style|{'placement':'top'}
        title=media.ass([{'start':0,'end':min(4,duration),'text':plan['title']}],title_style,w,h)
        overlay+=title.split('[Events]\n',1)[1].split('\n',1)[1].replace(',0,0,0,,',',0,0,0,,{\\an8}')
    (work/'captions.ass').write_text(overlay,encoding='utf-8')
    for ext in ('srt','vtt'):(work/('captions.'+ext)).write_text(media.caption_export(captions,ext),encoding='utf-8')
    args=['ffmpeg','-hide_banner','-y'];filters=[]
    for i,s in enumerate(plan['segments']):
        a=assets[s['asset']];length=(s['end']-s['start'])/s['speed']
        args+=['-ss',str(s['start']),'-t',str(s['end']-s['start']),'-protocol_whitelist','file,pipe','-i',a['path']]
        sw=int(w*s['zoom']/2)*2;sh=int(h*s['zoom']/2)*2
        vf=f"setpts=(PTS-STARTPTS)/{s['speed']},scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-ow)*{s['crop_x']}:(ih-oh)*{s['crop_y']},setsar=1,fps={plan['fps']}"
        if 'contrast' in plan['effects']:vf+=',eq=contrast=1.04:saturation=1.05'
        if 'slow_zoom' in plan['effects']:vf+=f",zoompan=z='1+0.035*on/{max(1,round(length*plan['fps']))}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={w}x{h}:fps={plan['fps']}"
        if 'fade' in plan['effects']:vf+=f',fade=t=in:d=0.15,fade=t=out:st={max(0,length-.15)}:d=0.15'
        filters.append(f'[{i}:v]{vf}[v{i}]')
        af=f"asetpts=PTS-STARTPTS,atempo={s['speed']},volume={s['volume']},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={length}"
        filters.append(f'[{i}:a]{af}[a{i}]' if a['metadata']['audio'] else f'anullsrc=r=48000:cl=stereo,atrim=duration={length}[a{i}]')
    filters.append(''.join(f'[v{i}][a{i}]' for i in range(len(plan['segments'])))+f"concat=n={len(plan['segments'])}:v=1:a=1[v][a]")
    filters.append('[v]subtitles=captions.ass[outv]')
    audio='[a]';mix=['[a]'];input_index=len(plan['segments'])
    if plan['audio_project']:
        p=db.project(plan['audio_project']);args+=['-stream_loop','-1','-protocol_whitelist','file,pipe','-i',str(artifact(p['id'],p['music']))]
        filters.append(f"[{len(plan['segments'])}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,volume={plan['audio_volume']}[music]")
        mix.append('[music]');input_index+=1
    for i,cue in enumerate(plan['sound_effects']):
        p=db.project(cue['project'])
        args+=['-ss',str(cue['source_start']),'-t',str(cue['duration']),'-protocol_whitelist','file,pipe','-i',str(artifact(p['id'],p['music']))]
        filters.append(f"[{input_index}:a]asetpts=PTS-STARTPTS,volume={cue['volume']},adelay={round(cue['start']*1000)}:all=1[sfx{i}]")
        mix.append(f'[sfx{i}]');input_index+=1
    if len(mix)>1:
        filters.append(''.join(mix)+f'amix=inputs={len(mix)}:duration=first:normalize=0[outa]');audio='[outa]'
    args+=['-filter_complex',';'.join(filters),'-map','[outv]','-map',audio,'-c:v','libx264','-preset','veryfast','-crf','28' if preview else '20','-pix_fmt','yuv420p','-c:a','aac','-t',str(duration),'-movflags','+faststart','-progress','pipe:1','-nostats',str(output)]
    media.run(args,job,duration,work)
    metadata=media.probe(output)
    if abs(metadata['duration']-duration)>.5 or not metadata['audio'] or (metadata['width'],metadata['height'])!=(w,h):raise ValueError('Rendered duration, dimensions or audio failed validation')
    media.run(['ffmpeg','-v','error','-protocol_whitelist','file,pipe','-i',str(output),'-f','null','-'],job,timeout=1800)
    with output.open('rb') as handle:sha=hashlib.file_digest(handle,'sha256').hexdigest()
    result={'metadata':metadata,'sha256':sha}
    sources.atomic(receipt,result);return result

def copy_source(source,target):
    if target.exists():
        with source.open('rb') as src,target.open('rb') as dst:
            if source.stat().st_size==target.stat().st_size and hashlib.file_digest(src,'sha256').digest()==hashlib.file_digest(dst,'sha256').digest():return
        raise ValueError('An existing bundle file differs from its source; choose a new destination or revision')
    # Copy originals: the editable bundle stays independent of mutable source files.
    if shutil.disk_usage(target.parent).free<source.stat().st_size+512*1024**2:raise ValueError('Insufficient space for portable source bundle')
    tmp=target.with_suffix(target.suffix+'.part');shutil.copy2(source,tmp);tmp.replace(target)

def register(value,index,work,metadata):
    """Register the actual verified render in the existing publishing pipeline."""
    id=uuid.uuid5(uuid.NAMESPACE_URL,f"ninja:{value['id']}:{value['revision']}:{index}").hex
    target=artifact(id,'final.mp4');target.parent.mkdir(parents=True,exist_ok=True);copy_source(work/'video.mp4',target)
    edl=EDL(clips=[{'start':0,'end':metadata['duration']}],captions=[]).model_dump()
    p={'id':id,'name':value['name']+f' · {index+1}','source':'final.mp4','metadata':metadata,'edl':edl,'suggestions':[],'video_workflow':value['id']}
    result={'file':'final.mp4','metadata':metadata,'revision':0,'preview':False,'video_workflow':value['id']}
    with db.connect() as c:
        c.execute('INSERT OR IGNORE INTO projects VALUES(?,?,?,?)',(id,p['name'],db.encode(p),time.time()))
        # This record describes the completed render, not a second render request.
        c.execute("INSERT OR IGNORE INTO jobs(id,project,kind,payload,state,result,progress,created,finished,step) VALUES(?,?,'render',?,'completed',?,1,?,?,?)",(id,id,db.encode({'video_workflow':value['id']}),db.encode(result),time.time(),time.time(),'Video workflow render verified'))
        row=c.execute('SELECT body FROM packages WHERE id=?',(id,)).fetchone()
    if not row:
        package=content.create(id,package_id=id);old=copy.deepcopy(package);package['rights']=value['request']['rights'];package['platforms']['youtube']['media']='final.mp4';package['platforms']['youtube']['title']=p['name'][:100];content.save(package,old)
    return id

def render(value,job,preview):
    from .video import folder,destination,validate_plan
    kind='preview' if preview else 'render';outputs=[]
    for index,raw in enumerate(value['plans']):
        plan=validate_plan(value,raw).model_dump();work=folder(value['id'])/f"v{value['revision']}-{kind}-{index+1}";work.mkdir(exist_ok=True)
        db.update_job(job,step=f'{kind}: clip {index+1}/{len(value["plans"])} · FFmpeg supported subset')
        result=one(value,plan,job,work,preview);entry={'index':index,'revision':value['revision'],'preview':preview,'file':str(work/'video.mp4'),**result}
        if not preview:
            bundle=destination(value['request']['destination'])/f"ninja-{value['id']}-v{value['revision']}";bundle.mkdir(parents=True,exist_ok=True)
            assets=[]
            for a in value['assets']:
                target=bundle/'sources'/(a['id']+Path(a['path']).suffix);target.parent.mkdir(exist_ok=True);copy_source(Path(a['path']),target);assets.append({k:v for k,v in a.items() if k not in ('path','transcript','evidence')}|{'path':target.relative_to(bundle).as_posix()})
            sources.atomic(bundle/'source-manifest.json',assets);sources.atomic(bundle/'edit-plans.json',value['plans'])
            for document in folder(value['id']).glob(f"openchatcut-v{value['revision']}-*.json"):copy_source(document,bundle/document.name)
            audio_assets={}
            for audio_id in dict.fromkeys(([plan['audio_project']] if plan['audio_project'] else [])+[c['project'] for c in plan['sound_effects']]):
                p=db.project(audio_id);name='audio-'+audio_id+Path(p['music']).suffix
                copy_source(artifact(p['id'],p['music']),bundle/name);audio_assets[audio_id]=name
            sources.atomic(bundle/f'clip-{index+1}-audio-manifest.json',audio_assets)
            for name in ('video.mp4','captions.srt','captions.vtt','captions.ass'):copy_source(work/name,bundle/(f'clip-{index+1}-'+name))
            entry['bundle']=str(bundle);entry['package']=register(value,index,work,result['metadata'])
        outputs.append(entry)
    value['outputs']=[o for o in value['outputs'] if not(o['preview']==preview and o['revision']==value['revision'])]+outputs
    return {'outputs':outputs,'editor':'FFmpeg subset: cuts, speed, manual crop, gentle zoom, fades, contrast, title, supplied audio and ClipX captions'}
