import json
import math
import shutil
import subprocess
import time
from pathlib import Path
from . import db
from .config import artifact
from .schemas import EDL

class Cancelled(Exception): pass

def run(args, job=None, duration=None, cwd=None, timeout=3600, env=None, include_stderr=False, expected_attempt=None, started=None):
    """started: an already running (process, stdout file, stderr file), e.g. a pre-warmed runner; it is supervised the same way."""
    if job and expected_attempt is not None:db.check_lease(job,expected_attempt)
    if job:
        db.event(job,'tool',f'Run {Path(args[0]).name}; timeout {timeout}s')
    # Drain both pipes to disk: no unbounded in-memory subprocess output.
    import tempfile
    files=started[1:] if started else (tempfile.TemporaryFile(),tempfile.TemporaryFile())
    with files[0] as out, files[1] as err:
        p=started[0] if started else subprocess.Popen(args, stdout=out, stderr=err, cwd=cwd, shell=False, env=env)
        started=time.monotonic()
        try:
            while p.poll() is None:
                if job and db.cancelled(job): raise Cancelled('Cancelled')
                if time.monotonic()-started>timeout: raise TimeoutError('Tool timeout')
                if job:
                    db.update_job(job,expected_attempt=expected_attempt,heartbeat=time.time())
                    if duration:
                        out.seek(0,2); size=out.tell(); out.seek(max(0,size-16000))
                        lines=out.read(16000).decode(errors='replace').splitlines()
                        for line in reversed(lines):
                            if line.startswith('out_time_us='):
                                db.update_job(job,expected_attempt=expected_attempt,progress=min(0.98,int(line.split('=')[1])/1e6/duration))
                                break
                time.sleep(0.25)
            err.seek(0); error=err.read()[-12000:].decode(errors='replace')
            if p.returncode:
                out.seek(0,2); size=out.tell(); out.seek(max(0,size-12000))
                stdout=out.read(12000).decode(errors='replace')
                raise RuntimeError((stdout+'\n'+error).strip() or f'Tool exit {p.returncode}')
            out.seek(0); result=out.read(2_000_000).decode(errors='replace')
            if include_stderr:
                err.seek(0);result+='\n'+err.read(2_000_000).decode(errors='replace')
            return result
        finally:
            if p.poll() is None:
                import psutil
                try: children=psutil.Process(p.pid).children(recursive=True)
                except psutil.Error: children=[]
                for child in children:
                    try: child.terminate()
                    except psutil.Error: pass
                p.terminate()
                try: p.wait(timeout=3)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
                for child in children:
                    try:
                        if child.is_running(): child.kill()
                    except psutil.Error: pass

def probe(path,audio_only=False):
    formats='mov,mp3,wav,ogg,aac' if audio_only else 'mov,matroska,webm,avi'
    info=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-format_whitelist',formats,'-show_format','-show_streams','-of','json',str(path)],timeout=30))
    video=next((s for s in info['streams'] if s['codec_type']=='video'),None)
    if not video and not audio_only: raise ValueError('No decodable video stream')
    duration=float(info['format'].get('duration',0))
    if not math.isfinite(duration) or duration<=0: raise ValueError('Invalid duration')
    if audio_only:
        if not any(s['codec_type']=='audio' for s in info['streams']):raise ValueError('No decodable audio stream')
        return {'duration':duration,'audio':True}
    return {'duration':duration,'width':video['width'],'height':video['height'],'fps':video.get('avg_frame_rate'),'codec':video.get('codec_name'),'audio':any(s['codec_type']=='audio' for s in info['streams'])}

def stamp(seconds, vtt=False):
    ms=round(seconds*1000)
    h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02}{"." if vtt else ","}{ms:03}'

def caption_export(captions, kind):
    if kind=='json': return json.dumps(captions,ensure_ascii=False,indent=2)
    result='WEBVTT\n\n' if kind=='vtt' else ''
    for i,c in enumerate(captions):
        text=c['text'].replace('-->', '→')
        result+=f'{i+1}\n{stamp(c["start"],kind=="vtt")} --> {stamp(c["end"],kind=="vtt")}\n{text}\n\n'
    return result

def remap(captions, clips):
    result=[]; offset=0
    for clip in clips:
        for c in captions:
            start=max(c['start'],clip['start']); end=min(c['end'],clip['end'])
            if end>start:
                words=[{'word':w['word'],'start':max(w['start'],start)-clip['start']+offset,'end':min(w['end'],end)-clip['start']+offset} for w in c.get('words',[]) if min(w['end'],end)>max(w['start'],start)]
                result.append({'start':start-clip['start']+offset,'end':end-clip['start']+offset,'text':c['text'],'words':words})
        offset+=clip['end']-clip['start']
    return result

def ass(captions, style, width, height):
    def color(hex): return '&H00'+hex[5:7]+hex[3:5]+hex[1:3]
    def ts(s): return stamp(s,True)[:-1]
    def escape(t): return t.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n','\\N')
    alignment={'top':8,'middle':5,'bottom':2}[style['placement']]
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['font']},{style['size']},{color(style['colour'])},&H0000FFFF,{color(style['outline_colour'])},&H80000000,0,0,0,0,100,100,0,0,1,{style['outline']},0,{alignment},20,20,35,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    for c in captions:
        text=escape(c['text'])
        if style['active_word'] and c.get('words'):
            # Karaoke highlighting applies only if edited text still matches words.
            if ''.join(w['word'].strip() for w in c['words']).replace(' ','')==c['text'].replace(' ',''):
                text=''; cursor=c['start']
                for w in c['words']:
                    gap=round((w['start']-cursor)*100)
                    if gap>0: text+=f'{{\\k{gap}}}'
                    text+=f'{{\\kf{max(1,round((w["end"]-w["start"])*100))}}}'+escape(w['word'])+' '
                    cursor=w['end']
        header+=f'Dialogue: 0,{ts(c["start"])},{ts(c["end"])},Default,,0,0,0,,{text}\n'
    return header

def render(project_id,job,payload):
    project=db.project(project_id); edl=EDL.model_validate(payload['edl']).model_dump()
    duration=sum(c['end']-c['start'] for c in edl['clips'])
    if any(c['end']>project['metadata']['duration']+.01 for c in edl['clips']): raise ValueError('Clip outside source')
    if shutil.disk_usage(artifact(project_id,'.')).free<max(100_000_000,duration*2_000_000): raise ValueError('Insufficient disk space')
    preview=payload['preview']; w,h={'9:16':(720,1280),'16:9':(1280,720),'1:1':(720,720)}[edl['aspect']]
    if preview: w//=2; h//=2
    work=artifact(project_id,'render-'+job); work.mkdir(exist_ok=True)
    caption_file=work/'captions.ass'
    style=dict(edl['style']); style['size']=max(12,round(style['size']*w/720))
    caption_file.write_text(ass(remap(edl['captions'],edl['clips']),style,w,h),encoding='utf-8')
    args=['ffmpeg','-hide_banner','-y','-protocol_whitelist','file,pipe','-format_whitelist','mov,matroska,webm,avi','-i',str(artifact(project_id,project['source']))]
    if edl['music']: args+=['-stream_loop','-1','-protocol_whitelist','file,pipe','-format_whitelist','mov,mp3,wav,ogg,aac','-i',str(artifact(project_id,edl['music']))]
    filters=[]; has_audio=project['metadata']['audio']
    for i,c in enumerate(edl['clips']):
        filters.append(f"[0:v]trim=start={c['start']}:end={c['end']},setpts=PTS-STARTPTS,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-ow)*{edl['crop_x']}:(ih-oh)*{edl['crop_y']},setsar=1[v{i}]")
        if has_audio: filters.append(f"[0:a]atrim=start={c['start']}:end={c['end']},asetpts=PTS-STARTPTS,volume={edl['volume']}[a{i}]")
        else: filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={c['end']-c['start']}[a{i}]")
    filters.append(''.join(f'[v{i}][a{i}]' for i in range(len(edl['clips'])))+f"concat=n={len(edl['clips'])}:v=1:a=1[v][a]")
    filters.append("[v]subtitles=captions.ass[outv]")
    if edl['music']:
        filters.append(f"[1:a]atrim=duration={duration},asetpts=PTS-STARTPTS,volume={edl['music_volume']}[music]")
        filters.append('[a][music]amix=inputs=2:duration=first:normalize=0[outa]')
    output=artifact(project_id,('preview-' if preview else 'final-')+job+'.mp4')
    common=['-filter_complex',';'.join(filters),'-map','[outv]','-map','[outa]' if edl['music'] else '[a]','-c:v',payload.get('encoder','libx264')]
    args+=common
    if payload.get('encoder','libx264')=='libx264': args+=['-preset','veryfast','-crf','28' if preview else '20']
    args+=['-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart','-t',str(duration),'-progress','pipe:1','-nostats',str(output)]
    try: run(args,job,duration,work)
    except RuntimeError:
        if payload.get('encoder','libx264')=='libx264': raise
        args[args.index('-c:v')+1]='libx264'; run(args,job,duration,work)
    metadata=probe(output)
    if abs(metadata['duration']-duration)>.5 or not metadata['audio']: raise ValueError('Render preflight failed')
    # Decode entire output before reporting completion.
    run(['ffmpeg','-v','error','-protocol_whitelist','file,pipe','-i',str(output),'-f','null','-'],job,timeout=600)
    return {'file':output.name,'metadata':metadata,'revision':edl['revision'],'preview':preview}
