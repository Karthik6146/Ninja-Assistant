import {useEffect,useRef,useState} from 'react';
import {API} from './TaskPanel';
import Icon from './Icons';

export type Models={provider:'ollama'|'cloud';model:string;local:string[];memory?:Record<string,{disk:number|null;vram:number|null}>;cloud:{model:string;host:string;ready:boolean}};
type Info={model:string;details:{family?:string;parameter_size?:string;quantization_level?:string;format?:string};capabilities:string[];parameters:number|null;context_max:number|null;disk_bytes:number|null;
 loaded:{size:number;size_vram:number;context_length:number}|null;gpu:{name:string;load:number;memory_used:number;memory_total:number;temperature:number}|null;
 speed:{turns:number;output_per_second:number|null;prompt_per_second:number|null;first_text_seconds:number|null;turn_seconds:number|null;load_seconds:number|null}|null};
// 'huihui_ai/qwen3.5-abliterated:4b' shows as 'qwen3.5-abliterated:4b'; the menu keeps the full name.
export const shortName=(model:string)=>model.split('/').pop()||model;
const gigs=(bytes:number)=>(bytes/2**30).toFixed(1)+' GB';
const ctx=(n:number)=>n>=1024?Math.round(n/1024)+'k':String(n);
const per=(n:number|null|undefined,unit:string)=>n==null?'—':(n>=100?Math.round(n):n)+' '+unit;
type Choice={provider:'ollama'|'cloud';model:string};

// A local model's facts, GPU load and measured speed, refreshed every 3 seconds while shown.
// Used in the picker's "i" popover and inline in Settings.
export function ModelInfo({api,model}:{api:API;model:string}){
 const [info,setInfo]=useState<Info>(),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const url='/assistant/models/info?model='+encodeURIComponent(model);
 const unload=()=>{setBusy(true);setError('');api('/assistant/models/unload','POST',{model}).then(()=>api<Info>(url).then(setInfo)).catch(e=>setError(String(e))).finally(()=>setBusy(false))};
 useEffect(()=>{
  const load=()=>api<Info>(url).then(setInfo).catch(()=>{});
  load();const timer=setInterval(load,3000);return()=>clearInterval(timer)},[model]);
 const shown=info?.model===model?info:undefined,gpu=shown?.gpu,speed=shown?.speed;
 const bar=(value:number,label:string)=><span className="infoBar" role="meter" aria-label={label} aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100}><i style={{width:Math.min(100,value)+'%'}}/></span>;
 return <div className="modelInfo">
  <div className="infoHead"><strong title={model}>{shortName(model)}</strong><span className={'infoLoaded'+(shown?.loaded?' on':'')}>{!shown?'Checking…':shown.loaded?'In GPU memory':'Not loaded'}</span>
   {shown?.loaded&&<button type="button" className="infoUnload" disabled={busy} title="Free its VRAM now; the next chat loads it again" onClick={unload}>{busy?'Unloading…':'Unload'}</button>}</div>
  {error&&<small className="infoError" role="alert">{error}</small>}
  {shown&&<>
   <section><p>Model</p><dl>
    <div><dt>Size</dt><dd>{shown.details.parameter_size||'—'} parameters</dd></div>
    <div><dt>Quantization</dt><dd>{shown.details.quantization_level||'—'}</dd></div>
    <div><dt>Weights on disk</dt><dd>{shown.disk_bytes?gigs(shown.disk_bytes):'—'}</dd></div>
    <div><dt>Context</dt><dd>{ctx(shown.loaded?.context_length||8192)} used{shown.context_max?' of '+ctx(shown.context_max)+' max':''}</dd></div>
    {shown.loaded&&<div><dt>In memory</dt><dd>{gigs(shown.loaded.size)}{shown.loaded.size_vram<shown.loaded.size?' · '+Math.round(100*shown.loaded.size_vram/shown.loaded.size)+'% on GPU':' · all on GPU'}</dd></div>}
   </dl>{!!shown.capabilities.length&&<div className="infoTags">{shown.capabilities.map(c=><span key={c}>{c}</span>)}</div>}</section>
   <section><p>GPU{gpu?' · '+gpu.name.replace(/^NVIDIA (GeForce )?/,''):''}</p>{gpu?<dl>
    <div><dt>Load</dt><dd>{bar(gpu.load,'GPU load')}{gpu.load}%</dd></div>
    <div><dt>VRAM</dt><dd>{bar(100*gpu.memory_used/gpu.memory_total,'VRAM used')}{gigs(gpu.memory_used)} / {gigs(gpu.memory_total)}</dd></div>
    <div><dt>Temperature</dt><dd>{gpu.temperature} °C</dd></div>
   </dl>:<small className="modelEmpty">No NVIDIA GPU found.</small>}</section>
   <section><p>Speed{speed?' · last '+speed.turns+' turns':''}</p>{speed?<dl>
    <div><dt>Writing</dt><dd>{per(speed.output_per_second,'tokens/s')}</dd></div>
    <div><dt>Reading prompt</dt><dd>{per(speed.prompt_per_second,'tokens/s')}</dd></div>
    <div><dt>First words</dt><dd>{per(speed.first_text_seconds,'s')}</dd></div>
    <div><dt>Per turn</dt><dd>{per(speed.turn_seconds,'s')}</dd></div>
   </dl>:<small className="modelEmpty">Ask Jarvis something to measure it.</small>}</section>
  </>}
 </div>;
}

// Composer model picker: installed Ollama models, plus the .env cloud model when it is set up.
// The "i" button beside it opens ModelInfo for the local model. Esc or a click outside closes either popover.
export default function ModelPicker({api,onChange,down}:{api:API;onChange?:(m:Models)=>void;down?:boolean}){
 const [models,setModels]=useState<Models>(),[open,setOpen]=useState<''|'menu'|'info'>(''),[error,setError]=useState('');
 const box=useRef<HTMLDivElement>(null);
 const apply=(m:Models)=>{setModels(m);onChange?.(m)};
 useEffect(()=>{api<Models>('/assistant/models').then(apply).catch(()=>{})},[]);
 useEffect(()=>{if(!open)return;
  const away=(e:MouseEvent)=>{if(!box.current?.contains(e.target as Node))setOpen('')};
  const esc=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen('')};
  document.addEventListener('mousedown',away);document.addEventListener('keydown',esc);
  return()=>{document.removeEventListener('mousedown',away);document.removeEventListener('keydown',esc)}},[open]);
 if(!models)return null;
 const local=models.provider==='ollama'&&models.model;
 const choose=(c:Choice)=>{setOpen('');setError('');api<Models>('/assistant/models','PUT',c.provider==='cloud'?{provider:'cloud'}:c).then(apply).catch(e=>setError(String(e)))};
 const unload=(model:string)=>{setError('');api<Models>('/assistant/models/unload','POST',{model}).then(setModels).catch(e=>setError(String(e)))};
 const item=(c:Choice,label:string,note:string)=>{const on=models.provider===c.provider&&(c.provider==='cloud'||models.model===c.model);
  const pick=<button type="button" role="menuitemradio" aria-checked={on} key={c.provider+c.model} onClick={()=>choose(c)}><span><strong>{label}</strong><small>{note}</small></span>{on&&<Icon name="check" size={14}/>}</button>;
  // A loaded local model gets an Unload button beside it, outside the menu item so the two clicks stay separate.
  return c.provider==='ollama'&&models.memory?.[c.model]?.vram?<div className="modelRow" key={c.model}>{pick}<button type="button" className="modelUnload" aria-label={'Unload '+c.model+' from VRAM'} title="Free its VRAM now" onClick={()=>unload(c.model)}>Unload</button></div>:pick};
 // Loaded models report real VRAM; an unloaded one needs about its file size.
 const vram=(m:string)=>{const v=models.memory?.[m];return v?.vram?'In VRAM · '+gigs(v.vram):v?.disk?'Not loaded · needs ~'+gigs(v.disk):'Private · runs on your GPU'};
 return <div className="modelPicker" ref={box}>
  <button type="button" className={'modelButton'+(error?' bad':'')} aria-haspopup="menu" aria-expanded={open==='menu'} title={error||(models.model?models.model+' · ':'')+'Choose the model Jarvis uses'} onClick={()=>{if(open!=='menu')api<Models>('/assistant/models').then(setModels).catch(()=>{});setOpen(v=>v==='menu'?'':'menu')}}>
   <span className={'modelDot '+models.provider} aria-hidden="true"/><span className="modelName">{shortName(models.model)||'Choose model'}</span><Icon name="chevron" size={12}/>
  </button>
  {local&&<button type="button" className="modelInfoButton" aria-expanded={open==='info'} aria-label="Model details" title="Model, GPU and speed" onClick={()=>setOpen(v=>v==='info'?'':'info')}><Icon name="info" size={15}/></button>}
  {open==='menu'&&<div className={'modelMenu'+(down?' down':'')} role="menu" aria-label="Model">
   <p>On this PC</p>
   {models.local.map(m=>item({provider:'ollama',model:m},m,vram(m)))}
   {!models.local.length&&<small className="modelEmpty">Start Ollama to see local models.</small>}
   <p>Cloud API</p>
   {models.cloud.ready?item({provider:'cloud',model:models.cloud.model},models.cloud.model,'Sends chats to '+models.cloud.host):<small className="modelEmpty">Add CLOUD_* settings to .env, then restart Ninja.</small>}
  </div>}
  {open==='info'&&local&&<div className={'modelMenu modelInfoPop'+(down?' down':'')} role="dialog" aria-label="Model details"><ModelInfo api={api} model={local}/></div>}
 </div>;
}

// Composer bar chip: GPU temperature, load, VRAM and the chat model's writing speed every 5 seconds; hidden without an NVIDIA GPU.
export function GpuTemp({api}:{api:API}){
 const [gpu,setGpu]=useState<Info['gpu']>(null),[rate,setRate]=useState<number|null>(null);
 useEffect(()=>{
  // Not gated on document.hidden: a tab opened in the background skipped its first load and showed nothing.
  const load=()=>api<{gpu:Info['gpu'];tokens_per_second:number|null}>('/assistant/gpu').then(v=>{setGpu(v.gpu);setRate(v.tokens_per_second)}).catch(()=>{});
  load();const timer=setInterval(load,5000);return()=>clearInterval(timer)},[]);
 if(!gpu)return null;
 const heat=gpu.temperature>=80?' hot':gpu.temperature>=70?' warm':'';
 return <span className={'gpuTemp'+heat} role="status" title={gpu.name+' · temperature, load, VRAM used of total'+(rate!=null?', writing speed over the last 20 replies':'')}>GPU {gpu.temperature}°C<span className="gpuLoad">{gpu.load}%</span><span className="gpuLoad gpuVram">{(gpu.memory_used/2**30).toFixed(1)}/{gigs(gpu.memory_total)}</span>{rate!=null&&<span className="gpuLoad gpuRate">{Math.round(rate)} tok/s</span>}</span>;
}
