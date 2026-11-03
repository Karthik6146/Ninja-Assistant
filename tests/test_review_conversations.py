"""scripts/review-conversations.py flags real failures only."""
import importlib.util,sys
from pathlib import Path

spec=importlib.util.spec_from_file_location('review_conversations',Path(__file__).resolve().parents[1]/'scripts/review-conversations.py')
review=importlib.util.module_from_spec(spec);sys.modules['review_conversations']=review;spec.loader.exec_module(review)

def task(messages):return {'id':'t','text':messages[0]['content'],'request':{},'messages':messages,'conversation':[]}

def test_offline_refusal_is_not_an_issue_but_claim_after_decline_is():
    quiet=task([{'role':'user','content':'what is meta data'},{'role':'assistant','content':'','tool_calls':[]},
                {'role':'tool','tool_name':'research.deep','content':'{"error":"No tool needed: answer this from your own knowledge, briefly.","verified":false}'},
                {'role':'assistant','content':'Metadata is data about data, sir.'}])
    assert review.review(quiet)==[]
    lied=task([{'role':'user','content':'Remember that my favourite colour is blue'},{'role':'assistant','content':'','tool_calls':[]},
               {'role':'tool','tool_name':'memory.remember','content':'{"error":"Sir declined this action. Do not retry it; acknowledge briefly.","verified":false,"declined":true}'},
               {'role':'assistant','content':"No tool action was verified for this reply.\n\nI've saved your preference for the colour blue."}])
    assert [kind for kind,_,_ in review.review(lied)]==['claimed after decline']
    honest=dict(lied,messages=lied['messages'][:3]+[{'role':'assistant','content':'Understood, sir; I have not saved it.'}])
    assert review.review(honest)==[]
