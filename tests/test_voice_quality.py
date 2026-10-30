import math
import pytest
from ninja import voice,agent,adapters,db,worker,neural_voice
from ninja.agent_models import Request,AgentTurn,Instruction

def words(text,score=.9):return [{'text':v,'confidence':score} for v in text.split()]

def test_one_uncertain_word_does_not_stop_a_clear_turn():
    sample=words('Jarvis what is a content management system')
    sample[0]['confidence']=.35
    assert not voice.uncertain_transcript(sample,'hinglish')

@pytest.mark.parametrize('text',['no no no no no please listen','hello はい hello','hello السلام hello','and then and then and then and then'])
def test_drift_and_repetition_are_not_automatically_sent(text):
    assert voice.uncertain_transcript(words(text),'hinglish')

@pytest.mark.parametrize('score',[None,float('nan'),1.5,.3])
def test_invalid_or_low_confidence_is_uncertain(score):
    assert voice.uncertain_transcript(words('make a video',score),'en')

def test_voice_request_uses_native_hindi_without_extra_model_pass(monkeypatch):
    messages=[]
    monkeypatch.setattr(adapters,'agent_turn',lambda m,*a,**kw:(messages.append(m) or AgentTurn(text='यह content management system है।')))
    created=agent.create(Request(text='CMS kya hai?',request_key='spoken-example',response_mode='companion',language='hinglish',spoken=True))
    worker.execute(db.claim('control'))
    assert len(messages)==1 and 'Devanagari' in messages[0][0]['content']
    assert agent.get(created['task'])['step']=='Reply ready'

def test_companion_context_drops_internal_recovery_but_retains_tool_receipts():
    history=[{'role':'user','content':'No tool action has run. If my request needs a supported action, invoke its tool now instead of describing an imagined result.'},{'role':'tool','content':'real receipt','tool_name':'assistant.today'},{'role':'user','content':'What is CMS?'}]
    assert agent.safe_history(history,companion=True)==history[1:]
    assert agent.safe_history(history)==history

def test_neural_voice_rejects_unbounded_requests_before_process(monkeypatch):
    monkeypatch.setattr(neural_voice,'Engine',lambda:pytest.fail('Invalid request spawned voice'))
    with pytest.raises(ValueError):neural_voice.speak('hello','untrusted voice')
    with pytest.raises(ValueError):neural_voice.speak('x'*3001,next(iter(neural_voice.VOICES)))


def test_definition_fast_path_does_not_disable_requested_tools():
    assert agent.simple_spoken_question('Jarvis, CMS kya hota hai?')
    assert agent.simple_spoken_question('CMS क्या होता है, एक छोटा example दो')
    assert not agent.simple_spoken_question('What is a logo? Generate one for my store.')
    assert not agent.simple_spoken_question('आज एक तस्वीर बनाओ')


def test_informational_voice_turn_cannot_dispatch_unrequested_tool(monkeypatch):
    from ninja.agent_models import ToolCall
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:AgentTurn(calls=[ToolCall(id='bad',name='assistant.add_task',arguments={'text':'Unrequested'})]))
    created=agent.create(Request(text='What is a CMS?',spoken=True,response_mode='companion',request_key='no-voice-side-effect'))
    job=db.claim('control')
    with pytest.raises(ValueError,match='informational turn'):agent.execute(created['task'],job['id'],job['attempts'])
    assert not agent.get(created['task'])['verified_actions']

def test_default_jarvis_voice_is_british_and_switches_for_hindi():
    default=next(iter(neural_voice.VOICES))
    assert neural_voice.voice_for('Right away, sir.',default)=='bm_george'
    assert neural_voice.voice_for('जी sir, thumbnail बन रहा है।',default)=='hm_omega'
    assert neural_voice.voice_for('Hello.','Kokoro · English female')=='af_heart'

@pytest.mark.parametrize('text,language',[('Speak in English please','en'),('अब इंग्लिश में बात करो','en'),('क्या तो मेर से इंगलीस में बात कर सकते हो?','en'),('Hindi mein bolo','hi'),('हिंदी में बोलिए','hi'),('Hinglish mein baat karo','hinglish'),('Translate this into English','') ,('CMS kya hai?','')])
def test_spoken_language_switch(text,language):
    assert (agent.requested_language(text) or '')==language

def test_language_switch_persists_for_the_conversation(monkeypatch):
    seen=[]
    monkeypatch.setattr(adapters,'agent_turn',lambda messages,*a,**kw:seen.append(messages) or AgentTurn(text='Very well, sir.'))
    created=agent.create(Request(text='Hello',request_key='switch-1',response_mode='companion',language='hinglish',spoken=True));worker.execute(db.claim('control'))
    agent.revise(created['task'],Instruction(text='Speak in English from now on',expected_revision=0,request_key='switch-2',language='hinglish',spoken=True));worker.execute(db.claim('control'))
    value=agent.get(created['task'])
    assert value['request']['language']=='en'
    assert 'English only' in seen[-1][0]['content'] and 'JARVIS' in seen[-1][0]['content'] and 'नमस्ते' not in seen[-1][0]['content']

def test_spoken_reply_starts_with_short_opener_for_fast_first_audio(monkeypatch):
    seen=[]
    monkeypatch.setattr(adapters,'agent_turn',lambda messages,*a,**kw:seen.append(messages) or AgentTurn(text='Of course, sir.'))
    agent.create(Request(text='Tell me about CMS',request_key='opener-test',response_mode='companion',language='en',spoken=True));worker.execute(db.claim('control'))
    assert 'Of course, sir.' in seen[0][0]['content'] and 'opener' in seen[0][0]['content']

@pytest.mark.parametrize('text',['What are my priorities today?','आज के tasks क्या हैं?','What are people saying on Reddit about the RTX 5060?','What is the weather in Noida?','What is the latest news on GTA 6?','What do you remember about me?'])
def test_personal_or_current_questions_keep_their_tools(text):
    assert not agent.simple_spoken_question(text)
