
import {useEffect,useRef,useState} from 'react';
import {API} from './TaskPanel';
import ChatMarkdown from './ChatMarkdown';
import VoiceControls from './VoiceControls';
type Message={role:'user'|'assistant';content:string};
export default function PrivateConversation({api,close}:{api:API;close:()=>void}){
 const [text,setText]=useState(''),[messages,setMessages]=useState<Message[]>([]),[pending,setPending]=useState(false),[error,setError]=useState('');
 const [voiceReset,setVoiceReset]=useState(0);
 const generation=useRef(0);useEffect(()=>()=>{generation.current++},[]);
 async function send(value=text,signal?:AbortSignal){
  if(signal?.aborted)return;
  const current=++generation.current,next=[...messages,{role:'user' as const,content:value}];setMessages(next);setText('');setError('');setPending(true);
  try{const answer=await api<{text:string}>('/assistant/private','POST',{messages:next.slice(-11)});if(generation.current===current&&!signal?.aborted)setMessages([...next,{role:'assistant',content:answer.text}]);}
  catch(e){if(generation.current===current)setError(String(e))}
  finally{if(generation.current===current)setPending(false)}
 }
 return <section className="card jarvisConsole" aria-label="Private Jarvis conversation"><div className="sectionTitle"><h2>Private conversation</h2><button onClick={close}>Leave and clear</button></div><p>Local Qwen replies stay in this window. No saved history, memory retrieval, task tools or publishing. Refresh or leave to clear the conversation.</p>
 {messages.map((m,i)=><div key={i} className="assistantReply"><strong>{m.role==='user'?'You':'Jarvis'}</strong><ChatMarkdown text={m.content}/></div>)}
 <label>Private question<textarea value={text} maxLength={6000} onChange={e=>setText(e.target.value)}/></label><VoiceControls key={voiceReset} api={api} onText={setText} reply={messages.filter(m=>m.role==='assistant').at(-1)?.content||''} replyKey={String(messages.length)} thinking={pending} failure={error} onUtterance={(value,signal)=>send(value,signal)}/><small>Voice uses temporary local audio deleted after transcription. OS memory and third-party Ollama logging settings are separate from Ninja's history.</small>
 <div className="inline"><button className="primary" disabled={pending||!text.trim()} onClick={()=>void send()}>Ask privately</button>{pending&&<button onClick={()=>{generation.current++;setPending(false);setError('Stopped waiting. The local model may finish its current reply; no task actions are running.')}}>Stop waiting</button>}<button onClick={()=>{generation.current++;setPending(false);setVoiceReset(v=>v+1);setText('');setMessages([]);setError('')}}>Clear conversation</button></div><p role="status">{pending?'Waiting for local Qwen':error}</p></section>;
}

