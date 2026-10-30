"""Explicit channel/workflow policy, applied through existing reviewed upload ledger."""
from typing import Literal
from filelock import FileLock
from pydantic import Field
from . import db,video,youtube as yt
from .video_models import Strict

class Policy(Strict):
    enabled:bool=False
    channel:str=Field(min_length=1,max_length=100)
    mode:Literal['private','public','schedule']='private'
    acknowledged:bool=False

def policy(id,body):
    video.get(id)
    with FileLock(db.DATA/('video-'+id+'.lock'),timeout=1):
        value=video.get(id);video.idle(value)
        if body.enabled and (not body.acknowledged or body.channel!=yt.channel()):raise ValueError('Confirm the connected channel and the concrete publishing policy')
        value['publish_policy']=body.model_dump();video.save(value)
        db.audit('video.publish-policy',{'workflow':id,**body.model_dump()})
        return value

def eligible(op):
    if op['kind']!='upload':return None
    p=db.project(op['params']['snapshot']['project']);id=p.get('video_workflow')
    if not id:return None
    value=video.get(id);rule=value.get('publish_policy',{})
    if not rule.get('enabled') or rule['channel']!=op['params']['channel'] or rule['channel']!=yt.channel():return None
    if not any(o.get('package')==op['params']['snapshot']['package'] and o['revision']==value['revision'] for o in value['outputs'] if not o['preview']):return None
    if value.get('approved_revision')!=value['revision']:return None
    yt.validate(op['params'])
    return value,rule

def prepared(op):
    return authorize(op,False)

def uploaded(op):
    return authorize(op,True)

def authorize(op,finished):
    if op["kind"]!="upload":return
    id=db.project(op["params"]["snapshot"]["project"]).get("video_workflow")
    if not id:return
    with FileLock(db.DATA/("video-"+id+".lock"),timeout=1):
        return after_upload(op) if finished else before_upload(op)

def before_upload(op):
    found=eligible(op)
    if found and op['state']=='review':
        value,rule=found
        if rule['mode']=='schedule':
            from datetime import datetime
            import time
            schedule=op['params']['snapshot']['draft']['schedule']
            if not schedule or datetime.fromisoformat(schedule).timestamp()<time.time()+120:raise ValueError('Auto-schedule policy requires a future, timezone-qualified date in the reviewed draft')
        result=yt.approve(op['id']);db.audit('video.policy-authorized',{'workflow':value['id'],'operation':op['id'],'mode':rule['mode']})
        return result

def after_upload(op):
    found=eligible(op)
    if not found or not op.get('remote_id'):return
    value,rule=found
    if rule['mode']=='private':return
    # Persist the operation before authorization; reuse it after an interruption.
    receipt=value.setdefault('policy_operations',{}).get(op['id'])
    if receipt:status=yt.get(receipt)
    else:
        schedule=op['params']['snapshot']['draft']['schedule'] if rule['mode']=='schedule' else None
        if rule['mode']=='schedule' and not schedule:raise ValueError('Missing reviewed publication date')
        status=yt.prepare_status(op['id'],'private' if schedule else 'public',schedule)
        value['policy_operations'][op['id']]=status['id'];video.save(value)
    if status['state']=='review':yt.approve(status['id'])
