import {useEffect,useState} from 'react';
export type API=<T>(route:string,method?:string,body?:unknown)=>Promise<T>;
export type ClientProps={api:API;action:(fn:()=>Promise<void>)=>Promise<void>;busy:boolean};
export type Task={id:string;kind:string;project:string;state:string;step?:string;progress:number;created:number;started?:number;finished?:number;error?:string;error_code?:string;retryable?:boolean;payload?:{template?:{name:string;kind:string};[key:string]:unknown};result?:{text?:string;file?:string;download?:string;title?:string;[key:string]:unknown};events?:{id:number;type:string;created:number;body:{summary:string}}[]};
export const active=(t:Task)=>['queued','running'].includes(t.state);
export function useTask(id:string,api:API){
 const [task,setTask]=useState<Task|null>(null),[connection,setConnection]=useState('Connecting');
 useEffect(()=>{
  setTask(null);if(!id)return;
  let alive=true,received=false;const stream=new EventSource('/api/tasks/'+id+'/stream');
  api<Task>('/tasks/'+id).then(t=>{if(alive&&!received)setTask(t)}).catch(()=>{if(alive)setConnection('Reconnecting')});
  stream.onopen=()=>setConnection('Live');
  stream.onmessage=e=>{if(!alive)return;received=true;const t=JSON.parse(e.data) as Task;setTask(t);setConnection('Live');if(!active(t)){stream.close();setConnection('Saved')}};
  stream.onerror=()=>setConnection('Reconnecting; saved state is safe');
  return()=>{alive=false;stream.close()};
 },[id]);
 return {task,connection};
}

export default function TaskPanel({api,action,busy,id,select,jobs}:{id:string;select:(id:string)=>void;jobs:Task[]}&ClientProps){
 const {task,connection}=useTask(id,api),[tab,setTab]=useState('Activity'),[,tick]=useState(0);
 useEffect(()=>{const timer=setInterval(()=>tick(v=>v+1),1000);return()=>clearInterval(timer)},[]);
 const elapsed=task?Math.max(0,Math.round((task.finished||Date.now()/1000)-(task.started||task.created))):0;
 return <section className="taskPanel" aria-label="Task context"><h2>Task workspace</h2>
  <label>Recent tasks<select value={id} onChange={e=>select(e.target.value)}><option value="">Choose a task</option>{jobs.map(j=><option key={j.id} value={j.id}>{j.payload?.template?.name||j.kind.replaceAll('_',' ')} · {j.state.replaceAll('_',' ')}</option>)}</select></label>
  <div className="segmented" role="group" aria-label="Task panel section">{['Plan','Activity','Outputs'].map(t=><button key={t} aria-pressed={tab===t} onClick={()=>setTab(t)}>{t}</button>)}</div>
  {!task?<p>Select a task to see its saved plan, observable steps and outputs.</p>:<>
   <div className="inline"><span className={'state '+task.state}>{task.state.replaceAll('_',' ')}</span><small>{elapsed}s · {connection}</small></div>
   <p role="status">{task.step||'Waiting for worker'}</p>
   {active(task)&&<progress aria-label="Task progress" max={1} value={task.progress>0?task.progress:undefined}/>}
   {task.state==='queued'&&elapsed>15&&<p>Still queued? Keep the separate worker running. Check Settings → Runtime setup.</p>}
   {task.state==='waiting_for_approval'&&<p>Open Projects to review the saved recording, or Automations → YouTube publishing &amp; approvals for publishing requests.</p>}
   {task.error&&<div role="alert" className="error">{task.error}</div>}
   {active(task)&&<button disabled={busy} onClick={()=>action(async()=>{await api('/jobs/'+task.id+'/cancel','POST',{})})}>Cancel task</button>}
   {task.retryable&&<button disabled={busy} onClick={()=>action(async()=>{const r=await api<{job:string}>('/tasks/'+task.id+'/retry','POST',{request_key:crypto.randomUUID()});select(r.job)})}>Retry safely</button>}
   {tab==='Plan'&&<ol>{(task.kind==='automation'?(task.payload?.template?.kind==='diagnostics'?['Run selected read-only checks','Summarize findings and proposed fixes','Save report']:['Retrieve supplied sources','Generate a source-cited draft','Validate references and save output']):task.kind==='chat'?['Use this conversation and selected attachments','Generate visible answer','Save answer in conversation']:['Validate saved inputs and approvals','Run '+task.kind.replaceAll('_',' '),'Verify and store the result']).map(s=><li key={s}>{s}</li>)}</ol>}
   {tab==='Activity'&&<><ol className="activity">{task.events?.map(e=><li key={e.id}><small>{new Date(e.created*1000).toLocaleTimeString()}</small><p>{e.body.summary}</p></li>)}</ol>{task.result?.text&&active(task)&&<div className="answer partial"><small>Partial answer · not complete</small><p>{task.result.text}</p></div>}</>}
   {tab==='Outputs'&&(task.state==='completed'?<><p>{task.result?.title||'Saved task result'}</p>{task.result?.download&&<a className="button" href={task.result.download}>Download report</a>}{task.result?.file&&<a className="button" href={'/api/projects/'+task.project+'/files/'+task.result.file} target="_blank" rel="noreferrer">Preview / download video</a>}{task.result?.text?<div className="answer">{task.result.text}</div>:<details><summary>Result details</summary><pre>{JSON.stringify(task.result,null,2)}</pre></details>}</>:<p>Verified outputs appear after completion. Partial answers are visible under Activity.</p>)}
  </>}
 </section>;
}
