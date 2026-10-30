import json
import copy
import threading
import time
from . import db, media, tools, youtube, workspace

def execute(job):
    stop=threading.Event()
    def heartbeat():
        while not stop.wait(5):
            try:db.update_job(job['id'],expected_attempt=job['attempts'] if job['kind']=='agent_turn' else None,heartbeat=time.time())
            except ValueError:return
    thread=threading.Thread(target=heartbeat,daemon=True); thread.start()
    try:
        if db.cancelled(job['id']): raise media.Cancelled()
        db.update_job(job['id'],expected_attempt=job['attempts'] if job['kind']=='agent_turn' else None,step='Running '+job['kind'].replace('_',' '))
        payload=json.loads(job['payload'])
        if job['kind']=='probe':
            project=db.project(job['project'])
            original=copy.deepcopy(project)
            project['metadata']=media.probe(media.artifact(job['project'],project['source']))
            project['edl']={'version':1,'revision':0,'clips':[{'start':0,'end':project['metadata']['duration']}],'captions':[]}
            db.save_project(job['project'],project,expected=original); result=project['metadata']
            media.artifact(job['project'],'edl-v0.json').write_text(db.encode(project['edl']),encoding='utf-8')
            from . import workflow  # langgraph import costs ~0.5 s; assistant turns never need it
            workflow.begin(job['project'],0)
        elif job['kind']=='agent_turn':
            from . import agent
            result=agent.execute(payload['task'],job['id'],job['attempts'])
            if result.get('deferred'):return
        elif job['kind']=='automation': result=workspace.automation(job['id'],payload)
        elif job['kind']=='render': result=media.render(job['project'],job['id'],payload)
        elif job['kind']=='video_stage':
            from . import video
            result=video.execute(job['project'],job['id'],payload)
        elif job['kind'] in ('assistant_chat','assistant_research'):
            from .assistant_desk import advise,research
            result=(advise if job['kind']=='assistant_chat' else research)(payload,job['id'])
        elif job['kind']=='studio_batch':
            from .studio_profiles import execute as batch
            result=batch(payload,job['id'])
        elif job['kind']=='studio_steer':
            from .studio_assistant import revise
            result=revise(payload,job['id'])
        elif job['kind']=='studio_run':
            from . import studio
            result=studio.execute(payload['run'],job['id'])
        elif job['kind']=='youtube_prepare':
            result=youtube.prepare(job['project'],job['id'],payload)
            from .video_publish import prepared
            prepared(result)
        elif job['kind']=='youtube_generate': result=youtube.generate(job['project'],job['id'],payload)
        elif job['kind']=='youtube_execute':
            result=youtube.execute(job['project'],job['id'])
            from .video_publish import uploaded
            uploaded(youtube.get(job['project']))
            from . import studio
            studio.uploaded(youtube.get(job['project']))
        elif job['kind']=='youtube_analytics': result=youtube.analytics(job['project'],payload['start'],payload['end'])
        elif job['kind']=='system_scan':result=tools.invoke('system.large_files',payload,{'system.read'})
        else: raise ValueError('Unknown job kind')
        if db.cancelled(job['id']): raise media.Cancelled()
        db.update_job(job['id'],expected_attempt=job['attempts'] if job['kind']=='agent_turn' else None,state='completed',step=('Waiting for your confirmation' if job['kind']=='agent_turn' and result.get('waiting') else 'Reply ready' if job['kind']=='agent_turn' and result.get('conversational') else 'Reply saved; no tool action verified' if job['kind']=='agent_turn' and not result.get('verified_actions') else 'Reply saved; tool receipts recorded' if job['kind']=='agent_turn' else 'Result verified and saved'),progress=1,result=db.encode(result))
        db.audit('job.finished',{'id':job['id'],'kind':job['kind']})
    except media.Cancelled:
        try:db.update_job(job['id'],expected_attempt=job['attempts'] if job['kind']=='agent_turn' else None,state='cancelled',step='Cancelled',error='Cancelled',error_code='CANCELLED')
        except ValueError:pass
    except Exception as e:
        try:db.update_job(job['id'],expected_attempt=job['attempts'] if job['kind']=='agent_turn' else None,state='failed',step='Failed',error=db.safe_error(e),error_code='TASK_FAILED')
        except ValueError:pass
    finally: stop.set(); thread.join(timeout=6)

def main(lane='heavy'):
    db.init()
    # A single worker lock prevents duplicate GPU-heavy work across processes.
    import os
    lock=open(db.DATA/('control-worker.lock' if lane=='control' else 'worker.lock'),'a+b')
    try:
        if os.name=='nt':
            import msvcrt
            lock.seek(0); lock.write(b'1'); lock.flush(); lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError: raise SystemExit('Another worker is already running')
    spare=None
    def prepare():
        # A runner that has already imported Ninja waits for the next job id (~0.3 s saved per assistant turn).
        import sys,tempfile,subprocess
        out,err=tempfile.TemporaryFile(),tempfile.TemporaryFile()
        return subprocess.Popen([sys.executable,'-m','ninja.runner','--wait'],stdin=subprocess.PIPE,stdout=out,stderr=err),out,err
    while True:
        from . import studio
        if lane=='control' and (spare is None or spare[0].poll() is not None):spare=prepare()
        try:
            if lane=='heavy':studio.tick()
            else:
                from . import assistant_events
                assistant_events.tick()
        except Exception as e:db.audit('studio.scheduler-error',{'message':db.safe_error(e)})
        job=db.claim(lane)
        if job:
            # Isolate tool/model jobs so cancellation kills their entire process tree.
            import sys
            try:
                started=None
                if spare and spare[0].poll() is None:
                    started,spare=spare,None
                    started[0].stdin.write(f"{job['id']} {job['attempts']}\n".encode());started[0].stdin.close()
                media.run([sys.executable,'-m','ninja.runner',job['id'],str(job['attempts'])],job['id'],timeout=900 if job['kind'] in ('chat','automation') else 7200,expected_attempt=job['attempts'] if job['kind']=='agent_turn' else None,started=started)
            except media.Cancelled:
                try:db.update_job(job['id'],expected_attempt=job['attempts'] if job['kind']=='agent_turn' else None,state='cancelled',step='Cancelled',error='Cancelled',error_code='CANCELLED')
                except ValueError:pass
            except Exception as e:
                try:db.update_job(job['id'],expected_attempt=job['attempts'] if job['kind']=='agent_turn' else None,state='failed',step='Failed',error=db.safe_error(e),error_code='TASK_FAILED')
                except ValueError:pass
        else: time.sleep(0.1 if lane=='control' else 1)

if __name__=='__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else 'heavy')
