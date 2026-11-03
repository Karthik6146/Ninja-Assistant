import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
import {Project} from './types';
import TaskPanel,{Task} from './TaskPanel';
import Automations from './Automations';
import Recordings from './Recordings';
import AssistantHome from './AssistantHome';
import AssistantConsole from './AssistantConsole';
// Read before the area effect rewrites the hash: #voice means start voice mode at once (tray "Voice in background").
const AUTO_VOICE=/^#voice(?![\w-])/.test(location.hash)||sessionStorage.getItem('ninja-auto-voice')==='1';
sessionStorage.removeItem('ninja-auto-voice');
import './assistant.css';
import {Launch} from './GuidedStudio';
import ContentCMS from './ContentCMS';
import ActivityPage from './ActivityPage';
import YouTubePage from './YouTubePage';
import Settings,{Integrations,Provider} from './Settings';
import ContentStudio from './ContentStudio';
import SystemFiles from './SystemFiles';
import SetupWizard from './SetupWizard';
import Icon from './Icons';
import Drawer from './Drawer';
import './shell.css';
import './jarvis.css';

import {AREAS,STUDIO,Area,StudioTab,route,slug} from './routes';

function App(){
 const [{area:wanted,studio},setView]=useState(()=>route(location.hash));
 // Studio and YouTube exist only in the creator build (NINJA_CREATOR=1); elsewhere their links land on Jarvis.
 const [creator,setCreator]=useState(false),[setup,setSetup]=useState(false);
 const area:Area=creator||(wanted!=='Studio'&&wanted!=='YouTube')?wanted:'Jarvis';
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
 async function refresh(){const [p,j,s]=await Promise.all([api<{body:Project;created:number}[]>('/projects'),api<Task[]>('/jobs'),api<{stopped:boolean;creator:boolean}>('/status')]);setProjects(p.map(v=>({...v.body,created:v.created})));setJobs(j);setStopped(s.stopped);setCreator(s.creator);setOnline(true)}
 async function connections(){const [p,i,w]=await Promise.all([api<Provider[]>('/providers'),api<Integrations>('/integrations'),api<{id:string;name:string}[]>('/workspaces')]);setProviders(p);setIntegrations(i);setWorkspaces(w)}
 async function login(){await api('/session','POST',{token});sessionStorage.setItem('ninja-token',token);setConnected(true);await Promise.all([refresh(),connections()])
  // First run: no Ollama or no model yet opens the setup wizard.
  const state=await api<{ollama:{running:boolean;models:string[]}}>('/setup');if(!state.ollama.running||!state.ollama.models.length)setSetup(true)}
 // The desktop launcher opens #launch=<one-time code>: trade it for the token once, drop it from the address, reload signed in.
 useEffect(()=>{const code=new URLSearchParams(location.hash.slice(1)).get('launch');
  if(!code){if(token)action(login);return}
  // #launch=<code>&voice: start voice mode after the sign-in reload (tray "Voice in background"). Remembered in
  // sessionStorage because the area effect below rewrites the hash before the reload happens.
  if(new URLSearchParams(location.hash.slice(1)).has('voice'))sessionStorage.setItem('ninja-auto-voice','1');
  history.replaceState(null,'',location.pathname+location.search);
  action(async()=>{const v=await api<{token:string}>('/launch','POST',{code});sessionStorage.setItem('ninja-token',v.token);location.reload()})},[]);
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
   <span className="railMark" title="Ninja"><Icon name="jarvis" size={24} label="Ninja"/></span>
   <ul>{AREAS.filter(a=>creator||(a.name!=='Studio'&&a.name!=='YouTube')).map(a=><li key={a.name}><button type="button" className="railItem" aria-current={area===a.name?'page':undefined} onClick={()=>{setSetup(false);go(a.name)}}><Icon name={a.icon} size={22}/><span>{a.name}</span>{a.name==='Activity'&&running>0&&<b className="railCount" aria-label={running+' running'}>{running}</b>}</button></li>)}</ul>
   <button type="button" className={'railItem railStop'+(stopped?' engaged':'')} disabled={!connected||busy} title={stopped?'Resume execution':'Emergency stop: block new jobs and cancel running ones'} onClick={()=>action(async()=>{await api('/emergency','POST',{stopped:!stopped});await refresh()})}><Icon name="stop" size={22}/><span>{stopped?'Resume':'Stop'}</span></button>
  </nav>
  <main id="main">
   <header className="topbar">
    <h1>{setup?'Setup':area}</h1>
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
   {connected&&setup?<SetupWizard {...props} onDone={()=>{setSetup(false);go('Jarvis')}}/>:!connected?<section className="login"><Icon name="jarvis" size={44}/><h2>Your workspace, on your computer.</h2><p>Connect with the token in data/access-token, or your configured NINJA_TOKEN. No online account is needed.</p><form onSubmit={e=>{e.preventDefault();action(login)}}><label>Local access token<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)}/></label><button className="primary" disabled={busy||!token}><Icon name="lock" size={18}/>Connect</button></form></section>:<>
    {area==='Jarvis'&&<><AssistantConsole {...props} autoVoice={AUTO_VOICE} onTask={onTask} onDraft={workflow=>studioLaunch({workflow,mode:'clips',projects:[],nonce:Date.now()})}/>
     <Drawer open={today} onClose={()=>setToday(false)} title="Today" side="right"><AssistantHome {...props} settings={()=>{setToday(false);go('Settings')}}/></Drawer></>}
    {area==='Studio'&&studio==='Media Library'&&<Recordings {...props} projects={projects} jobs={jobs} refresh={refresh} onTask={onTask} tool={integrations?.caption||null} start={(mode,ids)=>studioLaunch({mode,projects:ids,nonce:Date.now()})}/>}
    {area==='Studio'&&(studio==='Video Studio'||studio==='Automations')&&<ContentCMS key={studio} {...props} projects={projects} refresh={refresh} onTask={onTask} settings={()=>go('Settings')} launch={studio==='Video Studio'?launch:undefined} onLaunch={()=>setLaunch(undefined)} automations={studio==='Automations'}/>}
    {area==='Studio'&&studio==='Automations'&&<details className="card"><summary>Research and report automations</summary><Automations {...props} providers={providers} onTask={onTask} jobs={jobs}/></details>}
    {area==='Studio'&&studio==='Content'&&<ContentStudio {...props} projects={projects} youtube={false}/>}
    {area==='YouTube'&&<YouTubePage {...props} projects={projects}/>}
    {area==='Activity'&&<div className="activityPage">
     <ActivityPage {...props} id={task} select={setTask} jobs={jobs}/>
     <section className="card outputsCard"><h2>Saved files <small>{files.length}</small></h2><p>Reports, rendered videos and your original media. Originals and earlier caption exports are kept.</p><ul>{files.map((f,i)=><li key={i}><span className="cmsBadge">{f.kind}</span><strong title={f.name}>{f.name}</strong><a className="button" href={f.url} target="_blank" rel="noreferrer">Open</a>{f.task&&<button onClick={()=>{setTask(f.task!);window.scrollTo({top:0,behavior:'smooth'})}}>Show task</button>}</li>)}</ul>{!files.length&&<p className="profileHint">No saved files yet. Run a workflow or import a recording.</p>}</section>
     <details className="card"><summary>Approved folders and logs</summary><SystemFiles {...props} roots={integrations?.roots||[]}/></details>
    </div>}
    {area==='Settings'&&<><Settings {...props} creator={creator} openSetup={()=>setSetup(true)} providers={providers} integrations={integrations} refresh={connections} lock={()=>{void api('/session/logout','POST',{}).catch(()=>{});sessionStorage.removeItem('ninja-token');setToken('');setConnected(false)}}/>
     <section className="card"><h2>Workspaces</h2><p>Workspaces give Jarvis a separate memory scope, for example one per client or project.</p><form className="inline" onSubmit={e=>{e.preventDefault();action(async()=>{await api('/workspaces','POST',{name:workspaceName});setWorkspaceName('');await connections()})}}><label>Workspace name<input value={workspaceName} maxLength={100} onChange={e=>setWorkspaceName(e.target.value)}/></label><button disabled={busy||!workspaceName.trim()}><Icon name="plus" size={18}/>Create workspace</button></form>{workspaces.map(w=><p key={w.id}>{w.name}</p>)}</section></>}
   </>}
  </main>{panel&&connected&&area!=='Activity'&&<TaskPanel {...props} id={task} select={setTask} jobs={jobs}/>}
 </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
