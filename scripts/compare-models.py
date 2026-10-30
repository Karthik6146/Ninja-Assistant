"""Compare local Ollama models as Jarvis's brain: tool choice, robustness to a poisoned history, and spoken replies.

Run from the project root while Ollama is running (models must already be pulled):
  .venv\\Scripts\\python.exe scripts\\compare-models.py qwen3.5:9b qwen3:8b gemma4:e4b
Calls no tools and changes no settings.
"""
import importlib.util,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from ninja import agent,db,tools,assistant_tools  # noqa: F401
spec=importlib.util.spec_from_file_location('evaltools',ROOT/'scripts/eval-tools.py');ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)

# The real 2026-10-29 conversation where Qwen narrated "please wait" for 80 turns; tested raw, without safe_history's filter.
POISONED='f9a1cacd'
PROBES=['check for whatsapp messages','Can you find a file of my signature?','Can you tell me about the RAM prices news?']
SPOKEN=[('hinglish','CMS kya hota hai? ek line mein'),('hinglish','Mujhe neend nahi aa rahi, kya karun?'),('hi','आज का दिन कैसे बेहतर बनाऊँ?'),
        ('en','Tell me a short joke about programmers.'),('hinglish','Jarvis, tum kaun ho?')]

def summary(model,spoken):
    out=subprocess.run([sys.executable,str(ROOT/'scripts/eval-tools.py'),'--model',model]+(['--spoken'] if spoken else []),capture_output=True,text=True,encoding='utf-8',env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'})
    fails=[l.split('|')[1].strip() for l in out.stdout.splitlines() if l.startswith('FAIL')]
    line=next((l for l in out.stdout.splitlines() if 'correct' in l),out.stderr.strip()[-200:])
    return line,fails

def robustness(model):
    with db.connect() as c:row=c.execute('SELECT body FROM agent_tasks WHERE id LIKE ?',(POISONED+'%',)).fetchone()
    if not row:return 'poisoned conversation not found'
    task=json.loads(row[0]);msgs=task['messages'];schemas=[agent.tool_schema(t) for t in tools.REGISTRY.values()]
    system=agent.system_prompt(dict(task['request'],spoken=True),True,False);ok=0;n=0
    for probe in PROBES:
        i=max(k for k,m in enumerate(msgs) if m['role']=='user' and probe in m['content'])
        history=[m for m in msgs[:i+1][-20:] if not agent.recovery(m)]
        calls,_=ev.turn([{'role':'system','content':system}]+history,schemas,model);ok+=bool(calls);n+=1
    return f'{ok}/{n} probes called a tool'

def replies(model):
    rows=[]
    for language,text in SPOKEN:
        system=agent.system_prompt({'response_mode':'companion','spoken':True,'language':language},True,True)
        started=time.monotonic();_,reply=ev.turn([{'role':'system','content':system},{'role':'user','content':text}],[],model)
        rows.append((round(time.monotonic()-started,1),text,re.sub(r'\s+',' ',reply)))
    return rows

def main():
    for model in sys.argv[1:]:
        print(f'\n################ {model}')
        ev.turn([{'role':'user','content':'hi'}],[],model)  # load into memory so timings are warm
        for spoken in (False,True):
            line,fails=summary(model,spoken);print(('voice ' if spoken else 'typed ')+line);[print('   miss:',f) for f in fails]
        print('poisoned history:',robustness(model))
        for seconds,text,reply in replies(model):print(f'  {seconds}s  {text}\n        -> {reply}')

if __name__=='__main__':main()
