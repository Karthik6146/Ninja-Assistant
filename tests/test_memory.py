import pytest
from ninja import memory,db
from ninja.agent_models import Scope

def test_memory_scope_correction_forget_and_budget():
    personal=Scope();channel=Scope(kind='channel',id='channel-a')
    first=memory.remember('Use purple captions',personal,source='request-1')
    memory.remember('Use green captions',channel,source='request-2')
    assert [v['text'] for v in memory.search('captions',[personal])]==['Use purple captions']
    revised=memory.correct(first['id'],'Use yellow captions',first['revision'])
    assert memory.search('purple',[personal])==[]
    assert memory.search('yellow',[personal])[0]['source']=='request-1'
    with pytest.raises(ValueError,match='changed'):memory.correct(first['id'],'Other',0)
    memory.forget(first['id'])
    assert memory.search('captions',[personal])==[]
    with db.connect() as c:assert c.execute('SELECT count(*) FROM assistant_memory_fts WHERE id=?',(first['id'],)).fetchone()[0]==0
    for i in range(8):memory.remember('caption '+str(i)+' '+'a'*1800,personal,source=str(i))
    assert sum(len(v['text']) for v in memory.context('caption',[personal],budget=100))<=400

def test_memory_rejects_credentials_and_preserves_exact_quote():
    with pytest.raises(ValueError,match='vault'):memory.remember('My password is hunter2',Scope(),source='test')
    with pytest.raises(ValueError,match='sensitive'):memory.remember('My bank account number is 1234567890',Scope(),source='test')
    value=memory.remember('I prefer Hindi explanations',Scope(),source='voice-request',quotation='I prefer Hindi explanations')
    assert value['quotation']=='I prefer Hindi explanations'
    assert memory.listing([Scope()])[0]['id']==value['id']


def test_old_quotation_is_not_in_inference_context():
    value=memory.remember('Use purple captions',Scope(),source='fixture')
    memory.correct(value['id'],'Use yellow captions',0)
    context=memory.context('captions',[Scope()])
    assert 'purple' not in db.encode(context) and 'yellow' in db.encode(context)
    assert len(db.encode(context))<1500*4

def test_unlabelled_financial_identifier_is_not_searchable():
    with pytest.raises(ValueError,match='sensitive'):memory.remember('My card is 4111 1111 1111 1111',Scope(),source='fixture')

