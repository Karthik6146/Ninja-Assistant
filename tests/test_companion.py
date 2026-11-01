import json
import pytest
from ninja import agent,adapters,db,worker,media
from ninja.agent_models import Request,Instruction,AgentTurn,ToolCall

def companion(text,key='companion-request'):
    return agent.create(Request(text=text,request_key=key,response_mode='companion',language='hinglish'))

def run():
    worker.execute(db.claim('control'))

def test_companion_question_finishes_once_without_action_warning(monkeypatch):
    observed=[]
    def answer(messages,*a,**kw):
        observed.append(messages)
        return AgentTurn(text='CMS content ko manage karne ka system hai.',timing={'model_seconds':1.2})
    monkeypatch.setattr(adapters,'agent_turn',answer)
    task=companion('What is CMS?');run();value=agent.get(task['task'])
    assert len(observed)==1
    assert value['reply']=='CMS content ko manage karne ka system hai.'
    assert value['step']=='Reply ready'
    assert value['timing']['model_seconds']==1.2
    assert any('Hinglish' in m['content'] for m in observed[0] if m['role']=='system')
    assert value['conversation']==[{'role':'user','content':'What is CMS?','revision':0},{'role':'assistant','content':value['reply'],'revision':0}]

def test_companion_follow_up_keeps_context_and_selected_scope(monkeypatch):
    seen=[]
    def answer(messages,*a,**kw):
        seen.append(messages);return AgentTurn(text='The answer is local.')
    monkeypatch.setattr(adapters,'agent_turn',answer)
    created=companion('Call my example site Mango Desk.');run()
    revised=agent.revise(created['task'],Instruction(text='What did I call my example site?',expected_revision=0,request_key='follow-up-companion',language='en'))
    run();value=agent.get(created['task'])
    assert len(seen)==2
    assert 'Mango Desk' in db.encode(seen[-1])
    assert value['request']['response_mode']=='companion' and value['request']['language']=='en'
    assert len(value['conversation'])==4
    assert value['conversation'][2]['content']=='What did I call my example site?'
    assert value['scopes']==revised['scopes']

def test_companion_requested_action_still_recovers_native_tool(monkeypatch):
    answers=iter([AgentTurn(text='I added it'),AgentTurn(calls=[ToolCall(id='real',name='assistant.add_task',arguments={'text':'Prepare companion demo'})]),AgentTurn(text='Your task is saved.')])
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:next(answers))
    created=companion('Please add a task: Prepare companion demo');run()
    value=agent.get(created['task'])
    assert value['verified_actions'] is True
    assert value['conversation'][-1]['content']=='Your task is saved.'
    assert len([s for s in value['steps'] if s['name']=='assistant.add_task'])==1

def test_stale_preview_cannot_overwrite_revised_conversation(monkeypatch):
    created=companion('Explain CMS.')
    def answer(*a,**kw):
        agent.revise(created['task'],Instruction(text='Explain databases instead',expected_revision=0,request_key='preview-change'))
        kw['on_text']('Old answer')
        return AgentTurn(text='Old answer')
    monkeypatch.setattr(adapters,'agent_turn',answer)
    run()
    value=agent.get(created['task'])
    assert value['revision']==1 and value.get('preview','')==''
    assert value['conversation'][-1]['content']=='Explain databases instead'

def test_stream_accumulates_text_usage_and_only_complete_calls(monkeypatch):
    import httpx
    events=[
      {'message':{'content':'Hi '},'done':False},
      {'message':{'content':'there','tool_calls':[{'function':{'name':'assistant.today','arguments':{}}}]},'done':False},
      {'message':{},'done':True,'prompt_eval_count':12,'eval_count':5,'load_duration':100000000,'prompt_eval_duration':200000000,'eval_duration':300000000}
    ]
    payload=('\n'.join(json.dumps(e) for e in events)+'\n').encode()
    original=httpx.Client;requests=[]
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,content=payload)
    monkeypatch.setattr(adapters.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    monkeypatch.setattr(adapters,'local_model',lambda:'qwen3.5:9b')
    job=db.queue('fixture','agent_turn',{})
    chunks=[]
    value=adapters.agent_turn([{'role':'user','content':'Today?'}],[],job=job,on_text=chunks.append,max_tokens=512)
    assert value.text=='Hi there' and chunks[-1]=='Hi there'
    assert value.calls[0].arguments=={} and value.usage=={'input_tokens':12,'output_tokens':5}
    assert requests[0]['stream'] is True and requests[0]['think'] is False
    assert value.timing['load_seconds']==.1 and value.timing['first_text_seconds']>=0

def test_incomplete_stream_never_becomes_a_finished_tool_turn(monkeypatch):
    import httpx
    original=httpx.Client
    payload=json.dumps({'message':{'tool_calls':[{'function':{'name':'assistant.add_task','arguments':{'text':'Never execute'}}}]},'done':False}).encode()+b'\n'
    monkeypatch.setattr(adapters.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=payload)),**kw))
    monkeypatch.setattr(adapters,'local_model',lambda:'qwen3.5:9b')
    with pytest.raises(ValueError,match='finish'):
        adapters.agent_turn([],[],job=db.queue('p','agent_turn',{}),on_text=lambda text:None)

def test_stream_cancellation_discards_following_content(monkeypatch):
    import httpx
    original=httpx.Client
    payload=(json.dumps({'message':{'content':'Draft'},'done':False})+'\n'+json.dumps({'message':{'content':' late'},'done':True})+'\n').encode()
    monkeypatch.setattr(adapters.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=payload)),**kw))
    monkeypatch.setattr(adapters,'local_model',lambda:'qwen3.5:9b')
    job=db.queue('p','agent_turn',{})
    def preview(text):
        with db.connect() as c:db.cancel_jobs(c,job)
    with pytest.raises(media.Cancelled):adapters.agent_turn([],[],job=job,on_text=preview)



def test_hinglish_explanation_does_not_trigger_action_recovery(monkeypatch):
    calls=[]
    def answer(*args,**kwargs):
        calls.append(kwargs)
        return AgentTurn(text='CMS se content organize hota hai.')
    monkeypatch.setattr(adapters,'agent_turn',answer)
    created=agent.create(Request(text='Ab Hinglish mein explain karo, CMS ka example do.',request_key='explain-hinglish',response_mode='companion',language='hinglish'))
    job=db.claim('control')
    result=agent.execute(created['task'],job['id'],job['attempts'])
    assert len(calls)==1 and not result['reply'].startswith('No tool action') and result['conversational']


@pytest.mark.parametrize('event',[
 {'message':{'content':'pretend complete'},'done':'false'},
 {'message':['invalid'],'done':True},
 {'message':{'tool_calls':[{'function':{'name':'assistant.today','arguments':{}}}]},'done':1},
])
def test_malformed_stream_cannot_finish_tools(monkeypatch,event):
    import httpx
    original=httpx.Client
    payload=(json.dumps(event)+'\n').encode()
    monkeypatch.setattr(adapters.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=payload)),**kw))
    monkeypatch.setattr(adapters,'local_model',lambda:'qwen3.5:9b')
    with pytest.raises(ValueError):adapters.agent_turn([],[],job=db.queue('p','agent_turn',{}),on_text=lambda text:None)

def test_hindi_command_is_recognized():
    assert agent.action_requested('\u092c\u0928\u093e\u0913 \u090f\u0915 \u0924\u0938\u094d\u0935\u0940\u0930')

def test_legacy_task_does_not_duplicate_assistant_turn(monkeypatch):
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:AgentTurn(text='Hello'))
    created=companion('Hi')
    with db.connect() as c:
        task=agent.load(c,created['task']);task.pop('conversation');agent.save(c,task)
    run()
    assert len(agent.get(created['task'])['conversation'])==2

@pytest.mark.parametrize('text',['वल्रेंट गेम का तमनेल जन्रेट करो','जनेट करो','मुझे वो इमेज दिखाओ','CPU चेक कीजिए','Valorant ka thumbnail generate karo'])
def test_devanagari_and_misheard_commands_are_actions(text):
    assert agent.action_requested(text)

def test_narrated_tool_without_call_gets_one_recovery(monkeypatch):
    answers=iter([AgentTurn(text='मैं image.generate का उपयोग करके थंबनेल बना रहा हूँ।'),AgentTurn(calls=[ToolCall(id='real',name='assistant.add_task',arguments={'text':'Thumbnail'})]),AgentTurn(text='Done.')])
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:next(answers))
    task=agent.create(Request(text='हाँ ठीक है',request_key='narrated',response_mode='companion',language='hinglish',spoken=True));run()
    value=agent.get(task['task'])
    assert value['verified_actions'] and value['reply']=='Done.'

def test_spoken_turn_ends_with_user_request(monkeypatch):
    seen=[]
    monkeypatch.setattr(adapters,'agent_turn',lambda messages,*a,**kw:seen.append(messages) or AgentTurn(text='Ji.'))
    agent.create(Request(text='Hello Jarvis',request_key='spoken-last',response_mode='companion',language='hinglish',spoken=True));run()
    assert seen[0][-1]['role']=='user' and seen[0][-1]['content'].startswith('Hello Jarvis')
    assert 'weather' in seen[0][0]['content']

def test_talking_about_is_not_an_action_but_command_in_same_sentence_is():
    assert not agent.action_requested('मुझसे English में बात करो')
    assert agent.action_requested('मैं वालो रेंड गेम का बात कर रहा हूँ, उसका तमनेल जन्रेट करो')

def test_warm_loads_model_only_when_gpu_is_free(monkeypatch):
    from filelock import FileLock
    from ninja.config import DATA
    posts=[]
    class Client:
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,url,json):posts.append(json)
    monkeypatch.setattr(adapters.httpx,'Client',Client)
    monkeypatch.setattr(adapters,'local_model',lambda:'qwen3.5:9b')
    with FileLock(DATA/'model.lock',timeout=0):assert adapters.warm_local_model() is False
    assert adapters.warm_local_model() is True
    assert posts==[{'model':'qwen3.5:9b','keep_alive':-1,'options':{'num_ctx':8192}}]

def test_empty_recovery_keeps_first_reply_instead_of_failing(monkeypatch):
    answers=iter([AgentTurn(text='मैंने `workflow.draft` से ड्राफ्ट तैयार किया है, सर।'),AgentTurn(text='')])
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:next(answers))
    task=companion('check if the work has been started or not');run()
    value=agent.get(task['task'])
    assert value['state']=='completed'
    assert value['reply'].startswith('No tool action was verified') and 'workflow.draft' in value['reply']

def test_progress_narration_counts_as_claimed_action():
    assert agent.claims_action('मैं अभी इस लिंक से ड्राफ्ट तैयार कर रहा हूँ।')

def test_prompt_prefix_is_stable_between_turns_for_model_cache(monkeypatch):
    seen=[]
    monkeypatch.setattr(adapters,'agent_turn',lambda messages,*a,**kw:seen.append(messages) or AgentTurn(text='Of course, sir.'))
    created=companion('First question');run()
    agent.revise(created['task'],Instruction(text='Second question',expected_revision=0,request_key='cache-two'));run()
    first,second=seen
    assert first[0]==second[0]
    assert second[1]['content']=='First question'
    assert '(Local time: ' in second[-1]['content'] and second[-1]['content'].startswith('Updated instruction: Second question')

@pytest.mark.parametrize('text',['नोएडा का मौसम कैसा है?','Kal Delhi mein baarish hogi kya?','What is the weather in Pune?'])
def test_weather_questions_count_as_tool_requests(text):
    assert agent.action_requested(text)

def test_first_message_mentions_documents_only_when_shared():
    assert agent.first_message('Open Calculator',[])=='Open Calculator'
    assert agent.first_message('Summarise this',['D:/notes/a.txt'])=='Summarise this\nExplicitly shared non-sensitive documents: ["D:/notes/a.txt"]'

@pytest.mark.parametrize('text',['Research the best microphones for YouTube','Volume thoda badhao','gaana band karo','Next song chalao','Downloads mein resume dhundo','आवाज़ बढ़ाओ','Look up the GTA 6 release date','Play some music'])
def test_device_and_research_requests_count_as_actions(text):
    assert agent.action_requested(text)

@pytest.mark.parametrize('text',['Haan sir, volume badha diya hai.','Calculator khol diya hai, sir.','जी सर, reminder सेट हो गया है।','Done, sir. I have paused the music.','मैंने आवाज़ बढ़ा दी है।'])
def test_claimed_completions_trigger_recovery(text):
    assert agent.claims_action(text)

def test_plain_answers_are_not_claims():
    assert not agent.claims_action('CMS ek software hai jisse website ka content badla jata hai.')

def test_unbacked_promises_are_hidden_from_the_model_but_backed_replies_stay():
    messages=[{'role':'user','content':'check whatsapp'},{'role':'assistant','content':'Of course, sir. I am checking your messages. Please wait while I fetch them.'},
              {'role':'user','content':'Have you fetched it?'},{'role':'assistant','content':'I have searched and found nothing.'},
              {'role':'user','content':'weather?'},{'role':'assistant','content':'','tool_calls':[{'function':{'name':'weather.now','arguments':{}}}]},
              {'role':'tool','tool_name':'weather.now','content':'{}'},{'role':'assistant','content':'I have checked: 24°C, sir.'}]
    kept=agent.safe_history(messages,companion=True)
    assert [m['content'] for m in kept if m['role']=='assistant']==['','I have checked: 24°C, sir.']
    # Hidden replies take their questions with them: no unanswered question left for Qwen to answer instead of the newest.
    assert [m['content'] for m in kept if m['role']=='user']==['weather?']


def test_newest_question_follows_answered_history_after_a_hidden_refusal():
    messages=[{'role':'user','content':'What is on my screen?'},{'role':'assistant','content':'I cannot see your screen, sir.'},{'role':'user','content':'Find my resume'}]
    assert agent.safe_history(messages,companion=True)==[{'role':'user','content':'Find my resume'}]


@pytest.mark.parametrize('text,expected',[('Who won the last IPL final?',True),('Who is the CEO of OpenAI?',True),('What is the price of iPhone 17 in India?',True),
                                          ('What is photosynthesis?',False),('How does a heat pump work?',False),('Open my last file',False)])
def test_changing_facts_need_a_lookup(text,expected):
    from ninja import agent
    assert agent.current_question(text) is expected


def test_changing_fact_is_searched_even_when_the_model_answers_from_memory(monkeypatch):
    from ninja import tools
    searched=[]
    monkeypatch.setattr(tools.REGISTRY['research.deep'],'execute',lambda params,timeout,context:searched.append(params.query) or {'data':{'sources':[{'n':1,'excerpt':'RCB won the 2025 final.'}]}})
    answers=iter([AgentTurn(text='Mumbai Indians won.'),AgentTurn(text='Royal Challengers Bengaluru won the 2025 final [1].')])
    monkeypatch.setattr(adapters,'agent_turn',lambda *a,**kw:next(answers))
    created=companion('Who won the last IPL final?');run()
    value=agent.get(created['task'])
    assert searched==['Who won the last IPL final?'] and value['reply']=='Royal Challengers Bengaluru won the 2025 final [1].'


@pytest.mark.parametrize('text',['Note down that the wifi password is on the router sticker','Take a note: buy milk','ye likh lo: meeting at 5'])
def test_note_requests_are_actions(text):
    assert agent.action_requested(text)


def test_untried_refusals_are_hidden_from_later_turns():
    history=[{'role':'user','content':'Ek joke sunao'},{'role':'assistant','content':'I cannot play audio files directly, sir.'},
             {'role':'user','content':'What is on my screen?'},{'role':'assistant','content':'','tool_calls':[{'function':{'name':'screen.look','arguments':{}}}]},
             {'role':'tool','tool_name':'screen.look','content':'{}'},{'role':'assistant','content':'I cannot read the small text, but it is VS Code.'}]
    assert agent.unbacked(history)=={1}  # a refusal after a real tool call stays


@pytest.mark.parametrize('text',["What's on my screen right now?",'Is error ko samjhao jo screen pe hai','What did I copy? Summarise what I copied','What is in my notes about wifi?'])
def test_screen_clipboard_and_notes_questions_need_tools(text):
    assert agent.action_requested(text)


def test_retry_drops_chat_turns_but_keeps_tool_results():
    messages=[{'role':'user','content':'Eek joke sunao'},{'role':'assistant','content':'Why do atoms lie? They make up everything, sir.'},
              {'role':'user','content':'Find my resume'},{'role':'assistant','content':'','tool_calls':[{'function':{'name':'file.find','arguments':{}}}]},
              {'role':'tool','tool_name':'file.find','content':'{}'},{'role':'assistant','content':'Found Karthik resume 2026.pdf, sir.'},
              {'role':'user','content':"What's on my screen?"},{'role':'assistant','content':'I cannot see your screen, sir.'},{'role':'user','content':agent.RECOVERY}]
    kept=[m['content'] for m in agent.safe_history(messages,companion=True,focus=True)]
    assert kept==['Find my resume','','{}','Found Karthik resume 2026.pdf, sir.',"What's on my screen?"]
    # Normal turns keep the chat (only the untried refusal goes) and still end with the newest question.
    assert [m['content'] for m in agent.safe_history(messages,companion=True)][-1]=="What's on my screen?"


@pytest.mark.parametrize('reply',['Of course, sir. I will increase the volume for you now.',"I'll set a timer for five minutes.",'Volume increased by one step, sir.','Timer set for 5 minutes, sir.'])
def test_promised_or_stated_actions_without_a_tool_are_claims(reply):
    assert agent.claims_action(reply)


def test_spoken_volume_commands_are_actions():
    assert agent.action_requested('Volume, increase') and agent.action_requested('Volume बढ़ाओ')
    assert not agent.claims_action('I will explain how a heat pump works.')


@pytest.mark.parametrize('text',['So that is happening right now','Okay, nice.','The latest one was better'])
def test_comments_are_not_forced_searches(text):
    assert not agent.current_question(text)


def test_spoken_narration_without_a_tool_is_a_claim():
    assert agent.claims_action('Opening signature1 (2).jpg for you now, sir.') and agent.claims_action('Playing music for you now, sir.')
    assert not agent.claims_action('Photosynthesis turns light into food for plants, sir.')


def test_unparsable_tool_call_is_retried_with_forward_slashes(monkeypatch):
    import httpx
    sent=[]
    def handler(request):
        body=json.loads(request.content);sent.append(body['messages'][-1]['content'])
        if len(sent)==1:return httpx.Response(500,json={'error':'XML syntax error on line 4: unexpected end element </function>'})
        return httpx.Response(200,json={'done':True,'message':{'content':'','tool_calls':[{'function':{'name':'file.read','arguments':{'path':'D:/Notes/ideas.txt'}}}]}})
    real=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda *a,**kw:real(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(adapters,'local_model',lambda:'qwen3.5:9b')
    turn=adapters.agent_turn([{'role':'user','content':r'Read my notes file D:\Notes\ideas.txt'}],[],job=db.queue('p','agent_turn',{}))
    assert sent==[r'Read my notes file D:\Notes\ideas.txt','Read my notes file D:/Notes/ideas.txt'] and turn.calls[0].arguments=={'path':'D:/Notes/ideas.txt'}


@pytest.mark.parametrize('text,key',[('Next song lagao','next'),('Change the track','next'),('change the track again','next'),('Pichla gaana','previous'),
                                     ('Volume badhao','volume_up'),('Volume, increase','volume_up'),('volume kam karo','volume_down'),('Pause it','pause'),
                                     ('Play music','resume'),('Play music for me','resume'),('Can you play music for me','resume'),('Gaana pause karo','pause'),('Mute','mute'),
                                     ('Can you play All the way home?',None),('What was the last song you played for me yesterday evening?',None),('Tell me a joke',None)])
def test_short_media_commands_map_to_keys(text,key):
    assert agent.media_command(text)==key


def test_invented_song_resumes_but_named_song_plays():
    call=lambda q:ToolCall(id='x',name='media.play',arguments={'query':q,'where':'spotify'})
    assert agent.grounded(call('popular music'),['Play music for me']).name=='media.control'
    assert agent.grounded(call('Mine'),['Play the music name, Mine','Play it for me']).name=='media.play'
    assert agent.grounded(call('biryani recipe'),['YouTube pe biryani recipe chalao']).name=='media.play'


def test_definitions_skip_web_tools_but_current_values_search():
    offline=lambda q:not agent.action_requested(q) and agent.simple_spoken_question(q)
    assert offline('what is repo rate') and offline('GST kya hota hai?')
    assert not offline('What is the current repo rate?') and agent.current_question('What is the current repo rate?')
    assert agent.current_question('Aaj ka repo rate kitna hai?') and not agent.current_question('Aaj kitne baje meeting hai?')
    assert not agent.current_question('what is the current time')


def test_definition_runs_no_tool_even_when_qwen_calls_one(monkeypatch):
    offered=[];answers=iter([AgentTurn(calls=[ToolCall(id='x',name='research.deep',arguments={'query':'meta data'})]),AgentTurn(text='Metadata is data about data.')])
    def answer(messages,schemas,*a,**kw):
        offered.append({s['function']['name'] for s in schemas});return next(answers)
    monkeypatch.setattr(adapters,'agent_turn',answer)
    monkeypatch.setattr(agent,'run_tool',lambda *a,**kw:pytest.fail('a definition must not run a tool'))
    created=companion('what is meta data');run();value=agent.get(created['task'])
    assert offered[0]==set()
    assert value['reply']=='Metadata is data about data.' and value['failed_actions'] is False
