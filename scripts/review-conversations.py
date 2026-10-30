"""Review real Jarvis conversations and flag where they went wrong.

Run from the project root:
  .venv\\Scripts\\python.exe scripts\\review-conversations.py [--hours 24]
Flags: replies that claimed or promised an action no tool backed, failed tools, turns that needed the
recovery retry, slow turns, and transcripts the speech recogniser probably garbled. Read-only.
"""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from ninja import db,agent,assistant_tools  # noqa: F401  (assistant_tools fills the tool registry)

SLOW=8.0

def review(task):
    issues=[];messages=task.get('messages',[])
    for i in sorted(agent.unbacked(messages)):
        asked=next((m['content'] for m in reversed(messages[:i]) if m['role']=='user' and not agent.recovery(m)),'')
        issues.append(('unbacked claim',asked,messages[i]['content']))
    for m in messages:
        if m.get('role')=='tool':
            result=json.loads(m['content']) if m['content'].startswith('{') else {}
            if result.get('verified') is False and not result.get('declined'):issues.append(('tool failed',m.get('tool_name',''),result.get('error','')))
    seconds=task.get('timing',{}).get('model_seconds')
    if isinstance(seconds,(int,float)) and seconds>SLOW:issues.append(('slow turn',task['conversation'][-2]['content'] if len(task.get('conversation',[]))>1 else '',f'{seconds:.1f} s of model time'))
    for turn in task.get('conversation',[]):
        text=turn['content']
        # Mixed Devanagari fragments with no Hindi grammar words are usually misheard English.
        if turn['role']=='user' and any('ऀ'<=ch<='ॿ' for ch in text) and not any(w in text for w in ('है','हैं','का','की','के','को','में','करो','क्या','नहीं','दो','मैं','आप')):
            issues.append(('possibly misheard',text,''))
    return issues

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--hours',type=float,default=24);args=parser.parse_args()
    since=time.time()-args.hours*3600
    with db.connect() as c:rows=c.execute('SELECT body FROM agent_tasks WHERE updated>=? ORDER BY updated',(since,)).fetchall()
    total=0
    for row in rows:
        task=json.loads(row[0]);issues=review(task)
        if not issues:continue
        total+=len(issues)
        print(f"\n== {task['id'][:8]} · {'voice' if task['request'].get('spoken') else 'typed'} · {len(task.get('conversation',[]))//2} turns · {task['text'][:50]!r}")
        for kind,where,detail in issues:print(f'  [{kind}] {where[:90]!r}' + (f' -> {detail[:110]!r}' if detail else ''))
    print(f'\n{len(rows)} conversations in the last {args.hours:g} h, {total} issues.')

if __name__=='__main__':main()
