import {useEffect,useRef,useState} from 'react';
import {API} from './TaskPanel';
import Icon from './Icons';

export type Models={provider:'ollama'|'cloud';model:string;local:string[];cloud:{model:string;host:string;ready:boolean}};
type Choice={provider:'ollama'|'cloud';model:string};

// Composer model picker: installed Ollama models, plus the .env cloud model when it is set up.
// A small menu above the button; Esc or a click outside closes it.
export default function ModelPicker({api,onChange}:{api:API;onChange?:(m:Models)=>void}){
 const [models,setModels]=useState<Models>(),[open,setOpen]=useState(false),[error,setError]=useState('');
 const box=useRef<HTMLDivElement>(null);
 const apply=(m:Models)=>{setModels(m);onChange?.(m)};
 useEffect(()=>{api<Models>('/assistant/models').then(apply).catch(()=>{})},[]);
 useEffect(()=>{if(!open)return;
  const away=(e:MouseEvent)=>{if(!box.current?.contains(e.target as Node))setOpen(false)};
  const esc=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false)};
  document.addEventListener('mousedown',away);document.addEventListener('keydown',esc);
  return()=>{document.removeEventListener('mousedown',away);document.removeEventListener('keydown',esc)}},[open]);
 if(!models)return null;
 const choose=(c:Choice)=>{setOpen(false);setError('');api<Models>('/assistant/models','PUT',c.provider==='cloud'?{provider:'cloud'}:c).then(apply).catch(e=>setError(String(e)))};
 const item=(c:Choice,label:string,note:string)=>{const on=models.provider===c.provider&&(c.provider==='cloud'||models.model===c.model);
  return <button type="button" role="menuitemradio" aria-checked={on} key={c.provider+c.model} onClick={()=>choose(c)}><span><strong>{label}</strong><small>{note}</small></span>{on&&<Icon name="check" size={14}/>}</button>};
 return <div className="modelPicker" ref={box}>
  <button type="button" className={'modelButton'+(error?' bad':'')} aria-haspopup="menu" aria-expanded={open} title={error||'Choose the model Jarvis uses'} onClick={()=>setOpen(v=>!v)}>
   <span className={'modelDot '+models.provider} aria-hidden="true"/>{models.model||'Choose model'}<Icon name="chevron" size={12}/>
  </button>
  {open&&<div className="modelMenu" role="menu" aria-label="Model">
   <p>On this PC</p>
   {models.local.map(m=>item({provider:'ollama',model:m},m,'Private · runs on your GPU'))}
   {!models.local.length&&<small className="modelEmpty">Start Ollama to see local models.</small>}
   <p>Cloud API</p>
   {models.cloud.ready?item({provider:'cloud',model:models.cloud.model},models.cloud.model,'Sends chats to '+models.cloud.host):<small className="modelEmpty">Add CLOUD_* settings to .env, then restart Ninja.</small>}
  </div>}
 </div>;
}
