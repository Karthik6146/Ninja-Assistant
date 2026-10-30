"""Small authenticated OpenChatCut MCP adapter; export remains a separate capability."""
import json,os
from pathlib import Path
import httpx

PROFILE='52e8c6d2-2d3d-4aae-9be7-fb2f4f40996c'

class Editor:
    def __enter__(self):
        token=Path(os.getenv('OPENCHATCUT_TOKEN_FILE',str(Path.home()/'.openchatcut/dev-profiles'/PROFILE/'mcp-token')))
        if not token.is_file():raise ValueError('Start the separate OpenChatCut service first')
        self.client=httpx.Client(base_url='http://localhost:5199',headers={'Authorization':'Bearer '+token.read_text().strip(),'Accept':'application/json, text/event-stream'},timeout=httpx.Timeout(120,connect=3),trust_env=False)
        self.sequence=0
        try:
            self.rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'Ninja Assistant','version':'1'}})
            self.client.post('/api/external-mcp/mcp',json={'jsonrpc':'2.0','method':'notifications/initialized'})
            self.tools={t['name']:t for t in self.rpc('tools/list',{})['tools']}
            return self
        except Exception:self.client.close();raise

    def __exit__(self,*args):self.client.close()

    def rpc(self,method,params):
        self.sequence+=1
        try:
            r=self.client.post('/api/external-mcp/mcp',json={'jsonrpc':'2.0','id':self.sequence,'method':method,'params':params})
            if r.status_code>=400:raise ValueError(f'OpenChatCut HTTP {r.status_code}; check the local service and MCP token configuration')
            if r.headers.get('mcp-session-id'):self.client.headers['Mcp-Session-Id']=r.headers['mcp-session-id']
            if 'text/event-stream' in r.headers.get('content-type',''):
                messages=[json.loads(line[6:]) for line in r.text.splitlines() if line.startswith('data: ')]
                data=next((m for m in messages if m.get('id')==self.sequence),{})
            else:data=r.json()
            if data.get('error'):raise ValueError('OpenChatCut rejected request: '+str(data['error'].get('message','unknown error'))[:600])
            if 'result' not in data:raise ValueError('OpenChatCut response missing result')
            return data['result']
        except httpx.HTTPError:raise ValueError('OpenChatCut unavailable or timed out at localhost:5199') from None

    def call(self,name,arguments):
        if name not in self.tools:raise ValueError('Installed OpenChatCut does not expose '+name)
        result=self.rpc('tools/call',{'name':name,'arguments':arguments})
        text='\n'.join(c.get('text','') for c in result.get('content',[]) if c.get('type')=='text')
        if result.get('isError'):raise ValueError('OpenChatCut: '+text[:1000])
        try:return json.loads(text)
        except ValueError:return result.get('structuredContent') or {'text':text}

def health():
    try:
        with Editor() as editor:
            return {'ready':True,'tools':list(editor.tools),'status':editor.call('openchatcut_status',{}),'export':'MCP excludes MP4 export; separate occ render CLI requires independent validation','url':'http://localhost:5199'}
    except (ValueError,OSError) as e:return {'ready':False,'message':str(e),'url':'http://localhost:5199'}

def build(value,job):
    from . import db,video,video_sources
    from .video_render import captions_for
    assets={a['id']:a for a in value['assets']}
    entries=value.setdefault('editor_projects',[])
    for index,plan in enumerate(value['plans']):
        if any(e['revision']==value['revision'] and e['index']==index and e.get('state')=='applied' for e in entries):continue
        with Editor() as editor:
            w,h={'9:16':(720,1280),'16:9':(1280,720),'1:1':(720,720)}[plan['aspect']]
            project=editor.call('create_project',{'name':value['name']+f' clip {index+1} v{value["revision"]}','compositionWidth':w,'compositionHeight':h,'fps':plan['fps']})
            entry={'id':project['id'],'name':project['name'],'url':project['editorUrl'],'revision':value['revision'],'index':index,'state':'drafting'}
            entries.append(entry);video.save(value)
            editor.call('target_project',{'projectId':project['id']})
            session=editor.call('begin_edit_session',{'approvalMode':'auto','clientName':'Ninja isolated project'})
            sid=session['editSessionId'];entry['session']=sid;video.save(value)
            try:
                before=editor.call('read_project',{'editSessionId':sid})
                imported={}
                for asset_id in dict.fromkeys(s['asset'] for s in plan['segments']):
                    video.cancel(job)
                    result=editor.call('import_asset',{'path':assets[asset_id]['path'],'editSessionId':sid})
                    imported[asset_id]=result['imported'][0]['id']
                cursor=0
                for segment in plan['segments']:
                    video.cancel(job)
                    result=editor.call('edit_item',{'adds':[{'type':'video','assetId':imported[segment['asset']],'fromFrame':cursor,'sourceStartSeconds':segment['start'],'sourceEndSeconds':segment['end']}],'editSessionId':sid})
                    item=result['results'][0]['placed']['itemId'];length=round((segment['end']-segment['start'])/segment['speed']*plan['fps'])
                    update={'type':'video','itemId':item,'speed':segment['speed'],'volume':segment['volume'],'transform':{'scale':segment['zoom']},'fadeInSeconds':.15 if 'fade' in plan['effects'] else 0,'fadeOutSeconds':.15 if 'fade' in plan['effects'] else 0}
                    if 'contrast' in plan['effects']:update['filters']={'contrast':1.04,'saturate':1.05}
                    editor.call('edit_item',{'updates':[update],'editSessionId':sid});cursor+=length
                editor.call('set_aspect_ratio',{'ratio':plan['aspect'],'fit':'cover','editSessionId':sid})
                # Editable text clips reuse ClipX words, never trigger OpenChatCut ASR.
                text=captions_for(value,plan) if plan['captions'] else []
                if plan['title']:text=[{'start':0,'end':min(4,cursor/plan['fps']),'text':plan['title']}]+text
                for offset in range(0,len(text),20):
                    video.cancel(job)
                    editor.call('edit_item',{'adds':[{'type':'text','text':c['text'],'fromFrame':round(c['start']*plan['fps']),'durationInFrames':max(1,round((c['end']-c['start'])*plan['fps'])),'fontSize':32} for c in text[offset:offset+20]],'editSessionId':sid})
                document=editor.call('read_project',{'editSessionId':sid})
                editor.call('review_edit_session',{'editSessionId':sid,'summary':'Ninja edit; review framing and text layout before exporting from OpenChatCut'})
                status=editor.call('get_edit_session',{'editSessionId':sid})
                if status.get('status')!='applied':raise ValueError('OpenChatCut did not confirm the draft commit')
                entry['state']='applied';entry['limitations']='OpenChatCut uses centered cover framing and editable text overlays. Ninja previews use the exact crop, caption layout and supported FFmpeg effects in the saved plan.'
                video_sources.atomic(video.folder(value['id'])/f"openchatcut-v{value['revision']}-{index+1}.json",{'project':entry,'before':before,'document':document,'status':status});video.save(value)
            except Exception:
                try:editor.call('discard_edit_session',{'editSessionId':sid})
                except ValueError:pass
                entry['state']='failed';video.save(value);raise
    return entries
