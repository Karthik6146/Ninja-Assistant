import {useEffect,useRef,useState} from 'react';
import {ClientProps} from './TaskPanel';
import {useDraft} from './useDraft';
import ChatMarkdown from './ChatMarkdown';
import VoiceControls from './VoiceControls';
import PrivateConversation from './PrivateConversation';
import {Definition} from './StudioForm';
import Icon from './Icons';
import Drawer from './Drawer';
type ConversationTurn={role:'user'|'assistant';content:string;revision:number};
type ImageJob={job:string;state:string;step?:string;error?:string;outputs:{name:string;url:string}[]};
export type AssistantTask={id:string;job:string;text:string;revision:number;state:string;step?:string;error?:string;reply:string;preview?:string;conversation?:ConversationTurn[];timing?:Record<string,number>;scopes?:{kind:string;id:string}[];request?:{response_mode?:string;language?:string};images?:ImageJob[];steps:{id:string;name:string;state:string;result?:{verified?:boolean;error?:string;value?:unknown}}[];draft?:{summary:string;questions:string[];limitations:string[];check:{issues:string[]};definition:Definition};children?:{run:string;job:string;state:string;step?:string}[];pending?:{approval:string;summary:string;decision?:string}};
// Verification notices stay visible in the transcript but are not read aloud.
export const spokenReply=(reply:string)=>reply.replace(/^(?:No tool action was verified for this reply\.|Some tool calls failed;[^\n]*)\n\n/,'');
// Auto-scroll only while the reader is at the latest message, never while they read history.
export const nearBottom=(el:{scrollTop:number;scrollHeight:number;clientHeight:number})=>el.scrollHeight-el.scrollTop-el.clientHeight<80;
// isComposing guards Hindi/Devanagari IMEs, where Enter confirms a word rather than sending.
export const sendKey=(e:{key:string;shiftKey:boolean;isComposing:boolean})=>e.key==='Enter'&&!e.shiftKey&&!e.isComposing;
// Only real capabilities: no example asks for something Jarvis cannot do.
const SUGGESTIONS=['CMS kya hota hai? Simple example do.','Remind me tomorrow at 7 PM to check my upload queue','Check CPU and memory usage','Help me plan today’s YouTube work'];
export const greeting=(hour:number)=>hour<5?'Working late':hour<12?'Good morning':hour<17?'Good afternoon':'Good evening';
export const canChange=(state:string)=>['queued','running','failed','completed'].includes(state);
export const conversationTurns=(task:AssistantTask):ConversationTurn[]=>task.conversation?.length?task.conversation:[{role:'user',content:task.text,revision:0},...(task.reply?[{role:'assistant' as const,content:task.reply,revision:task.revision}]:[])];
export default function AssistantConsole({api,action,busy,onTask,onDraft}:ClientProps&{onTask:(id:string,open?:boolean)=>void;onDraft:(id:string)=>void}){
 const [history,setHistory]=useState(false),[privateMode,setPrivateMode]=useState(false),[fileConsent,setFileConsent]=useState(false),[contextEpoch,setContextEpoch]=useState(0),[sending,setSending]=useState(false);
 const [tasks,setTasks]=useState<AssistantTask[]>([]),[selected,setSelected]=useState(localStorage.getItem('jarvis-task')||''),[error,setError]=useState('');
 const [draft,setDraft]=useDraft('jarvis-console',{text:'',instruction:'',channel:'',file:'',response_mode:'companion',language:'en'});
 useEffect(()=>{if(!localStorage.getItem('jarvis-voice-v3')){setDraft(d=>({...d,response_mode:'companion',language:'en'}));localStorage.setItem('jarvis-voice-v3','1')}},[]);
 // Live reply text is off by default: Jarvis just talks, and the page does not re-render every streamed word.
 const [showText,setShowText]=useState(()=>{try{return localStorage.getItem('jarvis-show-text')==='1'}catch{return false}});
 const selection=useRef(selected),operation=useRef(0),sendLock=useRef(false),mounted=useRef(true);selection.current=selected;
 const [reminders,setReminders]=useState<{id:string;text:string;due:number;state:string}[]>([]);
 const dueReminder=reminders.find(r=>r.state==='due');
 useEffect(()=>{const poll=()=>api<{items:{id:string;text:string;due:number;state:string}[]}>('/assistant/reminders').then(r=>{if(mounted.current)setReminders(r.items)}).catch(()=>{});poll();const t=setInterval(poll,10000);return()=>clearInterval(t)},[]);
 const [channels,setChannels]=useState<{id:string;title:string}[]>([]);
 useEffect(()=>{api<{id:string;title:string}[]>('/studio/channels').then(c=>{if(mounted.current)setChannels(c)}).catch(()=>{})},[]);
 const task=tasks.find(t=>t.id===selected),active=!!task&&['queued','running'].includes(task.state);
 // While a turn runs the server pushes every change (drafts, steps, reply); the 1 s list refresh is the fallback.
 useEffect(()=>{if(!task||!active)return;const stream=new EventSource('/api/assistant/tasks/'+task.id+'/stream');stream.onmessage=e=>{const next=JSON.parse(e.data) as AssistantTask;if(mounted.current)setTasks(list=>list.map(t=>t.id===next.id?next:t));if(!['queued','running'].includes(next.state))stream.close()};stream.onerror=()=>stream.close();return()=>stream.close()},[task?.id,active]);
 const canSend=!busy&&!sending&&!(selected&&!task)&&!!draft.text.trim()&&!(!selected&&draft.file&&!fileConsent)&&!(task&&!canChange(task.state));
 const scroller=useRef<HTMLElement>(null),follow=useRef(true),[behind,setBehind]=useState(false);
 useEffect(()=>{follow.current=true;setBehind(false)},[selected]);
 useEffect(()=>{const el=scroller.current;if(!el)return;if(follow.current)el.scrollTo({top:el.scrollHeight,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});else setBehind(true)},[selected,task?.conversation?.length,task?.preview,active]);
 // A spoken "speak in English" switches the server-side language; keep the selector in step.
 const taskLanguage=task?.request?.language;
 useEffect(()=>{if(taskLanguage&&taskLanguage!==draft.language)setDraft(d=>({...d,language:taskLanguage}))},[taskLanguage]);
 const boundChannel=task?task.scopes?.find(s=>s.kind==='channel')?.id||'':draft.channel;
 async function refresh(){const next=await api<AssistantTask[]>('/assistant/tasks');if(mounted.current)setTasks(next)}
 useEffect(()=>{mounted.current=true;let alive=true,inflight=false;async function poll(){if(inflight)return;inflight=true;try{const next=await api<AssistantTask[]>('/assistant/tasks');if(alive){setTasks(next);setError('')}}catch(e){if(alive)setError(String(e))}finally{inflight=false}};poll();const timer=setInterval(poll,1000);return()=>{alive=false;mounted.current=false;operation.current++;clearInterval(timer)}},[]);
 useEffect(()=>{localStorage.setItem('jarvis-task',selected)},[selected]);
 function switchConversation(id:string){operation.current++;setContextEpoch(v=>v+1);setSelected(id);setFileConsent(false);setError('')}
 async function submit(text:string,signal?:AbortSignal,continuation=false){
  const value=text.trim();if(!value||signal?.aborted)return;
  if(selected&&!task)throw new Error('Conversation is loading or unavailable. Retry or choose New conversation.');
  if(sendLock.current)throw new Error('A turn is still being submitted. Wait or end the voice session.');
  if(!task&&draft.file&&!fileConsent)throw new Error('Review and allow the selected document before sending.');
  if(task&&!canChange(task.state))throw new Error('This conversation is stopped. Start a new conversation.');
  const current=operation.current,id=selected;sendLock.current=true;setSending(true);setError('');
  try{
   const next=task?await api<AssistantTask>('/assistant/tasks/'+task.id+'/instructions','POST',{text:value,expected_revision:task.revision,request_key:crypto.randomUUID(),response_mode:'companion',spoken:!!signal,language:draft.language||'en'}):await api<{task:string;job:string}>('/assistant/tasks','POST',{text:value,documents:draft.file&&fileConsent?[draft.file]:[],scopes:[{kind:'personal',id:'me'},...(draft.channel?[{kind:'channel',id:draft.channel}]:[])],request_key:crypto.randomUUID(),response_mode:'companion',spoken:!!signal,language:draft.language||'en'});
   if(signal?.aborted){const acceptedId='task' in next?next.task:next.id;await api('/assistant/tasks/'+acceptedId+'/cancel','POST',{});return}
   if(!mounted.current||current!==operation.current||selection.current!==id)return;
   if('task' in next)setSelected(next.task);
   setDraft(currentDraft=>({...currentDraft,...(continuation?{instruction:currentDraft.instruction===text?'':currentDraft.instruction}:{text:currentDraft.text===text?'':currentDraft.text}),...(!task?{file:''}:{})}));setFileConsent(false);onTask(next.job,false);await refresh();
  }catch(e){if(mounted.current&&current===operation.current)setError(String(e));throw e}
  finally{sendLock.current=false;if(mounted.current)setSending(false)}
 }
 const pending=task&&!active&&task.pending&&!task.pending.decision?task.pending:undefined;
 async function decide(allow:boolean){if(!task||!pending)return;const next=await api<AssistantTask>('/assistant/tasks/'+task.id+'/confirm','POST',{approval:pending.approval,allow});setTasks(list=>list.map(t=>t.id===next.id?next:t))}
 async function cancel(){if(!task)return;await api('/assistant/tasks/'+task.id+'/cancel','POST',{});await refresh()}
 if(privateMode)return <PrivateConversation api={api} close={()=>{setPrivateMode(false);setContextEpoch(v=>v+1)}}/>;
 const tools=task?task.steps.filter(s=>s.name!=='Qwen'):[],failed=tools.some(s=>s.result?.verified===false||!!s.result?.error)||!!task?.error;
 const showCard=!!task&&(active||tools.length>0||!!task.error||!!task.draft||!!task.children?.length);
 const startPrivate=()=>{operation.current++;setContextEpoch(v=>v+1);setHistory(false);setPrivateMode(true)};
 return <section className="jarvis" aria-label="Jarvis assistant">
 <div className="jarvisBar">
  <button type="button" className="ghost" onClick={()=>setHistory(true)}><Icon name="history" size={18}/>History</button>
  <h2 className="jarvisTitle" title={task?.text}>{task?task.text:'New conversation'}</h2>
  <button type="button" className="ghost" disabled={!selected} onClick={()=>switchConversation('')}><Icon name="plus" size={18}/>New</button>
 </div>
 {reminders.filter(r=>r.state==='due').map(r=><div role="status" className="reminder" key={r.id}><Icon name="today" size={18}/><span>{r.text} · {new Date(r.due*1000).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})} IST</span><button className="ghost" onClick={()=>action(async()=>{await api('/assistant/reminders/'+r.id+'/dismiss','POST',{});setReminders(reminders.filter(x=>x.id!==r.id))})}>Dismiss</button></div>)}
 <div className="jarvisColumn">
 {selected&&!task&&<p role="status">Conversation is loading or unavailable. <button onClick={()=>action(refresh)}>Retry</button> or start a new conversation.</p>}
 {!selected&&<div className="jarvisEmpty"><span className="emptyMark"><Icon name="jarvis" size={40}/></span><h2>{greeting(new Date().getHours())}, sir.</h2><p>Ask me anything, think out loud, or give me a task. Press the microphone to talk.</p><div className="suggestions">{SUGGESTIONS.map(text=><button type="button" key={text} onClick={()=>setDraft(current=>({...current,text}))}>{text}</button>)}</div></div>}
 {task&&<section ref={scroller} onScroll={e=>{follow.current=nearBottom(e.currentTarget);if(follow.current)setBehind(false)}} className="companionTranscript" aria-label="Conversation history">
  {conversationTurns(task).map((m,i)=><article className={'companionTurn '+m.role} key={task.id+':'+i}>{m.role==='assistant'&&<span className="turnAvatar" aria-hidden="true"><Icon name="jarvis" size={16}/></span>}<div className="bubble"><span className="srOnly">{m.role==='user'?'You: ':'Jarvis: '}</span><ChatMarkdown text={m.content}/></div></article>)}
  {active&&<article className="companionTurn assistant provisional"><span className="turnAvatar" aria-hidden="true"><Icon name="jarvis" size={16}/></span><div className="bubble">{task.preview&&showText?<><span className="srOnly">Jarvis is writing a live draft; actions appear only after verification: </span><ChatMarkdown text={task.preview}/><span className="caret" aria-hidden="true"/></>:<span className="typing" role="status" aria-label="Jarvis is thinking"><i/><i/><i/></span>}</div></article>}
  {behind&&<button type="button" className="jumpLatest" onClick={()=>{follow.current=true;setBehind(false);scroller.current?.scrollTo({top:scroller.current.scrollHeight})}}>Latest</button>}
 </section>}
 {showCard&&task&&<details className={'toolCard'+(failed?' failed':'')} open={failed||undefined}>
  <summary>{active?<span className="spinner" aria-hidden="true"/>:<Icon name={failed?'alert':'check'} size={16}/>}<span className="toolTitle">{active?(task.step||'Working'):failed?'An action needs attention':tools.length?'Ran '+tools.length+' action'+(tools.length>1?'s':''):'Details'}</span>{typeof task.timing?.model_seconds==='number'&&<small>{task.timing.model_seconds.toFixed(1)} s</small>}<Icon name="chevron" size={16}/></summary>
  <div className="toolBody">
  <div className="inline"><span className={'state '+task.state}>{task.state.replaceAll('_',' ')}</span><p role="status" aria-live="polite">{task.step||'Waiting for Jarvis'}</p>{active&&<button disabled={busy} onClick={()=>action(cancel)}>Stop task</button>}<button onClick={()=>onTask(task.job)}>Open in Activity</button></div>
  {!!task.timing&&<small>{Object.entries(task.timing).filter(([,value])=>typeof value==='number'&&Number.isFinite(value)).map(([name,value])=>name.replaceAll('_',' ')+': '+value.toFixed(2)+'s').join(' · ')}</small>}{task.error&&<p className="error" role="alert">{task.error}</p>}
  {!!task.children?.length&&<section><h3>Background work</h3>{task.children.map(c=><p key={c.run}>{c.step||'Workflow'} · {c.state} <button onClick={()=>onTask(c.job)}>Open workflow progress</button></p>)}<button disabled={busy} onClick={()=>action(cancel)}>Stop linked work</button><small>Stops pending local work and uploads. Already accepted YouTube schedules must be cancelled in YouTube.</small></section>}
  {task.draft&&<section className="assistantReply"><h3>Video draft</h3><p>{task.draft.summary}</p>{[...task.draft.questions,...task.draft.limitations,...task.draft.check.issues].map((text,i)=><p key={i}>{text}</p>)}<button disabled={busy} onClick={()=>action(async()=>{const saved=await api<{id:string}>('/assistant/tasks/'+task.id+'/draft','POST',{revision:task.revision});onDraft(saved.id)})}>Save and open in Video Studio</button><small>A new draft uses review policy. Existing activated workflows keep their publishing policy.</small></section>}
  {!!tools.length&&<ol className="activity">{tools.map(s=><li key={s.id}><strong>{s.name}</strong> · {s.state}{s.result?.error&&<p>{s.result.error}</p>}<details><summary>Result evidence</summary><pre>{JSON.stringify(s.result,null,2)}</pre></details></li>)}</ol>}
  {canChange(task.state)&&<details><summary>Change the next task step</summary><label>Workflow or task instruction<textarea maxLength={3000} value={draft.instruction} onChange={e=>setDraft({...draft,instruction:e.target.value})} placeholder="Change the next step or add information."/></label><button disabled={busy||sending||!draft.instruction.trim()} onClick={()=>action(()=>submit(draft.instruction,undefined,true))}>Update instructions</button><small>Updates apply to the next uncommitted step. Verified actions stay in history.</small></details>}
  </div>
 </details>}
 {pending&&task&&<div className="confirmCard" role="alertdialog" aria-labelledby="confirm-title"><Icon name="lock" size={20}/><div><strong id="confirm-title">Jarvis wants to {pending.summary}</strong><small>Email or web text was read in this conversation, or this capability is set to Ask first.</small></div><button type="button" className="primary" disabled={busy} onClick={()=>action(()=>decide(true))}>Allow once</button><button type="button" disabled={busy} onClick={()=>action(()=>decide(false))}>Deny</button></div>}
 {error&&<div className="error" role="alert">{error}<button onClick={()=>action(refresh)}>Retry</button></div>}
 <form className="composer" onSubmit={e=>{e.preventDefault();if(canSend)void action(()=>submit(draft.text))}}>
  <textarea rows={1} aria-label={task?'Your next message':'Your message'} maxLength={task?3000:6000} value={draft.text} onChange={e=>setDraft({...draft,text:e.target.value})} placeholder="Message Jarvis… e.g. CMS kya hota hai? or remind me at 7 PM" onKeyDown={e=>{if(sendKey({key:e.key,shiftKey:e.shiftKey,isComposing:e.nativeEvent.isComposing})){e.preventDefault();if(canSend)void action(()=>submit(draft.text))}}}/>
  <VoiceControls api={api} onText={text=>setDraft(current=>({...current,text}))} reply={task?.state==='completed'?spokenReply(task.reply):''} replyKey={task?.state==='completed'?task.id+':'+task.revision:''} draft={active?task?.preview||'':''} turnKey={task?task.id+':'+task.revision:''} failure={task?.state==='failed'?task.error||'The reply failed. Retry your message.':''} thinking={active||sending} contextKey={contextEpoch} language={draft.language||'en'} showText={showText} onShowText={value=>{setShowText(value);try{localStorage.setItem('jarvis-show-text',value?'1':'0')}catch{}}} onLanguage={language=>setDraft(current=>({...current,language}))} onUtterance={(text,signal)=>submit(text,signal)} announce={dueReminder?'Sir, a reminder: '+dueReminder.text:''} announceKey={dueReminder?'reminder:'+dueReminder.id:''}/>
  <button className="primary sendButton" disabled={!canSend} aria-label={active?'Update this turn':'Send message'} title={active?'Update this turn':'Send message'}>{sending?<span className="spinner" aria-hidden="true"/>:<Icon name="send" size={18}/>}</button>
 </form>
 <small className="composerHint">Enter to send · Shift+Enter for a new line{active?' · a new message updates the current turn':''} · sensitive actions ask first</small>
 </div>
 <Drawer open={history} onClose={()=>setHistory(false)} title="Conversations" side="left">
  <div className="historyActions"><button type="button" className="primary" onClick={()=>{switchConversation('');setHistory(false)}}><Icon name="plus" size={18}/>New conversation</button><button type="button" onClick={startPrivate}><Icon name="lock" size={18}/>Private</button></div>
  <ul className="historyList">{tasks.map(t=><li key={t.id}><button type="button" aria-current={t.id===selected||undefined} onClick={()=>{switchConversation(t.id);setHistory(false)}}><span>{t.text}</span><small>{t.state.replaceAll('_',' ')}{t.conversation?' · '+Math.ceil(t.conversation.length/2)+' turns':''}</small></button></li>)}{!tasks.length&&<li><p>No conversations yet.</p></li>}</ul>
  <label>Channel for a new conversation<select value={boundChannel} disabled={!!selected} onChange={e=>{setDraft({...draft,channel:e.target.value});setContextEpoch(v=>v+1)}}><option value="">Personal conversation / local tasks</option>{channels.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}</select></label>
  {selected?<small>An open conversation keeps its channel and shared documents. Start a new conversation to change them.</small>:<details><summary>Share a text document</summary><label>Approved text file path<input value={draft.file||''} onChange={e=>{setDraft(current=>({...current,file:e.target.value}));setFileConsent(false)}} placeholder="Path inside a NINJA_ROOTS folder"/></label><label className="libraryCheck"><input type="checkbox" checked={fileConsent} onChange={e=>setFileConsent(e.target.checked)}/>I reviewed this exact file; it contains no secrets or sensitive personal information and may be shared with local Qwen.</label><p>Other files stay unreadable to this request.</p></details>}
  {task&&!active&&<button type="button" className="danger" disabled={busy} onClick={()=>action(async()=>{await api('/assistant/tasks/'+task.id+'/forget','POST',{});switchConversation('');setHistory(false);await refresh()})}>Forget this conversation</button>}
 </Drawer>
 </section>;
}
