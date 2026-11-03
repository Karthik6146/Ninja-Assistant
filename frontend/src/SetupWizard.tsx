import {useEffect,useState} from 'react';
import {ClientProps} from './TaskPanel';
import Icon from './Icons';

type Task={state:'running'|'done'|'failed';progress:number|null;message:string};
type Model={model:string;size:number;label:string;note:string;fit:'gpu'|'cpu'|'no'};
type Setup={system:{ram:number|null;cpu:string|null;cores:number|null;disk_free:number;gpu:{name:string;vram:number}|null;other_gpus:string[]};
 models:Model[];recommended:string|null;ollama:{installed:boolean;running:boolean;models:string[]};current:string;voice:{ready:boolean};tasks:Record<string,Task>};
const gb=(bytes:number|null|undefined)=>bytes==null?'—':(bytes/2**30).toFixed(bytes<10*2**30?1:0)+' GB';
const FIT={gpu:['Fast','Runs fully on your GPU'],cpu:['Slow','Spills onto the CPU and RAM'],no:['Too big','Not enough memory or disk']} as const;

// First-run setup: what this PC can run, then Ollama, a model and (optionally) voice, each installed on the user's click.
// The server runs the installs in the background; this page polls while one is running.
export default function SetupWizard({api,action,busy,onDone}:ClientProps&{onDone:()=>void}){
 const [setup,setSetup]=useState<Setup>(),[choice,setChoice]=useState('');
 const load=()=>api<Setup>('/setup').then(v=>{setSetup(v);setChoice(c=>c||v.models.some(m=>m.model===v.current)&&v.current||v.recommended||'')});
 const running=Object.values(setup?.tasks||{}).some(t=>t.state==='running');
 useEffect(()=>{void load().catch(()=>{})},[]);
 useEffect(()=>{if(!running)return;const timer=setInterval(()=>void load().catch(()=>{}),1000);return()=>clearInterval(timer)},[running]);
 if(!setup)return <section className="card setupPage"><p className="profileHint">Checking this PC…</p></section>;
 const {system:pc,ollama,tasks}=setup,start=(path:string,body?:unknown)=>action(async()=>{await api('/setup/'+path,'POST',body);await load()});
 const status=(kind:string)=>{const t=tasks[kind];return t&&<div className={'setupTask '+t.state} role="status">{t.state==='running'&&t.progress!=null&&<span className="setupBar"><i style={{width:Math.round(100*t.progress)+'%'}}/></span>}<small>{t.message}</small></div>};
 const picked=setup.models.find(m=>m.model===choice),installed=picked&&ollama.models.includes(picked.model),ready=!!setup.current&&ollama.models.includes(setup.current);
 return <div className="setupPage">
  <div className="setupIntro"><h2>Set up Ninja</h2><p>Ninja checks your PC and installs what Jarvis needs. Everything runs on this computer; nothing you say leaves it.</p></div>

  <section className="card setCard"><h3><span className="setupStep">1</span>Your PC</h3>
   <dl className="setupFacts">
    <div><dt>Processor</dt><dd>{pc.cpu||'Unknown'}{pc.cores?' · '+pc.cores+' threads':''}</dd></div>
    <div><dt>Memory</dt><dd>{gb(pc.ram)}</dd></div>
    <div><dt>Graphics</dt><dd>{pc.gpu?pc.gpu.name.replace(/^NVIDIA (GeForce )?/,'')+' · '+gb(pc.gpu.vram)+' VRAM':(pc.other_gpus.join(', ')||'No dedicated GPU')+' · models run on the CPU, slower'}</dd></div>
    <div><dt>Free disk</dt><dd>{gb(pc.disk_free)}</dd></div>
   </dl>
  </section>

  <section className="card setCard"><h3><span className={'setupStep'+(ollama.running?' done':'')}>{ollama.running?<Icon name="check" size={14}/>:'2'}</span>Ollama, the model runner</h3>
   <p>{ollama.running?'Running. '+(ollama.models.length?ollama.models.length+' model'+(ollama.models.length>1?'s':'')+' installed.':'No models yet.'):ollama.installed?'Installed but not running.':'Not installed. Ninja installs it with winget, which accepts Ollama\'s license for you.'}</p>
   {!ollama.running&&<button type="button" className="primary" disabled={busy||tasks.ollama?.state==='running'} onClick={()=>start('ollama')}>{ollama.installed?'Start Ollama':'Install Ollama'}</button>}
   {status('ollama')}
  </section>

  <section className="card setCard"><h3><span className={'setupStep'+(ready?' done':'')}>{ready?<Icon name="check" size={14}/>:'3'}</span>Choose a model</h3>
   <p>Bigger models answer better but need more memory. The recommended one is the largest that runs fast on this PC.</p>
   <div className="setupModels" role="radiogroup" aria-label="Model">
    {setup.models.map(m=><button type="button" role="radio" aria-checked={choice===m.model} key={m.model} className={'setupModel fit-'+m.fit} disabled={m.fit==='no'} onClick={()=>setChoice(m.model)}>
     <span className="setupModelHead"><strong>{m.model}</strong>{m.model===setup.recommended&&<em>Recommended</em>}{ollama.models.includes(m.model)&&<em className="have">Installed</em>}</span>
     <small>{m.label} · {m.size} GB download</small>
     <span className="setupFit" title={FIT[m.fit][1]}>{FIT[m.fit][0]}</span>
     <small className="setupNote">{m.note}</small>
    </button>)}
   </div>
   {picked&&<div className="inline">
    {installed?<button type="button" className="primary" disabled={busy||setup.current===picked.model} onClick={()=>action(async()=>{await api('/assistant/models','PUT',{provider:'ollama',model:picked.model});await load()})}>{setup.current===picked.model?'Selected for Jarvis':'Use '+picked.model}</button>
     :<button type="button" className="primary" disabled={busy||!ollama.running||tasks.pull?.state==='running'} onClick={()=>start('pull',{model:picked.model})}>Download {picked.model} ({picked.size} GB)</button>}
    {!ollama.running&&<small className="profileHint">Start Ollama first.</small>}
   </div>}
   {status('pull')}
  </section>

  <section className="card setCard"><h3><span className={'setupStep'+(setup.voice.ready?' done':'')}>{setup.voice.ready?<Icon name="check" size={14}/>:'4'}</span>Voice <small>optional</small></h3>
   <p>{setup.voice.ready?'Ready: speech recognition, Jarvis\'s voice and the "Hey Jarvis" wake word.':'Talk to Jarvis and hear replies. Downloads about 1.5 GB of speech models. The wake-word model is for personal, non-commercial use.'}</p>
   {!setup.voice.ready&&<button type="button" disabled={busy||tasks.voice?.state==='running'} onClick={()=>start('voice')}>Set up voice</button>}
   {status('voice')}
  </section>

  <div className="setupDone"><button type="button" className="primary" disabled={!ready||running} onClick={onDone}>{ready?'Start using Jarvis':'Install a model to continue'}</button><button type="button" className="ghost" onClick={onDone}>Skip for now</button></div>
 </div>;
}
