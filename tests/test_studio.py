import copy,json,time
from pathlib import Path
import httpx,pytest
from ninja import db,studio,content,youtube as yt,youtube_auth as auth,media
from ninja.config import artifact

@pytest.fixture
def channels(monkeypatch):
    values={}
    def vault(name,value=None,delete=False):
        if delete:values.pop(name,None)
        elif value is not None:values[name]=copy.deepcopy(value)
        return copy.deepcopy(values.get(name))
    monkeypatch.setattr(auth,'vault',vault)
    for i in range(6):
        connection=f'{i+1:032x}';token={'access_token':f'account-{i}','refresh_token':'refresh','expires':time.time()+3600,'scope':' '.join(auth.SCOPES.values()),'channel':{'id':f'channel-{i}','title':f'Channel {i}'}}
        vault(auth.token_key(connection),token);auth.remember(connection,token)
    return values

def source(tmp_path,monkeypatch):
    p=tmp_path/'finished.mp4';p.write_bytes(b'finished-video-without-transcoding')
    monkeypatch.setattr(media,'probe',lambda _:dict(duration=4,width=320,height=240,audio=True))
    project={'id':'a'*32,'name':'Finished source','source':'source.mp4','edl':{'revision':0,'captions':[]},'metadata':{'duration':4}}
    path=artifact(project['id'],project['source']);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(p.read_bytes())
    with db.connect() as c:c.execute('INSERT INTO projects VALUES(?,?,?,?)',(project['id'],project['name'],db.encode(project),time.time()))
    return project,p

def test_six_channels_and_finished_workflow_immutable_upload(tmp_path,monkeypatch,channels):
    assert len(auth.channels())==6
    p,path=source(tmp_path,monkeypatch)
    definitions=[]
    for i in range(6):definitions.append(studio.save({'name':f'Flow {i}','channel':f'channel-{i}','projects':[p['id']],'rights':'owned','policy':'private','description':f'Description {i}','made_for_kids':False,'synthetic_media':False}))
    assert len({x['definition']['channel'] for x in studio.listing()})==6
    f=definitions[0];studio.activate(f['id'],1,True,True)
    run=studio.start(f['id'],False,'first-run-immutable')
    # Finished mode must never invoke any production stages.
    monkeypatch.setattr(studio.video,'execute',lambda *a:pytest.fail('Finished media was edited'))
    result=studio.execute(run['id'],run['job']);item=result['items'][0];op=yt.get(item['operation'])
    assert artifact(item['project'],item['file']).read_bytes()==path.read_bytes()
    assert op['params']['channel']=='channel-0' and op['params']['connection']==f'{1:032x}'
    calls=[]
    def request(method,url,**kw):
        calls.append(kw['headers']['Authorization'])
        if '/channels' in url:return httpx.Response(200,json={'items':[{'id':'channel-0'}]})
        if method=='POST':return httpx.Response(200,headers={'Location':'https://www.googleapis.com/upload/youtube/v3/videos?upload_id=fixture'})
        if method=='PUT':return httpx.Response(200,json={'id':'abcdefghijk'})
        return httpx.Response(200,json={'items':[{'id':'abcdefghijk','snippet':{'channelId':'channel-0','title':'Finished source'},'status':{'privacyStatus':'private'}}]})
    monkeypatch.setattr(auth,'request',request)
    with auth.target(f'{6:032x}','channel-5'):
        yt.execute(op['id'],run['job'])
    assert set(calls)=={'Bearer account-0'}
    again=studio.start(f['id'],False,'second-run-dedup');out=studio.execute(again['id'],again['job'])
    assert out['items'][0]['state']=='skipped'
    assert studio.start(f['id'],False,'second-run-dedup')['id']==again['id']
    channels[auth.token_key(f'{1:032x}')]['channel']['id']='channel-5'
    with pytest.raises(ValueError,match='Reconnect'):yt.execute(op['id'],run['job'])

def test_draft_test_has_no_publication_and_activation_is_revision_bound(tmp_path,monkeypatch,channels):
    p,_=source(tmp_path,monkeypatch);flow=studio.save({'projects':[p['id']],'rights':'owned','policy':'public','channel':'channel-0'})
    monkeypatch.setattr(yt,'approve',lambda _:pytest.fail('Test tried to publish'))
    run=studio.start(flow['id'],True,'test-is-local');studio.execute(run['id'],run['job'])
    with db.connect() as c:assert c.execute('SELECT count(*) FROM youtube_operations').fetchone()[0]==0
    with pytest.raises(ValueError):studio.start(flow['id'],False,'not-active')
    with pytest.raises(ValueError,match='Local tests'):studio.prepare_review(run['id'],0)
    newer=studio.save({**flow['definition'],'name':'Changed draft'},flow['id'],1)
    with pytest.raises(ValueError):studio.activate(flow['id'],1,True,True)
    assert not newer['active']

def test_folder_observation_ignores_copying_files_and_schedule_claims(tmp_path,monkeypatch):
    studio.grant(str(tmp_path));p=tmp_path/'ready.mp4';p.write_bytes(b'first');(tmp_path/'incomplete.mp4.part').write_bytes(b'copying')
    now=time.time();assert studio.stable_files('f',str(tmp_path),now)==[]
    assert studio.stable_files('f',str(tmp_path),now+31)==[p]
    p.write_bytes(b'changed');assert studio.stable_files('f',str(tmp_path),now+32)==[]
    assert studio.stable_files('f',str(tmp_path),now+63)==[p]
    flow=studio.save({'name':'Daily','mode':'business','trigger':'daily','time':'19:00','timezone':'Asia/Kolkata'})
    flow=studio.activate(flow['id'],1,True,True);flow['next_run']=now-1
    with db.connect() as c:c.execute('UPDATE studio_workflows SET body=? WHERE id=?',(db.encode(flow),flow['id']))
    studio.tick();studio.tick()
    assert len(studio.runs(flow['id']))==1
    from datetime import datetime,timezone
    stamp=studio.next_time(flow['definition'],datetime(2026,10,8,10,tzinfo=timezone.utc).timestamp())
    assert datetime.fromtimestamp(stamp,timezone.utc).isoformat()=='2026-10-08T13:30:00+00:00'


def test_local_clip_mode_uses_ranked_candidates_and_audio_probe(tmp_path):
    import wave
    from ninja import video
    sound=tmp_path/'cue.wav'
    with wave.open(str(sound),'wb') as wav:
        wav.setparams((1,2,16000,0,'NONE','not compressed'));wav.writeframes(b'\0\0'*16000)
    assert media.probe(sound,audio_only=True)['duration']==1
    value={'id':'b'*32,'revision':0,'request':{'urls':[],'clips':True,'rank_model':False,'count':2,'seconds':30,'aspect':'9:16','preset':'education','captions':False},
           'assets':[{'id':'source','duration':100,'evidence':{'scene_boundaries':[35,70],'speech_resumptions':[]},'transcript':{'words':[]}}]}
    video.select(value,'not-running')
    assert len(value['plans'])==2
    assert all(30<=sum(s['end']-s['start'] for s in p['segments'])<=180 for p in value['plans'])


def test_review_run_binds_connection_and_unchanged_save_keeps_activation(tmp_path,monkeypatch,channels):
    p,_=source(tmp_path,monkeypatch)
    flow=studio.save({'channel':'channel-0','projects':[p['id']],'rights':'owned','description':'Reviewed description','made_for_kids':False,'synthetic_media':False})
    active=studio.activate(flow['id'],1,True,True)
    assert studio.save(active['definition'],flow['id'],1)['active']
    run=studio.start(flow['id'],False,'manual-review-run')
    studio.execute(run['id'],run['job'])
    op=studio.prepare_review(run['id'],0)
    assert op['state']=='review' and op['params']['connection']==f'{1:032x}'
    assert studio.prepare_review(run['id'],0)['id']==op['id']


@pytest.mark.parametrize('test',[True,False])
def test_automatic_export_metadata_and_upload_are_retry_safe(tmp_path,monkeypatch,channels,test):
    from ninja import studio_metadata,adapters
    p,path=source(tmp_path,monkeypatch);calls=[];generated=[]
    flow=studio.save({'mode':'clips','projects':[p['id']],'rights':'owned','channel':'channel-0','automatic':True,'ai_metadata':True,'policy':'public','made_for_kids':False,'synthetic_media':False})
    monkeypatch.setattr(studio,'preflight',lambda d:{'ready':True,'issues':[]})
    studio.activate(flow['id'],1,True,True);run=studio.start(flow['id'],test,'automatic-'+str(test))
    item=studio.finished_project(path,'Rendered clip',run,run['job'])
    value={'id':'b'*32,'revision':0,'plans':[{'segments':[{'asset':'asset','start':0,'end':4}]}],'assets':[{'id':'asset','title':'Source title','transcript':{'words':[{'start':0,'end':1,'text':'Actual spoken content'}]}}],'outputs':[]}
    monkeypatch.setattr(studio.video,'create',lambda d:value)
    monkeypatch.setattr(studio.video,'get',lambda id:value)
    monkeypatch.setattr(studio.video,'approve',lambda *a:calls.append('approve'))
    def execute(id,job,payload):
        calls.append(payload['stage'])
        if payload['stage']=='render':value['outputs']=[{'preview':False,'revision':0,'index':0,'package':item['package'],'sha256':item['sha256']}]
    monkeypatch.setattr(studio.video,'execute',execute)
    def complete(prompt, *, schema):
        assert schema['required']==['title','description']
        generated.append(prompt)
        return {'text':json.dumps({'title':'Accurate generated title','description':'Written from the actual clip','tags':['shorts']}),'usage':{'input_tokens':10,'output_tokens':12}}
    monkeypatch.setattr(adapters,'complete',complete)
    monkeypatch.setattr(adapters,'local_model',lambda:'qwen3.5:9b')
    studio.execute(run['id'],run['job']);studio.execute(run['id'],run['job'])
    saved=studio.load_run(run['id'])
    assert calls[:3]==['prepare','approve','render'] and len(generated)==1
    assert 'Actual spoken content' in generated[0]
    assert saved['items'][0]['generated_metadata']['title']=='Accurate generated title'
    with db.connect() as c:assert c.execute('SELECT count(*) FROM youtube_operations').fetchone()[0]==(0 if test else 1)
    if not test:
        op=yt.get(saved['items'][0]['operation'])
        assert op['state']=='queued' and op['params']['channel']=='channel-0'
        assert op['params']['metadata']['snippet']['title']=='Accurate generated title'
        studio.activate(flow['id'],1,False,False)
        with pytest.raises(ValueError,match='paused'):studio.execute(run['id'],run['job'])


def test_youtube_research_is_read_only_cached_and_bound(monkeypatch,channels):
    from ninja import studio_metadata
    from ninja.studio_models import Definition
    calls=[]
    def api(method,resource,**kw):
        assert method=='GET' and auth.binding()['channel']=='channel-2'
        calls.append((resource,kw['params']))
        if resource=='search':return {'items':[{'id':{'videoId':'abcdefghijk'}}]}
        return {'items':[{'id':'abcdefghijk','snippet':{'title':'Reference','publishedAt':'2026-10-01T00:00:00Z'},'statistics':{'viewCount':'42'},'contentDetails':{'duration':'PT45S'}}]}
    monkeypatch.setattr(auth,'api',api)
    run={'connection':f'{3:032x}','definition':Definition(channel='channel-2',title='Research fixture unique').model_dump()}
    result=studio_metadata.research(run,{})
    assert studio_metadata.research(run,{})==result and len(calls)==3
    assert result['videos'][0]['views']=='42' and result['retrieved']>0
    assert calls[0][1]['videoDuration']=='short' and 'publishedAfter' in calls[0][1]
    with pytest.raises(ValueError):studio_metadata.Metadata(title='<bad>',description='description')


def test_finished_ai_metadata_never_edits_and_resumes_failure(tmp_path,monkeypatch,channels):
    from ninja import adapters
    p,path=source(tmp_path,monkeypatch)
    flow=studio.save({'projects':[p['id']],'rights':'owned','channel':'channel-0','automatic':True,'ai_metadata':True,'policy':'public','made_for_kids':False,'synthetic_media':False})
    monkeypatch.setattr(studio,'preflight',lambda d:{'ready':True,'issues':[]})
    studio.activate(flow['id'],1,True,True);run=studio.start(flow['id'],False,'finished-ai')
    monkeypatch.setattr(studio.video,'execute',lambda *a:pytest.fail('Finished file was edited'))
    def broken(*a,**kw):raise ValueError('Model unavailable')
    monkeypatch.setattr(adapters,'complete',broken)
    with pytest.raises(ValueError,match='Model unavailable'):studio.execute(run['id'],run['job'])
    saved=studio.load_run(run['id']);assert saved['steps']['produce']=='completed'
    with db.connect() as c:assert c.execute('SELECT count(*) FROM youtube_operations').fetchone()[0]==0
    monkeypatch.setattr(adapters,'complete',lambda *a,**kw:{'text':json.dumps({'title':'Generated finished title','description':'Actual finished video description','tags':[]}), 'usage':{}})
    saved=studio.execute(run['id'],run['job']);item=saved['items'][0]
    assert item['metadata']['duration']==4 and item['generated_metadata']['title']=='Generated finished title'
    assert artifact(item['project'],item['file']).read_bytes()==path.read_bytes()
    op=yt.get(item['operation']);op['remote_id']='abcdefghijk';public=[]
    monkeypatch.setattr(yt,'prepare_status',lambda id,visibility,date:public.append((id,visibility,date)) or {'id':'status'})
    monkeypatch.setattr(yt,'get',lambda id:{'id':id,'state':'review'})
    monkeypatch.setattr(yt,'approve',lambda id:None)
    studio.uploaded(op);studio.uploaded(op)
    assert public==[(op['id'],'public',None)]


def test_metadata_schema_reaches_ollama(monkeypatch):
    from ninja import adapters,studio_metadata
    calls=[]
    monkeypatch.setattr(adapters,'local_model',lambda:'qwen3.5:9b')
    def post(url,**kw):
        calls.append(kw['json'])
        return httpx.Response(200,request=httpx.Request('POST',url),json={'message':{'content':'{}'}})
    monkeypatch.setattr(adapters.httpx,'post',post)
    adapters.complete('metadata',schema=studio_metadata.Metadata.model_json_schema())
    assert calls[0]['format']['additionalProperties'] is False
    assert calls[0]['format']['required']==['title','description']
    with pytest.raises(ValueError,match='local Ollama'):adapters.complete('metadata','cloud',schema={})


def test_finished_instruction_transfers_only_unpublished_reservation(tmp_path,monkeypatch,channels):
    from ninja import studio_assistant as assistant,adapters
    p,path=source(tmp_path,monkeypatch)
    flow=studio.save({'projects':[p['id']],'rights':'owned','channel':'channel-0','automatic':True,'ai_metadata':True,'policy':'public','made_for_kids':False,'synthetic_media':False})
    monkeypatch.setattr(studio,'preflight',lambda d:{'ready':True,'issues':[]})
    studio.activate(flow['id'],1,True,True);run=studio.start(flow['id'],False,'finished-revision')
    monkeypatch.setattr(studio.video,'execute',lambda *a:pytest.fail('Finished footage was edited'))
    def unavailable(*a,**kw):raise ValueError('Model unavailable')
    monkeypatch.setattr(adapters,'complete',unavailable)
    with pytest.raises(ValueError):studio.execute(run['id'],run['job'])
    db.update_job(run['job'],state='failed')
    change=assistant.steer(run['id'],assistant.Change(text='Use a calm description',key='finished-revise'))
    monkeypatch.setattr(assistant,'interpret',lambda *a,**kw:assistant.Plan(name='Same video',mode='finished',count=1,seconds=60,aspect='9:16',preset='podcast',captions=False,language='en',summary='Metadata only'))
    monkeypatch.setattr(adapters,'complete',lambda *a,**kw:{'text':json.dumps({'title':'Calm title','description':'Calm description','tags':[]}), 'usage':{}})
    with db.connect() as c:payload=json.loads(c.execute('SELECT payload FROM jobs WHERE id=?',(change['job'],)).fetchone()[0])
    result=assistant.revise(payload,change['job']);item=result['items'][0]
    assert item['state']=='queued' and item['operation']
    assert db.project(item['project'])['studio_run']==change['run']
    assert artifact(item['project'],item['file']).read_bytes()==path.read_bytes()
    with db.connect() as c:
        assert c.execute('SELECT count(*) FROM youtube_operations').fetchone()[0]==1
        assert c.execute('SELECT run FROM studio_uploads').fetchone()[0]==change['run']
