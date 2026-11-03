import {useEffect,useState} from 'react';
import {ClientProps} from './TaskPanel';
export type Provider={id:string;name:string;scope:string;available:boolean;model:string;models:string[];message:string};
import {CaptionTool} from './MediaWorkspace';
import MemoryPanel from './MemoryPanel';
import ModelPicker,{ModelInfo,Models} from './ModelPicker';
export type Integrations={caption:CaptionTool;dependencies:Record<string,boolean>;optional:{name:string;status:string;message:string}[];roots:string[];tools:{name:string;permission:string;timeout:number}[]};
const Dot=({ok}:{ok:boolean})=><i className={'setDot'+(ok?' ok':'')} aria-hidden="true"/>;
export default function Settings({api,action,busy,creator,openSetup,providers,integrations,refresh,lock}:ClientProps&{creator:boolean;openSetup:()=>void;providers:Provider[];integrations:Integrations|null;refresh:()=>Promise<void>;lock:()=>void}){
 const [url,setUrl]=useState(''),[path,setPath]=useState(''),[notice,setNotice]=useState(''),[audit,setAudit]=useState<unknown[]>([]),[chosen,setChosen]=useState<Models>();
 useEffect(()=>{setUrl(integrations?.caption.url||'');setPath(integrations?.caption.path||'')},[integrations?.caption.url,integrations?.caption.path]);
 const local=providers.find(p=>p.id==='ollama'),cloud=providers.find(p=>p.id==='cloud');
 const deps=Object.entries(integrations?.dependencies||{}),missing=deps.filter(([,ok])=>!ok).map(([n])=>n),roots=integrations?.roots||[];
 // One line per part of the setup, so problems are visible before opening any section.
 const status:[string,boolean,string][]=[
  ['Local AI',!!local?.available,local?.available?local.model||'No model chosen':local?.message||'Ollama not running'],
  ['Cloud AI',!!cloud?.available,cloud?.available?cloud.model:'Off'],
  // Video tools and the caption tool belong to Studio, so only the creator build lists them.
  ...(creator?[['Video tools',!!deps.length&&!missing.length,missing.length?'Missing '+missing.join(', '):deps.length+' of '+deps.length+' ready'],
  ['Caption tool',!!integrations?.caption.available,integrations?.caption.available?'Running':integrations?.caption.configured?'Offline':'Not set up']] as [string,boolean,string][]:[]),
  ['File access',roots.length>0,roots.length?roots.length+' folder'+(roots.length>1?'s':''):'No folders approved'],
 ];
 return <div className="settingsPage">
 <div className="sectionTitle"><div><h2>Setup and status</h2><p>Everything runs on this computer. API keys stay in <code>.env</code> on the backend.</p></div><div className="inline"><button disabled={busy} onClick={()=>action(refresh)}>Refresh</button><button onClick={lock}>Lock dashboard</button></div></div>
 <ul className="setStatus">{status.map(([name,ok,text])=><li key={name}><Dot ok={ok}/><span>{name}</span><strong title={text}>{text}</strong></li>)}</ul>
 {notice&&<p role="status" className="cmsNotice">{notice}</p>}

 <section className="card setCard"><div className="setHead"><h3>AI model</h3><button type="button" onClick={openSetup}>Check PC and models</button></div><p>{creator?'Jarvis and Studio use':'Jarvis uses'} this model for new tasks. You can also switch models from the chat box.</p>
  <div className="setRow"><Dot ok={!!local?.available}/><div><strong>Ollama on this PC</strong><small>{local?.available?local.models.length+' model'+(local.models.length===1?'':'s')+' installed':local?.message||'Not detected'}</small></div>
   <ModelPicker api={api} down onChange={m=>{setChosen(m);void refresh()}}/></div>
  {chosen?.provider==='ollama'&&chosen.model&&<ModelInfo api={api} model={chosen.model}/>}
  <div className="setRow"><Dot ok={!!cloud?.available}/><div><strong>Cloud API</strong><small>{cloud?.available?cloud.model+' · messages leave this PC':'Off. Nothing is sent online.'}</small></div></div>
  <details><summary>How to add a model or turn on cloud</summary><p>Add a local model: press <strong>Check PC and models</strong> to download one that fits this PC, or run <code>ollama pull MODEL_NAME</code> and press Refresh.</p><p>Turn on cloud: set <code>CLOUD_ENABLED=true</code>, <code>CLOUD_URL</code>, <code>CLOUD_MODEL</code> and <code>CLOUD_API_KEY</code> in <code>.env</code>, then restart Ninja. Each run asks before sharing.</p></details>
 </section>

 <MemoryPanel api={api} action={action} busy={busy}/>

 {creator&&<section className="card setCard"><h3>Video tools</h3>
  <div className="setChips">{deps.map(([name,ok])=><span key={name} className={ok?'ok':'bad'}><Dot ok={ok}/>{name}</span>)}</div>
  {!!missing.length&&<p className="cmsCaution">Install {missing.join(', ')}, add {missing.length>1?'them':'it'} to PATH, then restart Ninja.</p>}
  <div className="setRow"><Dot ok={!!integrations?.caption.available}/><div><strong>ClipX caption tool</strong><small>{integrations?.caption.status||'Not configured'}</small></div></div>
  <details open={!integrations?.caption.configured}><summary>Caption tool connection</summary><div className="setFields"><label>Local URL<input placeholder="http://127.0.0.1:3000" value={url} onChange={e=>setUrl(e.target.value)}/></label><label>Project folder<input placeholder="C:\path\to\ClipX" value={path} onChange={e=>setPath(e.target.value)}/></label></div><button disabled={busy} onClick={()=>action(async()=>{await api('/integrations/caption','PUT',{url,path});await refresh();setNotice('Caption connection saved.')})}>Save connection</button><p>Start ClipX yourself: open PowerShell in its folder and run <code>npm run dev</code>. Ninja only opens it; videos are not sent automatically.</p></details>
 </section>}

 <section className="card setCard"><h3>System</h3>
  <div className="setRow"><Dot ok={roots.length>0}/><div><strong>Approved folders</strong><small>{roots.length?roots.join(' · '):'Jarvis cannot read or write your files yet.'}</small></div></div>
  <p>Set <code>NINJA_ROOTS</code> (folders Jarvis may use) and <code>NINJA_REPOS</code> (code repositories) in <code>.env</code>, then restart. Start Ninja with <code>scripts\start.ps1</code>; the API and the worker must both keep running.</p>
  <details><summary>Advanced: extensions, tools and audit log</summary>
   {integrations?.optional.map(o=><div className="setRow" key={o.name}><Dot ok={o.status!=='Not configured'}/><div><strong>{o.name}</strong><small>{o.status} · {o.message}</small></div></div>)}
   <details><summary>{integrations?.tools.length||0} tools Jarvis can call</summary><ul className="setTools">{integrations?.tools.map(t=><li key={t.name}><code>{t.name}</code><small>{t.permission} · {t.timeout}s limit</small></li>)}</ul></details>
   <button disabled={busy} onClick={()=>action(async()=>setAudit(await api('/audit')))}>Load audit records</button>{!!audit.length&&<pre>{JSON.stringify(audit,null,2)}</pre>}
  </details>
 </section>
 </div>;
}
