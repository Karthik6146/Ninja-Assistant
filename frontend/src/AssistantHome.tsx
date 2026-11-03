import {useEffect,useState} from 'react';
import {ClientProps} from './TaskPanel';
import {useDraft} from './useDraft';
import Icon from './Icons';
type Advice={reply:string;question:string;suggestions:{text:string;mode:string}[];model:string};
type Today={revision:number;date:string;timezone:string;greeting:string;model:string;tasks:{id:string;text:string;done:boolean}[];messages:{id:string;state:string;step:string;error?:string;text:string;advice?:Advice}[];upcoming:{id:string;name:string;next_run:number;timezone:string}[]};
export default function AssistantHome({settings,...props}:ClientProps&{settings:()=>void}){
 const {api,action,busy}=props,[data,setData]=useState<Today|null>(null),[error,setError]=useState('');
 const [draft,setDraft]=useDraft('ninja-assistant-home',{priority:'',text:''});
 async function refresh(){setData(await api<Today>('/assistant/today'));setError('')}
 useEffect(()=>{let alive=true,inflight=false;const poll=async()=>{if(inflight)return;inflight=true;try{const d=await api<Today>('/assistant/today');if(alive){setData(d);setError('')}}catch(e){if(alive)setError(String(e))}finally{inflight=false}};poll();const t=setInterval(poll,3000);return()=>{alive=false;clearInterval(t)}},[]);
 async function save(tasks:Today['tasks']){if(!data)return;try{setData(await api<Today>('/assistant/today','PUT',{revision:data.revision,tasks}));setDraft({...draft,priority:''})}catch(e){setError(String(e))}}
 const tasks=data?.tasks||[],done=tasks.filter(t=>t.done).length,full=tasks.length>=30;
 const add=()=>{const text=draft.priority.trim();if(text&&data&&!busy&&!full)void action(()=>save([...tasks,{id:crypto.randomUUID().replaceAll('-',''),text,done:false}]))};
 // Open tasks stay on top; finished ones sink below them in their original order.
 const ordered=[...tasks].sort((a,b)=>Number(a.done)-Number(b.done));
 return <section className="todayPanel">
  <div className="todayIntro"><p className="todayDate">{data?new Date(data.date+'T00:00').toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long'}):'Today'}</p><h2>What shall we work on today?</h2><p>{data?.greeting||'Loading your day…'}</p></div>
  {error&&<p role="alert" className="error">{error}<button type="button" onClick={()=>action(refresh)}>Retry</button><button type="button" onClick={settings}>Open Settings</button></p>}
  <form className="todayAdd" onSubmit={e=>{e.preventDefault();add()}}><input aria-label="Add a task" maxLength={200} value={draft.priority} onChange={e=>setDraft({...draft,priority:e.target.value})} placeholder={full?'30 tasks is the limit for a day':'Add a task and press Enter'} disabled={full}/><button className="primary" aria-label="Add task" title="Add task" disabled={busy||!draft.priority.trim()||!data||full}><Icon name="plus" size={18}/></button></form>
  {!!tasks.length&&<div className="todayProgress"><span>{done===tasks.length?'All done for today':done+' of '+tasks.length+' done'}</span><div className="meter" role="meter" aria-valuemin={0} aria-valuemax={tasks.length} aria-valuenow={done} aria-label="Tasks done"><i style={{width:done/tasks.length*100+'%'}}/></div></div>}
  <ul className="todayList">{ordered.map(t=><li key={t.id} className={t.done?'done':''}><label><input type="checkbox" checked={t.done} disabled={busy} onChange={e=>action(()=>save(tasks.map(x=>x.id===t.id?{...x,done:e.target.checked}:x)))}/><span>{t.text}</span></label><button type="button" className="iconButton todayRemove" aria-label={'Remove task '+t.text} title="Remove" disabled={busy} onClick={()=>action(()=>save(tasks.filter(x=>x.id!==t.id)))}><Icon name="trash" size={15}/></button></li>)}</ul>
  {data&&!tasks.length&&<p className="todayEmpty">No tasks yet. Add one above, or tell Jarvis your priorities and it will help you pick what comes next.</p>}
  {!!data?.upcoming.length&&<details className="todayUpcoming"><summary>Upcoming workflows · {data.upcoming.length}</summary><ul>{data.upcoming.map(w=><li key={w.id}><span>{w.name}</span><small>{new Date(w.next_run*1000).toLocaleString('en-IN',{timeZone:w.timezone,weekday:'short',day:'numeric',month:'short',hour:'numeric',minute:'2-digit'})}</small></li>)}</ul></details>}
  {data&&<small className="todayMeta">{data.timezone||'Asia/Kolkata'} · {data.model||'No local model chosen'}</small>}
 </section>;
}
