import copy,json,hashlib,shutil,subprocess,time
import pytest
from fastapi.testclient import TestClient
from ninja import db,media_library as lib
from ninja.api import app
from ninja.config import artifact

def project(id='a'*32,rendered=False):
    path=artifact(id,'source.mp4');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'original media')
    value={'id':id,'name':'Original','source':'source.mp4','metadata':{'duration':12,'width':320,'height':180},'edl':{'revision':3},'suggestions':[]}
    if rendered:value['video_workflow']='v'*32
    with db.connect() as c:c.execute('INSERT INTO projects VALUES(?,?,?,?)',(id,value['name'],db.encode(value),time.time()))
    return value

def test_organisation_is_isolated_atomic_and_revision_checked():
    p=project();original=copy.deepcopy(p)
    value=lib.organise(lib.Batch(revisions={p['id']:0},changes=lib.Edit(name='Library name',notes='Editing idea',archived=True)))
    assert value[0]['library']['revision']==1 and db.project(p['id'])==original
    assert artifact(p['id'],p['source']).read_bytes()==b'original media'
    with pytest.raises(ValueError,match='changed'):lib.organise(lib.Batch(revisions={p['id']:0},changes=lib.Edit(favourite=True)))
    with pytest.raises(ValueError,match='no longer'):lib.organise(lib.Batch(revisions={p['id']:1,'b'*32:0},changes=lib.Edit(favourite=True)))
    item=lib.listing()[0];assert item['name']=='Library name' and item['library']['archived'] and not item['library']['favourite']
    lib.organise(lib.Batch(revisions={p['id']:1},changes=lib.Edit(archived=False)));assert not lib.listing()[0]['library']['archived']

def test_bulk_labels_preserve_independent_existing_labels_and_limits():
    a=project();b=project('b'*32)
    lib.organise(lib.Batch(revisions={a['id']:0},changes=lib.Edit(labels=['Personal'])))
    lib.organise(lib.Batch(revisions={b['id']:0},changes=lib.Edit(labels=['Other'])))
    lib.add_label(lib.LabelBatch(revisions={a['id']:1,b['id']:1},label=' Shared '))
    items={p['id']:p for p in lib.listing()};assert items[a['id']]['library']['labels']==['Personal','Shared'];assert items[b['id']]['library']['labels']==['Other','Shared']
    lib.organise(lib.Batch(revisions={b['id']:2},changes=lib.Edit(labels=[str(i) for i in range(20)])))
    with pytest.raises(ValueError):lib.add_label(lib.LabelBatch(revisions={a['id']:2,b['id']:3},label='Overflow'))
    assert lib.listing()[1]['library']['revision']==2
    lib.add_label(lib.LabelBatch(revisions={b['id']:3},label='0'))
    with pytest.raises(ValueError):lib.Edit(labels=[' '])

def test_library_status_has_real_publication_and_exports_evidence():
    p=project(rendered=True)
    op={'id':'upload','kind':'upload','state':'private','remote_id':'abcdefghijk','params':{'channel':'channel','snapshot':{'project':p['id']}}}
    with db.connect() as c:
        c.execute('INSERT INTO youtube_operations VALUES(?,?,?,?)',(op['id'],'upload','fingerprint',db.encode(op)))
        c.execute('INSERT INTO youtube_operations VALUES(?,?,?,?)',('status','status','other',db.encode({'id':'status','kind':'status','state':'failed','params':{'upload':'upload'}})))
    job=db.queue(p['id'],'render',{});db.update_job(job,state='completed',result=db.encode({'file':'render-v3.mp4','revision':3,'preview':False}))
    value=lib.listing()[0];assert value['kind']=='Rendered' and value['publications'][0]['state']=='failed' and value['exports']==[{'file':'render-v3.mp4','revision':3}]
    with db.connect() as c:
        op['state']='public';c.execute('UPDATE youtube_operations SET body=? WHERE id=?',(db.encode(op),'upload'))
        c.execute('UPDATE youtube_operations SET body=? WHERE id=?',(db.encode({'id':'status','kind':'status','state':'confirmed','params':{'upload':'upload'}}),'status'))
    assert lib.listing()[0]['publications'][0]['state']=='public'
    artifact(p['id'],p['source']).unlink();assert lib.listing()[0]['missing']

def test_authenticated_routes_reject_invalid_ids_and_unapproved_mutations():
    p=project()
    with TestClient(app) as client:
        assert client.get('/api/library').status_code==401
        client.post('/api/session',json={'token':'test-token'})
        assert client.post('/api/library/organise',json={'revisions':{p['id']:0},'changes':{'archived':True}}).status_code==403
        headers={'X-Ninja-Token':'test-token'}
        assert client.post('/api/library/organise',headers=headers,json={'revisions':{p['id']:0},'changes':{'path':'outside'}}).status_code==422
        assert client.get('/api/library/bad/thumbnail').status_code==400
        assert client.get('/api/library',headers=headers).status_code==200

def test_real_thumbnail_cache_preserves_source_and_confines_paths(monkeypatch):
    if not shutil.which('ffmpeg'):pytest.skip('FFmpeg unavailable')
    p=project();path=artifact(p['id'],p['source'])
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i','color=c=blue:s=320x180:d=1','-threads','1',str(path)],check=True,capture_output=True)
    p['metadata']['duration']=1;db.save_project(p['id'],p)
    original=hashlib.sha256(path.read_bytes()).hexdigest()
    response=lib.thumbnail(p['id']);assert response.media_type=='image/jpeg';target=artifact(p['id'],'library-thumbnail.jpg');assert target.read_bytes().startswith(b'\xff\xd8')
    monkeypatch.setattr(lib.subprocess,'run',lambda *a,**kw:pytest.fail('Cached thumbnail was regenerated'))
    lib.thumbnail(p['id']);assert hashlib.sha256(path.read_bytes()).hexdigest()==original
    p['source']='../../access-token';db.save_project(p['id'],p)
    with pytest.raises(ValueError):lib.thumbnail(p['id'])
