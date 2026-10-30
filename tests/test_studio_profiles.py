import copy,json,time
import pytest
from ninja import db,studio,studio_profiles as profiles,studio_assistant as assistant,youtube_auth as auth,media

@pytest.fixture
def setup(monkeypatch):
    tokens={}
    def vault(key,value=None,delete=False):
        if delete:tokens.pop(key,None)
        elif value is not None:tokens[key]=copy.deepcopy(value)
        return copy.deepcopy(tokens.get(key))
    monkeypatch.setattr(auth,'vault',vault)
    monkeypatch.setattr(studio,'preflight',lambda d:{'ready':True,'issues':[]})
    flows=[]
    for i in range(6):
        channel='channel-'+str(i);connection=f'{i+1:032x}'
        value={'channel':{'id':channel,'title':'Channel '+str(i)},'access_token':'fake','refresh_token':'fake','expires':time.time()+3600,'scope':' '.join(auth.SCOPES.values())}
        vault(auth.token_key(connection),value);auth.remember(connection,value)
        flow=studio.save({'name':'Flow '+str(i),'channel':channel,'mode':'clips','rights':'owned','policy':'public','automatic':True,'made_for_kids':False,'synthetic_media':False,'urls':['https://youtube.com/watch?v=abcdefghijk']})
        flows.append(studio.activate(flow['id'],1,True,True))
        profiles.save(channel,profiles.Profile(name='Profile '+str(i),audience='Audience '+str(i),instructions='Unique '+str(i),workflow=flow['id']))
    monkeypatch.setattr(assistant,'interpret',lambda text,*a,**kw:assistant.Plan(name=text[:80],mode='clips',count=2,seconds=45,aspect='9:16',preset='podcast',captions=True,language='en',summary=text[:200]))
    return flows,tokens

def payload(id):
    with db.connect() as c:return json.loads(c.execute('SELECT payload FROM jobs WHERE id=?',(id,)).fetchone()[0])

def test_six_profiles_isolated_and_preserved_on_reconnection(setup):
    flows,tokens=setup;values=profiles.listing()
    assert len(values)==6 and len({v['profile']['audience'] for v in values})==6
    with pytest.raises(ValueError,match='belonging'):profiles.save('channel-0',profiles.Profile(revision=1,workflow=flows[1]['id']))
    with pytest.raises(ValueError,match='changed'):profiles.save('channel-0',profiles.Profile(revision=0))
    auth.remember(f'{1:032x}',tokens[auth.token_key(f'{1:032x}')])
    assert next(p for p in profiles.listing() if p['id']=='channel-0')['profile']['instructions']=='Unique 0'

def test_batch_uses_snapshots_and_retries_without_duplicates(setup):
    flows,_=setup
    body=profiles.Batch(channels=['channel-'+str(i) for i in range(6)],text='Make two short clips',source='https://youtube.com/watch?v=abcdefghijk',test=False,key='six-channel-batch')
    id=profiles.queue(body)['job'];snap=payload(id)
    profiles.save('channel-0',profiles.Profile(revision=1,name='Edited',instructions='Changed later',workflow=flows[0]['id']))
    result=profiles.execute(snap,id);again=profiles.execute(snap,id)
    assert [r['run'] for r in result['targets']]==[r['run'] for r in again['targets']]
    assert profiles.queue(body)['job']==id
    assert len(studio.runs())==6
    for i,result in enumerate(result['targets']):
        run=studio.load_run(result['run']);d=run['definition']
        assert d['channel']=='channel-'+str(i) and run['connection']==f'{i+1:032x}'
        assert 'Unique '+str(i) in d['prompt'] and 'Changed later' not in d['prompt']
        assert d['policy']=='public' and run['revision']==1 and run['batch']==id
    assert all(studio.get(f['id'])['revision']==1 for f in flows)
    with db.connect() as c:assert c.execute('SELECT count(*) FROM youtube_operations').fetchone()[0]==0

def test_partial_failure_retry_and_paused_policy(setup,monkeypatch):
    flows,_=setup;original=assistant.interpret
    def model(text,*a,**kw):
        if 'Unique 1' in text:raise ValueError('Model failed on this profile')
        return original(text,*a,**kw)
    monkeypatch.setattr(assistant,'interpret',model)
    id=profiles.queue(profiles.Batch(channels=['channel-0','channel-1'],text='Make clips',key='partial-batch',test=False))['job']
    with pytest.raises(ValueError,match='Some profiles'):profiles.execute(payload(id),id)
    assert len(studio.runs())==1
    monkeypatch.setattr(assistant,'interpret',original)
    assert len(profiles.execute(payload(id),id)['targets'])==2 and len(studio.runs())==2
    another=profiles.queue(profiles.Batch(channels=['channel-0'],key='paused-after-queue',test=False))['job']
    studio.activate(flows[0]['id'],1,False,False)
    with pytest.raises(ValueError,match='Some profiles'):profiles.execute(payload(another),another)
    assert len(studio.runs())==2

def test_dry_batch_and_reconnected_identity(setup):
    flows,tokens=setup
    studio.activate(flows[0]['id'],1,False,False)
    with pytest.raises(ValueError,match='activate'):profiles.queue(profiles.Batch(channels=['channel-0'],test=False,key='paused-start'))
    id=profiles.queue(profiles.Batch(channels=['channel-0'],key='local-only-batch'))['job']
    result=profiles.execute(payload(id),id)
    assert studio.load_run(result['targets'][0]['run'])['test']
    with pytest.raises(ValueError,match='once'):profiles.queue(profiles.Batch(channels=['channel-1','channel-1'],key='duplicate-channel'))
    with pytest.raises(ValueError,match='different'):profiles.queue(profiles.Batch(channels=['channel-1'],key='local-only-batch'))
    id=profiles.queue(profiles.Batch(channels=['channel-1'],key='bound-connection',test=False))['job']
    tokens[auth.token_key(f'{2:032x}')]['channel']['id']='channel-5'
    with pytest.raises(ValueError,match='Some profiles'):profiles.execute(payload(id),id)

def test_live_progress_exposes_verified_previews_and_pending_changes(setup,monkeypatch):
    flows,_=setup;run=studio.start(flows[0]['id'],True,'preview-run')
    run['video']='b'*32;studio.checkpoint(run)
    monkeypatch.setattr(profiles.video,'get',lambda id:{'id':id,'revision':2,'stages':{'preview':{'state':'completed'}},'outputs':[{'revision':1,'index':0,'preview':True},{'revision':2,'index':0,'preview':True}]})
    change=assistant.steer(run['id'],assistant.Change(text='Use one clip',key='change-preview'))
    db.queue('other','chat',{},'ordinary-task')
    state=profiles.progress(run['id'])
    assert len(state['previews'])==1 and '/outputs/2/0/preview' in state['previews'][0]['url']
    assert state['change']['id']==change['job'] and state['change']['text']=='Use one clip'
    assert db.claim()['id']==change['job']

def test_single_plan_uses_profile_without_changing_policy(setup):
    flows,_=setup
    result=assistant.draft(assistant.Brief(workflow=flows[0]['id'],channel='channel-0',text='Task override'))
    assert 'Unique 0' in result['definition']['prompt'] and result['definition']['policy']=='public'
    with pytest.raises(ValueError,match='another channel'):assistant.draft(assistant.Brief(workflow=flows[0]['id'],channel='channel-1',text='Task override'))


def test_batch_worker_dispatch_and_queue_status(setup):
    from ninja import worker
    id=profiles.queue(profiles.Batch(channels=['channel-0'],key='worker-batch'))['job']
    worker.execute(db.claim())
    batch=profiles.batches()[0]
    assert batch['id']==id and batch['state']=='completed'
    run=studio.load_run(batch['targets'][0]['run'])
    db.update_job(run['job'],state='failed',error='Caption tool unavailable',step='caption')
    target=profiles.batches()[0]['targets'][0]
    assert target['state']=='failed' and target['error']=='Caption tool unavailable'
