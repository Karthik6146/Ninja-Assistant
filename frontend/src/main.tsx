import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
import {Project} from './types';
import TaskPanel,{Task} from './TaskPanel';
import Automations from './Automations';
import Recordings from './Recordings';
import AssistantHome from './AssistantHome';
import AssistantConsole from './AssistantConsole';
import './assistant.css';
import {Launch} from './GuidedStudio';
import ContentCMS from './ContentCMS';
import StudioConnections from './StudioConnections';
import Settings,{Integrations,Provider} from './Settings';
import ContentStudio from './ContentStudio';
import YouTubeStudio from './YouTubeStudio';
import SystemFiles from './SystemFiles';
import Icon from './Icons';
import Drawer from './Drawer';
import './shell.css';
import './jarvis.css';

import {AREAS,STUDIO,Area,StudioTab,route,slug} from './routes';

function App(){
 const [{area,studio},setView]=useState(()=>route(location.hash));
 const go=(next:Area,tab?:StudioTab)=>setView(v=>({area:next,studio:tab||v.studio}));
 const [token,setToken]=useState(sessionStorage.getItem('ninja-token')||''),[connected,setConnected]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [projects,setProjects]=useState<Project[]>([]),[jobs,setJobs]=useState<Task[]>([]),[providers,setProviders]=useState<Provider[]>([]),[integrations,setIntegrations]=useState<Integrations|null>(null),[workspaces,setWorkspaces]=useState<{id:string;name:string}[]>([]);
 const [stopped,setStopped]=useState(false),[online,setOnline]=useState(true),[panel,setPanel]=useState(localStorage.getItem('ninja-panel')==='true'),[today,setToday]=useState(false);
 const [files,setFiles]=useState<{name:string;kind:string;url:string;task?:string}[]>([]);
 const [task,setTask]=useState(localStorage.getItem('ninja-task')||''),[launch,setLaunch]=useState<Launch>(),[workspaceName,setWorkspaceName]=useState('');
 async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
  let response:Response;
  try{response=await fetch('/api'+path,{method,headers:{'X-Ninja-Token':token,...(body instanceof FormData?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)})}catch{throw Error('Cannot reach Ninja. Start the local server and worker, then reconnect.')}
  if(!response.ok){let value;try{value=await response.json()}catch{value={detail:response.statusText}}throw Error(typeof value.detail==='string'?value.detail:JSON.stringify(value.detail))}
  return response.json() as Promise<T>;
 }
 async function action(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setBusy(false)}}
 async function refresh(){const [p,j,s]=await Promise.all([api<{body:Project;created:number}[]>('/projects'),api<Task[]>('/jobs'),api<{stopped:boolean}>('/status')]);setProjects(p.map(v=>({...v.body,created:v.created})));setJobs(j);setStopped(s.stopped);setOnline(true)}
 async function connections(){const [p,i,w]=await Promise.all([api<Provider[]>('/providers'),api<Integrations>('/integrations'),api<{id:string;name:string}[]>('/workspaces')]);setProviders(p);setIntegrations(i);setWorkspaces(w)}
 async function login(){await api('/session','POST',{token});sessionStorage.setItem('ninja-token',token);setConnected(true);await Promise.all([refresh(),connections()])}
 useEffect(()=>{if(token)action(login)},[]);
 useEffect(()=>{if(!connected)return;let inflight=false;const timer=setInterval(async()=>{if(inflight)return;inflight=true;try{await refresh()}catch{setOnline(false)}finally{inflight=false}},2500);return()=>clearInterval(timer)},[connected,token]);
 useEffect(()=>{const hash='#'+slug(area)+(area==='Studio'?'/'+slug(studio):'');if(location.hash!==hash)history.replaceState(null,'',hash);window.scrollTo({top:0,behavior:'auto'})},[area,studio]);
 useEffect(()=>{const handler=()=>setView(route(location.hash));window.addEventListener('hashchange',handler);return()=>window.removeEventListener('hashchange',handler)},[]);
 useEffect(()=>{if(area==='Activity'&&connected)action(async()=>setFiles(await api('/files')))},[area,connected,jobs.length,jobs.filter(j=>j.state==='completed').length]);
 useEffect(()=>{localStorage.setItem('ninja-panel',String(panel));localStorage.setItem('ninja-task',task)},[panel,task]);
 function onTask(id:string,open=true){setTask(id);if(open&&area!=='Activity')setPanel(true);refresh().catch(()=>setOnline(false))}
 const props={api,action,busy},running=jobs.filter(j=>['queued','running'].includes(j.state)).length;
 const studioLaunch=(value:Launch)=>{setLaunch(value);go('Studio','Video Studio')};
 return <div className={'app'+(panel&&connected&&area!=='Activity'?' hasPanel':'')} data-area={slug(area)}>
  <a className="skipLink" href="#main">Skip to workspace</a>
  <nav className="rail" aria-label="Main navigation">
   <span className="railMark" title="Ninja"><Icon name="jarvis" size={26} label="Ninja"/></span>
   <ul>{AREAS.map(a=><li key={a.name}><button type="button" className="railItem" aria-current={area===a.name?'page':undefined} onClick={()=>go(a.name)}><Icon name={a.icon} size={22}/><span>{a.name}</span>{a.name==='Activity'&&running>0&&<b className="railCount" aria-label={running+' running'}>{running}</b>}</button></li>)}</ul>
   <button type="button" className={'railItem railStop'+(stopped?' engaged':'')} disabled={!connected||busy} title={stopped?'Resume execution':'Emergency stop: block new jobs and cancel running ones'} onClick={()=>action(async()=>{await api('/emergency','POST',{stopped:!stopped});await refresh()})}><Icon name="stop" size={22}/><span>{stopped?'Resume':'Stop'}</span></button>
  </nav>
  <main id="main">
   <header className="topbar">
    <h1>{area}</h1>
    {area==='Studio'&&connected&&<div className="tabs" role="tablist" aria-label="Studio sections">{STUDIO.map(t=><button key={t} type="button" role="tab" aria-selected={studio===t} onClick={()=>go('Studio',t)}>{t}</button>)}</div>}
    <div className="topbarEnd">
     {area==='Jarvis'&&connected&&<button type="button" className="ghost" onClick={()=>setToday(true)}><Icon name="today" size={18}/>Today</button>}
     {connected&&area!=='Activity'&&<button type="button" className="ghost" aria-expanded={panel} onClick={()=>setPanel(!panel)}><Icon name="activity" size={18}/>{panel?'Hide activity':'Activity'}{running>0&&<b className="count">{running}</b>}</button>}
     <span className={'connection'+(!online?' offline':'')}>{busy?'Working…':connected?(online?'Local · connected':'Reconnecting'):'Locked'}</span>
    </div>
   </header>
   {error&&<div className="error" role="alert"><span>{error}</span><button onClick={()=>go('Settings')}>Open Settings</button><button onClick={()=>setError('')}>Dismiss</button></div>}
   {!online&&<div className="error" role="status">Connection interrupted. Saved conversations and tasks remain on disk; reconnecting automatically.</div>}
   {stopped&&<div className="error" role="alert">Emergency stop is active. Resume execution to run tasks. Already scheduled YouTube publications must be cancelled in YouTube.</div>}
   {!connected?<section className="login"><Icon name="jarvis" size={44}/><h2>Your workspace, on your computer.</h2><p>Connect with the token in data/access-token, or your configured NINJA_TOKEN. No online account is needed.</p><form onSubmit={e=>{e.preventDefault();action(login)}}><label>Local access token<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)}/></label><button className="primary" disabled={busy||!token}><Icon name="lock" size={18}/>Connect</button></form></section>:<>
    {area==='Jarvis'&&<><AssistantConsole {...props} onTask={onTask} onDraft={workflow=>studioLaunch({workflow,mode:'clips',projects:[],nonce:Date.now()})}/>
     <Drawer open={today} onClose={()=>setToday(false)} title="Today" side="right"><AssistantHome {...props} settings={()=>{setToday(false);go('Settings')}} studio={(text,mode)=>{setToday(false);studioLaunch({mode,projects:[],text,nonce:Date.now()})}}/></Drawer></>}
    {area==='Studio'&&studio==='Media Library'&&<Recordings {...props} projects={projects} jobs={jobs} refresh={refresh} onTask={onTask} tool={integrations?.caption||null} start={(mode,ids)=>studioLaunch({mode,projects:ids,nonce:Date.now()})}/>}
    {area==='Studio'&&(studio==='Video Studio'||studio==='Automations')&&<ContentCMS key={studio} {...props} projects={projects} refresh={refresh} onTask={onTask} settings={()=>go('Settings')} launch={studio==='Video Studio'?launch:undefined} onLaunch={()=>setLaunch(undefined)} automations={studio==='Automations'}/>}
    {area==='Studio'&&studio==='Automations'&&<details className="card"><summary>Research and report automations</summary><Automations {...props} providers={providers} onTask={onTask} jobs={jobs}/></details>}
    {area==='Studio'&&studio==='Content'&&<ContentStudio {...props} projects={projects} youtube={false}/>}
    {area==='YouTube'&&<><StudioConnections {...props}/><YouTubeStudio {...props}/><ContentStudio {...props} projects={projects} youtube/></>}
    {area==='Activity'&&<div className="activityPage">
     <TaskPanel {...props} id={task} select={setTask} jobs={jobs}/>
     <section className="card"><h2>Saved outputs and original media</h2><p>Managed project files and completed task outputs. Originals and earlier caption exports are preserved.</p>{files.map((f,i)=><div className="output" key={i}><span>{f.name} · {f.kind}</span><a href={f.url} target="_blank" rel="noreferrer">Preview / download</a>{f.task&&<button onClick={()=>setTask(f.task!)}>Task details</button>}</div>)}{!files.length&&<p>No outputs yet. Run a workflow or import a recording.</p>}</section>
     <details className="card"><summary>Approved folders and logs</summary><SystemFiles {...props} roots={integrations?.roots||[]}/></details>
    </div>}
    {area==='Settings'&&<><Settings {...props} providers={providers} integrations={integrations} refresh={connections} lock={()=>{void api('/session/logout','POST',{}).catch(()=>{});sessionStorage.removeItem('ninja-token');setToken('');setConnected(false)}}/>
     <section className="card"><h2>Workspaces</h2><p>Workspaces give Jarvis a separate memory scope, for example one per client or project.</p><form className="inline" onSubmit={e=>{e.preventDefault();action(async()=>{await api('/workspaces','POST',{name:workspaceName});setWorkspaceName('');await connections()})}}><label>Workspace name<input value={workspaceName} maxLength={100} onChange={e=>setWorkspaceName(e.target.value)}/></label><button disabled={busy||!workspaceName.trim()}><Icon name="plus" size={18}/>Create workspace</button></form>{workspaces.map(w=><p key={w.id}>{w.name}</p>)}</section></>}
   </>}
  </main>{panel&&connected&&area!=='Activity'&&<TaskPanel {...props} id={task} select={setTask} jobs={jobs}/>}
 </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
