import time
import pytest
from ninja import content, db

@pytest.fixture
def package():
    with db.connect() as c:
        c.execute('INSERT INTO projects VALUES(?,?,?,?)',('p','fixture',db.encode({'id':'p','name':'recording','source':'source.mp4','edl':{'revision':1,'captions':[]}}),time.time()))
    return content.create('p')

def test_platform_change_only_invalidates_that_platform(package):
    body=content.scenes(package['id'],0,[],'owned')
    draft=content.Draft(platform='threads',account='my account',copy='Reviewed source-based draft')
    body=content.edit_draft(package['id'],draft)
    body=content.review(package['id'],'threads',1)
    assert body['platforms']['threads']['review']=='reviewed'
    content.edit_draft(package['id'],content.Draft(platform='youtube',copy='Different draft'))
    assert content.load(package['id'])['platforms']['threads']['review']=='reviewed'
    draft=content.Draft.model_validate(body['platforms']['threads']);draft.copy='Changed after approval'
    assert content.edit_draft(package['id'],draft)['platforms']['threads']['review']=='draft'

def test_source_change_invalidates_reviews_and_media(package):
    content.scenes(package['id'],0,[],'owned')
    content.edit_draft(package['id'],content.Draft(platform='threads',account='account',copy='Post'))
    content.review(package['id'],'threads',1)
    p=db.project('p');p['edl']['revision']=2;db.save_project('p',p)
    body=content.load(package['id'])
    assert body['source_revision']==2
    assert all(p['review']=='draft' and p['media'] is None for p in body['platforms'].values())

def test_scene_script_change_invalidates_audio_timing(package):
    scene={'id':'scene1','script':'old','start':0,'end':2}
    body=content.scenes(package['id'],0,[scene],'owned')
    scene=body['scenes'][0];scene['script']='updated'
    body=content.scenes(package['id'],body['revision'],[scene],'owned')
    assert body['scenes'][0]['revision']==1
    assert body['scenes'][0]['start'] is None and body['scenes'][0]['end'] is None
    assert body['scenes'][0]['narration_asset'] is None
    assert body['scenes'][0]['status']=='needs_rebuild'

def test_no_fabricated_remote_ids_or_unregistered_media(package):
    for values in ({'remote_id':'fake'},{'media':'not-rendered.mp4'},{'schedule':'2026-10-03T18:00:00'}):
        with pytest.raises(ValueError):content.edit_draft(package['id'],content.Draft(platform='instagram',**values))
    with pytest.raises(ValueError):content.review(package['id'],'youtube',0)
