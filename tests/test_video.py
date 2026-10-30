import pytest
from ninja.video_models import EditPlan,Segment
from ninja.video_sources import youtube_id,select_candidates,retime_words

def test_source_boundaries_and_timing():
    assert youtube_id('https://www.youtube.com/watch?v=v9QtM6qnG50')=='v9QtM6qnG50'
    assert youtube_id('https://youtu.be/v9QtM6qnG50?t=10')=='v9QtM6qnG50'
    for url in ('https://youtube.com.evil.org/watch?v=v9QtM6qnG50','file:///etc/passwd','http://127.0.0.1/x','https://youtube.com/playlist?list=abc'):
        with pytest.raises(ValueError):youtube_id(url)
    with pytest.raises(ValueError):Segment(asset='a',start=0,end=float('nan'))
    with pytest.raises(ValueError):EditPlan(segments=[dict(asset='a',start=0,end=40)],effects=['shell'])
    words=[dict(text='one',start=9,end=10),dict(text='two',start=10,end=11),dict(text='three',start=11,end=12)]
    result=retime_words(words,10,12,2,3)
    assert [(w['start'],w['end']) for w in result]==[(3,3.5),(3.5,4)]

def test_candidate_limits_and_nonoverlap():
    words=[dict(text='Word.',start=i,end=i+.6) for i in range(0,360,2)]
    candidates=select_candidates(360,words,[31,95,160,221],[45,150],4,60)
    assert candidates and all(30<=c['end']-c['start']<=180 for c in candidates)
    for i,a in enumerate(candidates):
        assert a['reason'] and 0<=a['confidence']<=1
        for b in candidates[i+1:]:assert min(a['end'],b['end'])<=max(a['start'],b['start'])
    assert select_candidates(29,[],[],[],3,60)==[]

def test_workflow_review_revisions_and_recovery(monkeypatch):
    from ninja import db,video,video_routes
    from ninja.config import DATA
    value=video.create({'urls':['https://youtu.be/v9QtM6qnG50'],'rights':'licensed','rank_model':False})
    id=value['id'];key='test-video-request'
    assert video.queue(id,'ingest',0,key)==video.queue(id,'ingest',0,key)
    with pytest.raises(ValueError):video.queue(id,'render',0,'test-video-other')
    job=video.queue(id,'ingest',0,key)['job'];db.update_job(job,state='failed',error='Interrupted')
    value.update(assets=[{'id':'source','metadata':{'duration':90,'audio':False}}],plans=[EditPlan(segments=[{'asset':'source','start':0,'end':40}]).model_dump()])
    value['stages']={s:{'state':'completed','revision':0,'result':{}} for s in video.STAGES[:-1]};video.save(value)
    video.approve(id,0)
    updated=video.edit(id,0,[value['plans'][0]])
    assert updated['revision']==1 and 'approved_revision' not in updated and 'preview' not in updated['stages']
    with pytest.raises(ValueError):video.approve(id,1)
    with pytest.raises(ValueError):video.edit(id,0,value['plans'])
    with pytest.raises(ValueError):video.queue('../escape','ingest',0,'test-escape-key')
    updated['stages']['edit']={'state':'running','job':job};video.save(updated)
    assert video_routes.get(id)['stages']['edit']['state']=='failed'

def test_render_multisource_speed_and_idempotent_registration(tmp_path):
    import shutil
    from ninja import db,media,video,video_render
    from ninja.config import DATA
    if not shutil.which('ffmpeg'):pytest.skip('FFmpeg required for integration check')
    source=tmp_path/'sample.mp4'
    media.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=320x240:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','4','-c:v','libx264','-c:a','aac',str(source)])
    value=video.create({'urls':['https://youtu.be/v9QtM6qnG50'],'rights':'owned','captions':True,'rank_model':False})
    asset=video.source_asset(source,'Synthetic test','sample');asset['transcript']={'words':[{'text':'Local test','start':.1,'end':1.5}]}
    value['request']['urls']=[]  # Custom-footage output can be shorter than a highlight.
    value['assets']=[asset];value['plans']=[EditPlan(segments=[{'asset':'sample','start':0,'end':2,'speed':2},{'asset':'sample','start':2,'end':4}],title='Caption timing check',effects=['fade','slow_zoom']).model_dump()]
    video.save(value);job=db.queue(value['id'],'video_stage',{})
    result=video_render.render(value,job,True)
    assert abs(result['outputs'][0]['metadata']['duration']-3)<.15
    assert result['outputs'][0]['metadata']['width']==360
    final=video_render.render(value,job,False)['outputs'][0]
    again=video_render.render(value,job,False)['outputs'][0]
    assert final['sha256']==again['sha256'] and final['package']==again['package']
    with db.connect() as c:assert c.execute('SELECT count(*) FROM packages WHERE id=?',(final['package'],)).fetchone()[0]==1
    assert video_render.captions_for(value,value['plans'][0])[0]['end']==.75
    project=db.project(final['package']);project['music']='final.mp4';db.save_project(project['id'],project)
    value['revision']=1
    value['plans'][0]['sound_effects']=[{'project':project['id'],'start':.5,'duration':1,'volume':.2}]
    mixed=video_render.render(value,job,True)['outputs'][0]
    assert abs(mixed['metadata']['duration']-3)<.15
    changed=tmp_path/'changed.mp4';changed.write_bytes(b'changed')
    with pytest.raises(ValueError):video_render.copy_source(source,changed)


def test_policy_requires_matching_channel_and_reviewed_current_output(monkeypatch):
    from ninja import db,video,video_publish as p,youtube as yt
    value=video.create({'urls':['https://youtu.be/v9QtM6qnG50'],'rights':'owned'})
    monkeypatch.setattr(yt,'channel',lambda:'channel-A')
    with pytest.raises(ValueError):p.policy(value['id'],p.Policy(enabled=True,channel='channel-B',acknowledged=True))
    with pytest.raises(ValueError):p.policy(value['id'],p.Policy(enabled=True,channel='channel-A'))
    value=p.policy(value['id'],p.Policy(enabled=True,channel='channel-A',acknowledged=True))
    monkeypatch.setattr(db,'project',lambda _: {'video_workflow':value['id']})
    op={'kind':'upload','params':{'channel':'channel-A','snapshot':{'project':'p','package':'pkg'}}}
    assert p.eligible(op) is None
    value.update(approved_revision=0,outputs=[{'package':'pkg','revision':0,'preview':False}]);video.save(value)
    calls=[];monkeypatch.setattr(yt,'validate',lambda _:calls.append('validated'))
    assert p.eligible(op)[1]['mode']=='private' and calls==['validated']
    value.pop('approved_revision');video.save(value);assert p.eligible(op) is None
    value['approved_revision']=0
    value['revision']=1;video.save(value);assert p.eligible(op) is None


def test_analysis_cache_tracks_source_changes(tmp_path,monkeypatch):
    from ninja import video_sources as s
    source=tmp_path/'source.mp4';source.write_bytes(b'first')
    calls=[];monkeypatch.setattr(s.media,'run',lambda *a,**kw:calls.append(a) or '')
    metadata={'duration':12,'audio':False}
    s.evidence(source,tmp_path,None,metadata);count=len(calls)
    s.evidence(source,tmp_path,None,metadata);assert len(calls)==count
    source.write_bytes(b'changed footage')
    s.evidence(source,tmp_path,None,metadata);assert len(calls)>count
