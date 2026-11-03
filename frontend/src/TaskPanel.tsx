import {useEffect,useState} from 'react';
import TaskPicker from './TaskPicker';
export type API=<T>(route:string,method?:string,body?:unknown)=>Promise<T>;
export type ClientProps={api:API;action:(fn:()=>Promise<void>)=>Promise<void>;busy:boolean};
export type Task={id:string;title?:string;kind:string;project:string;state:string;step?:string;progress:number;created:number;started?:number;finished?:number;error?:string;error_code?:string;retryable?:boolean;payload?:{template?:{name:string;kind:string};[key:string]:unknown};result?:{text?:string;file?:string;download?:string;title?:string;[key:string]:unknown};events?:{id:number;type:string;created:number;body:{summary:string}}[]};
// Plain names for the tool receipts in the action card; unknown tools show their own name.
const TOOL_NAMES:Record<string,string>={'research.deep':'Researched the web','web.search':'Searched the web','web.open':'Opened a web page','media.play':'Played media','media.control':'Controlled playback','youtube.search':'Searched YouTube','video.describe':'Watched a video','file.find':'Searched files','file.open':'Opened a file','file.list':'Listed a folder','file.write':'Wrote a file','file.undo':'Undid a file change','app.open':'Opened an app','assistant.remind':'Set a reminder','assistant.add_task':'Added a task','assistant.today':'Checked today','note.add':'Saved a note','note.read':'Read notes','clipboard.read':'Read the clipboard','clipboard.write':'Copied to clipboard','screen.look':'Looked at the screen','system.monitor':'Checked the PC','system.large_files':'Found large files','memory.remember':'Remembered something','memory.search':'Searched memory','gmail.list':'Checked email','gmail.read':'Read an email','whatsapp.recent':'Checked WhatsApp','workflow.draft':'Drafted a workflow','workflow.change':'Changed a workflow'};
export const toolName=(name:string)=>TOOL_NAMES[name]||name;
// Activity in plain words: worker plumbing is hidden ('' = technical), tool and model steps are renamed.
export const friendlyStep=(text:string):string=>{
 if(/^(Worker started task|Run \S+; timeout|Running agent turn)/.test(text))return '';
 const tool=text.match(/^Running ([a-z_]+\.[a-z_]+)/);if(tool)return toolName(tool[1]);
 return ({'Task queued':'Request received','Qwen is choosing the next supported action':'Jarvis is thinking','Reply saved; tool receipts recorded':'Reply ready'} as Record<string,string>)[text]||text;
};
export const STATE_WORDS:Record<string,string>={completed:'Done',failed:'Failed',running:'Working',queued:'Waiting',cancelled:'Stopped',waiting_for_approval:'Needs your approval'};
const KIND_WORDS:Record<string,string>={agent_turn:'Jarvis reply',chat:'Chat answer',automation:'Automation',render:'Video render'};
export const kindName=(t:Task)=>KIND_WORDS[t.kind]||t.kind.replaceAll('_',' ');
// What the task was about: the conversation for Jarvis turns, the template name for workflows.
export const taskTitle=(t:Task)=>t.title||t.payload?.template?.name||kindName(t);
export const seconds=(t:Task)=>Math.max(0,Math.round((t.finished||(active(t)?Date.now()/1000:t.started||t.created))-(t.started||t.created)));
export const took=(n:number)=>n<60?n+' s':Math.floor(n/60)+' min '+(n%60?n%60+' s':'');
const VERIFY=/^No tool action was verified for this reply\.\n\n/;
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

export default function TaskPanel({api,action,busy,id,select,jobs,embedded}:{id:string;select:(id:string)=>void;jobs:Task[];embedded?:boolean}&ClientProps){
 const {task,connection}=useTask(id,api),[tab,setTab]=useState('Overview'),[,tick]=useState(0);
 useEffect(()=>{const timer=setInterval(()=>tick(v=>v+1),1000);return()=>clearInterval(timer)},[]);
 const elapsed=task?Math.max(0,Math.round((task.finished||Date.now()/1000)-(task.started||task.created))):0;
 const when=(t:number)=>new Date(t*1000).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit',second:'2-digit'});
 // The single-task API has no title; the list entry carries what was asked.
 const name=task?taskTitle(jobs.find(j=>j.id===task.id)||task):'';
 const reply=typeof task?.result?.text==='string'?task.result.text.replace(VERIFY,''):'';
 return <section className="taskPanel" aria-label="Task details">{!embedded&&<><h2>Task details</h2>
  <TaskPicker id={id} jobs={jobs} select={select}/></>}
  {!task?<p className="profileHint">{!id?'Choose a task to see what was asked, each step and the result.':connection==='Connecting'?'Loading task…':'This task could not be loaded. It may have been deleted.'}</p>:<>
   <div className="taskHead"><span className={'state '+task.state}>{STATE_WORDS[task.state]||task.state.replaceAll('_',' ')}</span><h3 title={name}>{name}</h3><small>{kindName(task)} · {active(task)?took(elapsed)+' so far':'took '+took(elapsed)}{connection==='Live'||connection==='Saved'?'':' · '+connection}</small></div>
   {active(task)&&<p role="status">{friendlyStep(task.step||'')||'Working…'}</p>}
   {active(task)&&<progress aria-label="Task progress" max={1} value={task.progress>0?task.progress:undefined}/>}
   {task.state==='queued'&&elapsed>15&&<p className="cmsCaution">Still waiting? The worker may not be running. Start Ninja with scripts\start.ps1.</p>}
   {task.state==='waiting_for_approval'&&<p className="cmsCaution">This task needs your approval. Open the Jarvis chat or YouTube publishing to review it.</p>}
   {task.error&&<div role="alert" className="error">{task.error}</div>}
   <div className="inline">{active(task)&&<button disabled={busy} onClick={()=>action(async()=>{await api('/jobs/'+task.id+'/cancel','POST',{})})}>Stop task</button>}
   {task.retryable&&<button disabled={busy} onClick={()=>action(async()=>{const r=await api<{job:string}>('/tasks/'+task.id+'/retry','POST',{request_key:crypto.randomUUID()});select(r.job)})}>Retry safely</button>}</div>
   <div className="segmented" role="group" aria-label="Task section">{['Overview','Steps','Output'].map(t=><button key={t} aria-pressed={tab===t} onClick={()=>setTab(t)}>{t}</button>)}</div>
   {tab==='Overview'&&<dl className="taskFacts">
    <div><dt>Request</dt><dd>{name}</dd></div>
    <div><dt>Type</dt><dd>{kindName(task)}</dd></div>
    <div><dt>Received</dt><dd>{when(task.created)}</dd></div>
    {task.finished&&<div><dt>Finished</dt><dd>{when(task.finished)}</dd></div>}
    <div><dt>Time taken</dt><dd>{active(task)?took(elapsed)+' so far':took(elapsed)}{task.started&&task.started-task.created>2?' (waited '+took(Math.round(task.started-task.created))+' in queue)':''}</dd></div>
    <div><dt>Steps</dt><dd>{task.events?.filter(e=>friendlyStep(e.body.summary)).length||0} recorded</dd></div>
    {reply&&<div><dt>Result</dt><dd className="taskReply">{reply.length>500?reply.slice(0,500)+'…':reply}</dd></div>}
    {task.error_code&&<div><dt>Error code</dt><dd><code>{task.error_code}</code></dd></div>}
   </dl>}
   {tab==='Steps'&&<><ol className="timeline">{task.events?.map(e=>({e,text:friendlyStep(e.body.summary)})).filter(x=>x.text).map(({e,text},i,list)=><li key={e.id} className={i===list.length-1?'last':''}><span>{text}</span><small>{i===0?new Date(e.created*1000).toLocaleTimeString([],{hour:'numeric',minute:'2-digit',second:'2-digit'}):'+'+Math.max(0,Math.round(e.created-list[0].e.created))+' s'}</small></li>)}</ol>
   <details className="techLog"><summary>Technical log</summary><ol>{task.events?.map(e=><li key={e.id}><small>{new Date(e.created*1000).toLocaleTimeString()}</small> {e.body.summary}</li>)}</ol></details>
   {task.result?.text&&active(task)&&<div className="answer partial"><small>Partial answer · not complete</small><p>{task.result.text}</p></div>}</>}
   {tab==='Output'&&(task.state==='completed'?<><p>{task.result?.title||'Saved task result'}</p>{task.result?.download&&<a className="button" href={task.result.download}>Download report</a>}{task.result?.file&&<a className="button" href={'/api/projects/'+task.project+'/files/'+task.result.file} target="_blank" rel="noreferrer">Preview / download video</a>}{reply?<div className="answer">{reply}</div>:<details><summary>Result details</summary><pre>{JSON.stringify(task.result,null,2)}</pre></details>}</>:<p>The result appears here when the task finishes. Live progress is under Steps.</p>)}
  </>}
 </section>;
}
