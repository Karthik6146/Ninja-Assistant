"""Tool-choice eval against the live local model: does Jarvis pick the right tool (or none) for real requests?

Run from the project root while Ollama is running:
  .venv\\Scripts\\python.exe scripts\\eval-tools.py [--spoken] [--only substring] [--model qwen3:8b]
It uses the same system prompt, tool schemas and one-retry recovery as a real Jarvis turn, and calls no tools.
"""
import argparse,json,sys,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from ninja import adapters,agent,tools,assistant_tools  # noqa: F401  (assistant_tools registers the tools)


def turn(messages,schemas,model=None):
    body={'model':model or adapters.local_model(),'messages':messages,'tools':schemas,'stream':False,'think':False,'keep_alive':-1,'options':{'num_ctx':8192,'temperature':0,'num_predict':256}}
    message=httpx.post(adapters.ollama_url()+'/api/chat',json=body,timeout=180).json()['message']
    return [c['function']['name'] for c in message.get('tool_calls') or []],message.get('content') or ''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spoken',action='store_true');parser.add_argument('--only',default='');parser.add_argument('--model',default=None)
    args=parser.parse_args()
    cases=[json.loads(line) for line in (ROOT/'tests/evals/jarvis_tools.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    schemas=[agent.tool_schema(tool) for tool in tools.REGISTRY.values()]
    available={tool for tool in tools.REGISTRY}
    passed=0;first_pass=0;missing=0;rows=[]
    for case in cases:
        if args.only and args.only not in case['text']:continue
        request={'response_mode':'companion','spoken':args.spoken,'language':'hinglish'}
        action=agent.action_requested(case['text']);direct=args.spoken and not action and agent.simple_spoken_question(case['text'])
        messages=[{'role':'system','content':agent.system_prompt(request,True,direct)},{'role':'user','content':agent.first_message(case['text'],[])+' (Current local date/time: 2026-10-28T18:00:00+05:30)'}]
        started=time.monotonic();calls,text=turn(messages,[] if direct else schemas,args.model);first=calls
        if not calls and not direct and (action or agent.claims_action(text)):
            calls,_=turn(messages+[{'role':'assistant','content':text},{'role':'user','content':agent.RECOVERY}],schemas,args.model)
        expected=case['expect'];unavailable=bool(expected) and not (set(expected)-{'none'})&available
        # "none" in expect means answering without a tool is also correct (e.g. memory already in the prompt).
        ok=bool(set(calls)&set(expected)) or ('none' in expected and not calls) if expected else not calls
        passed+=ok;first_pass+=(bool(set(first)&set(expected)) if expected else not first);missing+=unavailable
        rows.append((('PASS' if ok else 'MISSING' if unavailable else 'FAIL'),case['text'][:52],','.join(expected) or '-',','.join(calls) or '-',round(time.monotonic()-started,1)))
    for row in rows:print('{:7} | {:52} | want {:30} | got {:28} | {}s'.format(*row))
    total=len(rows);times=sorted(r[4] for r in rows)
    print(f'\n{passed}/{total} correct ({passed*100//max(total,1)}%), {first_pass}/{total} on the first try, {missing} need tools that do not exist yet. Median {times[total//2] if total else 0}s per request.')


if __name__=='__main__':main()
