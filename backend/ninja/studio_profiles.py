"""Channel-local preferences and durable multi-channel dispatch on the existing worker."""
import copy,json,time
from pydantic import Field
from . import db,studio,studio_assistant as assistant,youtube_auth as auth,media,video
from .studio_models import Strict,Definition,Reference

class Profile(Strict):
    revision:int=Field(default=0,ge=0)
    name:str=Field(default='',max_length=100)
    audience:str=Field(default='',max_length=300)
    instructions:str=Field(default='',max_length=1500)
    workflow:str=Field(default='',pattern=r'^(?:[a-f0-9]{32})?$')

def listing():
    flows=studio.listing();result=[]
    for channel in auth.channels():
        saved=channel.get('profile',{})
        own=[f for f in flows if f['definition']['channel']==channel['id']]
        default=next((f['id'] for f in own if f['active']),own[0]['id'] if own else '')
        profile=Profile.model_validate({'name':channel['title'],'workflow':default,**saved}).model_dump()
        result.append({**channel,'profile':profile})
    return result

def save(id,body):
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT body FROM youtube_channels WHERE id=?',(id,)).fetchone()
        if not row:raise ValueError('Connect and verify this channel before creating its profile')
        channel=json.loads(row[0])
        if body.revision!=channel.get('profile',{}).get('revision',0):raise ValueError('Profile changed; reload before saving')
        if body.workflow:
            row=c.execute('SELECT body FROM studio_workflows WHERE id=?',(body.workflow,)).fetchone()
            if not row or json.loads(row[0])['definition']['channel']!=id:raise ValueError('Choose a workflow belonging to this channel')
        channel['profile']=body.model_dump()|{'revision':body.revision+1}
        c.execute('UPDATE youtube_channels SET body=? WHERE id=?',(db.encode(channel),id))
    return channel['profile']

class Batch(Strict):
    channels:list[str]=Field(min_length=1,max_length=50)
    text:str=Field(default='',max_length=1800)
    source:str=Field(default='',max_length=2000)
    references:list[Reference]=Field(default_factory=list,max_length=5)
    test:bool=True
    key:str=Field(min_length=8,max_length=100)

def queue(body):
    if len(set(body.channels))!=len(body.channels):raise ValueError('Select each profile only once')
    if body.source:
        from .video_sources import youtube_id
        youtube_id(body.source)
    request=body.model_dump(exclude={'key'})
    with db.connect() as c:old=c.execute('SELECT id,payload FROM jobs WHERE request_key=?',('profiles-'+body.key,)).fetchone()
    if old:
        if json.loads(old['payload'])['request']!=request:raise ValueError('Batch key belongs to different instructions')
        return {'job':old['id']}
    profiles={p['id']:p for p in listing()};targets=[]
    for id in body.channels:
        p=profiles.get(id)
        if not p or not p['connected']:raise ValueError('Reconnect the selected profile in Settings')
        if not p['profile']['workflow']:raise ValueError(p['title']+': select a default workflow in its profile')
        flow=studio.get(p['profile']['workflow'])
        if flow['definition']['channel']!=id:raise ValueError('Profile workflow no longer belongs to this channel')
        if not body.test and (not flow['active'] or flow.get('authorized_revision')!=flow['revision']):raise ValueError(p['title']+': activate its default workflow before starting production')
        connection=auth.connection_for(id)
        if not body.test and connection!=flow.get('connection'):raise ValueError(p['title']+': connection changed; reactivate the workflow')
        flow['connection']=connection
        targets.append({'channel':id,'title':p['title'],'profile':p['profile'],'workflow':flow})
    return {'job':db.queue('channel-profiles','studio_batch',{'request':request,'targets':targets},'profiles-'+body.key)}

def execute(payload,job):
    request=payload['request'];results=[]
    for target in payload['targets']:
        if db.cancelled(job):raise media.Cancelled()
        slot='profile-'+job+'-'+target['channel'];result={'channel':target['channel'],'title':target['title']}
        try:
            with db.connect() as c:existing=c.execute('SELECT body FROM studio_runs WHERE slot=?',(slot,)).fetchone()
            if existing:run=json.loads(existing[0])
            else:
                flow=copy.deepcopy(target['workflow']);base=flow['definition'];p=target['profile']
                text='\n'.join(x for x in (p['instructions'],'Audience: '+p['audience'] if p['audience'] else '',base['prompt'], 'Task instruction (takes priority): '+request['text'] if request['text'] else '') if x)
                if len(text)>4000:raise ValueError('Combined profile, workflow and task instructions exceed 4,000 characters; shorten one')
                db.update_job(job,step='Plan for '+target['title'],progress=len(results)/len(payload['targets']))
                if text:
                    plan=assistant.interpret(text,base,request['source'],request['references'])
                    changes=plan.model_dump(exclude={'mode','summary','limitations'})
                    result.update(summary=plan.summary,limitations=plan.limitations)
                else:changes={}
                # Only creative fields change; credentials, mode and publication policy are fixed.
                d={**base,**changes,'prompt':text}
                if request['source']:
                    if d['mode']!='clips':raise ValueError('A shared YouTube source requires a Create clips workflow')
                    d.update(urls=[request['source']],projects=[],folder='')
                if request['references']:d['references']=request['references']
                flow['definition']=Definition.model_validate(d).model_dump()
                check=studio.preflight(flow['definition'])
                if not check['ready']:raise ValueError('; '.join(check['issues']))
                with auth.target(flow['connection'],target['channel']):pass
                with db.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    if db.cancelled(job):raise media.Cancelled()
                    current=json.loads(c.execute('SELECT body FROM studio_workflows WHERE id=?',(flow['id'],)).fetchone()[0])
                    if not request['test'] and (not current['active'] or current['revision']!=flow['revision'] or current.get('connection')!=flow['connection']):raise ValueError('Workflow changed or paused; start a new batch after reactivation')
                    run=studio.enqueue(c,flow,request['test'],slot)
                    run['batch']=job;run['profile']=target['profile'];run['plan_summary']=result.get('summary','Saved workflow settings');run['plan_limitations']=result.get('limitations',[])
                    c.execute('UPDATE studio_runs SET body=? WHERE id=?',(db.encode(run),run['id']))
            result.update(run=run['id'],state='queued')
        except media.Cancelled:raise
        except Exception as e:result.update(state='failed',error=db.safe_error(e))
        results.append(result);db.update_job(job,result=db.encode({'targets':results}),progress=len(results)/len(payload['targets']))
    if any(r['state']=='failed' for r in results):raise ValueError('Some profiles need attention; successful tasks stay queued. Fix the reported issue and retry planning.')
    return {'targets':results}

def batches():
    with db.connect() as c:rows=c.execute("SELECT id,state,step,error,result,created,payload FROM jobs WHERE kind='studio_batch' ORDER BY created DESC LIMIT 30").fetchall()
    result=[]
    for r in rows:
        targets=(json.loads(r['result']) if r['result'] else {}).get('targets',[])
        for target in targets:
            if not target.get('run'):continue
            run=studio.load_run(target['run']);seen=set()
            while run.get('superseded_by') and run['id'] not in seen:
                seen.add(run['id']);run=studio.load_run(run['superseded_by'])
            with db.connect() as c:job=c.execute('SELECT state,step,error FROM jobs WHERE id=?',(run['job'],)).fetchone()
            if job:target.update(state=job['state'],step=job['step'],error=job['error'])
        result.append({k:r[k] for k in ('id','state','step','error','created')}|{'targets':targets,'channels':json.loads(r['payload'])['request']['channels']})
    return result

def retry(id,kind):
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT state,kind FROM jobs WHERE id=?',(id,)).fetchone()
        if not row or row['kind']!=kind or row['state'] not in ('failed','cancelled'):raise ValueError('Only a failed or stopped planning task can be retried')
        c.execute("UPDATE jobs SET state='queued',cancel=0,error=NULL,error_code=NULL,finished=NULL WHERE id=?",(id,))
    return {'job':id}

def progress(id):
    run=studio.load_run(id)
    with db.connect() as c:
        job=dict(c.execute('SELECT id,state,step,error,progress,started,finished FROM jobs WHERE id=?',(run['job'],)).fetchone())
        change=c.execute("SELECT id,state,error,payload FROM jobs WHERE project=? AND kind='studio_steer' ORDER BY created DESC LIMIT 1",(id,)).fetchone()
    previews=[];stages=[]
    if run.get('video'):
        v=video.get(run['video'])
        for name in video.STAGES:
            stage=v['stages'].get(name,{});state=stage.get('state','pending')
            if state=='running' and job['state'] in ('failed','cancelled'):state=job['state']
            stages.append({'name':name,'state':state})
        for output in v['outputs']:
            if output['revision']!=v['revision']:continue
            kind='preview' if output['preview'] else 'render'
            previews.append({'label':f"Clip {output['index']+1} · {kind}",'url':f"/api/video/workflows/{v['id']}/outputs/{v['revision']}/{output['index']}/{kind}"})
    else:
        stages=[{'name':k,'state':v} for k,v in run['steps'].items()]
        previews=[{'label':item['name'],'url':f"/api/projects/{item['project']}/files/{item['file']}"} for item in run['items'] if item.get('file') and item.get('project')]
    change_result=None
    if change:change_result={k:change[k] for k in ('id','state','error')}|{'text':json.loads(change['payload'])['text']}
    return {'id':id,'name':run['definition']['name'],'channel':run['definition']['channel'],'policy':run['definition']['policy'],'test':run['test'],'job':job,'stages':stages,'previews':previews,'instructions':run.get('instructions',[]),'change':change_result,'replacement':run.get('superseded_by'),'locked':any(i.get('operation') for i in run['items']),'brief':run['definition']['prompt'],'limitations':run.get('plan_limitations',[])}
