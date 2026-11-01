import {useEffect,useRef,useState} from 'react';
import {API} from './TaskPanel';
import {VoiceActivity} from './voiceActivity';
import Icon from './Icons';

type Status={ready:boolean;message:string;voices:string[];default_voice?:string;live_ready?:boolean};
type Transcript={text:string;uncertain?:boolean};
type Props={api:API;onText:(text:string)=>void;reply:string;replyKey?:string;draft?:string;turnKey?:string;thinking?:boolean;failure?:string;contextKey?:string|number;language?:string;onLanguage?:(language:string)=>void;onUtterance?:(text:string,signal:AbortSignal)=>Promise<void>;onInterrupt?:()=>void;showText?:boolean;onShowText?:(value:boolean)=>void;announce?:string;announceKey?:string};
type Speech={key:string;parts:string[];spoken:number;final:boolean;playing:boolean};
export const acceptedTranscript=(result:Transcript)=>/[\p{L}\p{N}]/u.test(result.text)&&!result.uncertain;
// Long sentences also break at commas (left piece ≥2 words, e.g. an opener like "जी सर,") so the first clause plays while Qwen keeps writing.
const clauses=(sentence:string)=>sentence.split(/\s+/).length<=8?[sentence]:sentence.split(/(?<=,)\s+/u).reduce<string[]>((out,piece)=>{if(out.length&&out[out.length-1].split(/\s+/).length<2)out[out.length-1]+=' '+piece;else out.push(piece);return out},[]);
export const speechParts=(text:string)=>text.slice(0,3000).split(/(?<=[.!?।])\s+/u).filter(p=>p.trim()).flatMap(clauses);
// The last draft part may still be mid-sentence; only finished sentences are spoken early.
export const draftSentences=(draft:string)=>speechParts(draft).slice(0,-1);
const WAKE=/^\s*(?:(?:hey|hi|ok|okay|हे|ओके)[\s,]+)?(?:jarvis|जार्विस|जारविस|जर्विस|जार्वीस|जारवीस|जावीस)(?![\p{L}\p{M}])[\s,.!?।:]*/iu;
const ENDING=/^(?:that'?s all|that is all|thank you|thanks|goodbye|bye|ok bye|bas|bas itna hi|बस|बस इतना ही|धन्यवाद|शुक्रिया)$/u;
// null: no wake word, so standby discards the phrase; '': wake word alone.
export const wakeText=(text:string)=>{const m=text.match(WAKE);return m?text.slice(m[0].length).trim():null};
export const endsConversation=(text:string)=>ENDING.test(text.toLowerCase().replace(/jarvis|जार्विस/giu,'').replace(/[^\p{L}\p{M}\s']/gu,' ').replace(/\s+/g,' ').trim());
// Voice-to-voice latency the user actually feels: end of speech to recognized text, and to Jarvis's first sound.
export const turnTiming=(m:{end?:number;text?:number;voice?:number})=>m.end&&m.text&&m.voice?`You stopped → text ${((m.text-m.end)/1000).toFixed(2)} s · → Jarvis speaking ${((m.voice-m.end)/1000).toFixed(2)} s`:'';
const words=(text:string)=>text.toLowerCase().replace(/jarvis|जार्विस/giu,'').replace(/[^\p{L}\p{M}\p{N}\s']/gu,' ').split(/\s+/).filter(Boolean);
// While Jarvis talks, only these interrupt him; anything else is kept and answered after he finishes.
const STOP=/^(?:stop|wait|hold on|enough|cancel|ruko|ruk jao|bas karo|chup|chup karo|रुको|रुक जाओ|बस करो|चुप)(?![\p{L}\p{M}])/u;
export const stopsSpeech=(text:string)=>STOP.test(words(text).join(' '));
// Speakers can leak Jarvis's own voice into the mic; a "user" phrase made of his current words is that echo.
export const isEcho=(text:string,said:string)=>{const heard=words(text),spoken=new Set(words(said));return heard.length>0&&heard.filter(w=>spoken.has(w)).length/heard.length>=.6};
export const extendsSpoken=(queued:string[],parts:string[])=>parts.length>=queued.length&&queued.every((p,i)=>parts[i]===p);
export type OrbMode='idle'|'listening'|'thinking'|'speaking'|'standby'|'muted';
export const orbMode=(state:string,muted:boolean):OrbMode=>muted?'muted':state.startsWith('Standby')?'standby':state==='Jarvis is speaking'?'speaking':['Understanding you','Jarvis is thinking','Preparing voice','Opening microphone'].includes(state)?'thinking':state.startsWith('Listening')||state==='Please repeat'?'listening':'idle';
type Action={kind:'send';text:string;woke:boolean}|{kind:'ignore'|'greet'|'end'|'repeat'};
// verified: the live listener already heard "hey jarvis", so a misheard wake word in the text is still a request.
export function transcriptAction(result:Transcript,awake:boolean,verified:boolean):Action{
 const accepted=acceptedTranscript(result);let text=result.text,woke=false;
 if(!awake){
  if(!accepted)return {kind:verified?'greet':'ignore'};
  const rest=wakeText(text)??(verified?text.trim():null);
  if(rest===null)return {kind:'ignore'};
  if(!rest)return {kind:'greet'};
  text=rest;woke=true;
 }
 if(accepted&&endsConversation(text))return {kind:'end'};
 if(!accepted)return {kind:'repeat'};
 return {kind:'send',text,woke};
}
// Mic audio -> 16 kHz int16 frames of 512 samples, posted to the page for the live WebSocket.
const PCM_WORKLET="class P extends AudioWorkletProcessor{constructor(){super();this.b=new Int16Array(512);this.n=0}process(i){const c=i[0][0];if(c){for(let k=0;k<c.length;k++){const v=Math.max(-1,Math.min(1,c[k]));this.b[this.n++]=v<0?v*32768:v*32767;if(this.n===512){this.port.postMessage(this.b.buffer,[this.b.buffer]);this.b=new Int16Array(512);this.n=0}}}return true}}registerProcessor('pcm16',P)";
export default function VoiceControls({api,onText,reply,replyKey='',draft='',turnKey='',thinking=false,failure='',contextKey='',language:preferredLanguage,onLanguage,onUtterance,onInterrupt,showText=false,onShowText,announce='',announceKey=''}:Props){
 const [status,setStatus]=useState<Status|null>(null),[state,setState]=useState('Ready to talk'),[localLanguage,setLanguage]=useState('en'),[voice,setVoice]=useState(''),[error,setError]=useState(''),[session,setSession]=useState(false);
 const mounted=useRef(true),epoch=useRef(0),active=useRef(false),seenReply=useRef(replyKey),seenAnnounce=useRef(announceKey),failures=useRef(0);
 const recorder=useRef<MediaRecorder|null>(null),stream=useRef<MediaStream|null>(null),audio=useRef<HTMLAudioElement|null>(null),context=useRef<AudioContext|null>(null),timer=useRef<ReturnType<typeof setInterval>|null>(null),resumeTimer=useRef<ReturnType<typeof setTimeout>|null>(null),url=useRef('');
 const request=useRef<AbortController|null>(null),submission=useRef<AbortController|null>(null);
 const [wakeMode,setWakeMode]=useState(()=>{try{return localStorage.getItem('jarvis-wake-word')==='1'}catch{return false}});
 // awake: in a conversation; closing: end the session after the goodbye is spoken; watcher: barge-in mic.
 const wake=useRef(wakeMode),awake=useRef(true),closing=useRef(false),watcher=useRef<(()=>void)|null>(null);wake.current=wakeMode;
 const marks=useRef<{end?:number;text?:number;voice?:number}>({}),[timing,setTiming]=useState('');
 // live: one mic + WebSocket for the whole conversation; the server decides when each turn ends.
 const live=useRef<{ws:WebSocket;ctx:AudioContext;media:MediaStream;node:AudioWorkletNode}|null>(null),idle=useRef<ReturnType<typeof setTimeout>|null>(null);
 const [bargeIn,setBargeIn]=useState(()=>{try{return localStorage.getItem('jarvis-barge-in')!=='0'}catch{return true}}),barge=useRef(bargeIn);barge.current=bargeIn;
 // Voice mode presentation: minimized pill, settings panel, mute, captions and the orb's live level meters.
 const [mini,setMini]=useState(false),[panelOpen,setPanelOpen]=useState(false),[muted,setMuted]=useState(false),[heard,setHeard]=useState(''),[saying,setSaying]=useState('');
 const mutedRef=useRef(false);mutedRef.current=muted;
 const orbRef=useRef<HTMLDivElement>(null),micMeter=useRef<AnalyserNode|null>(null),outCtx=useRef<AudioContext|null>(null),outMeter=useRef<AnalyserNode|null>(null);
 const finishPlayback=useRef<(()=>void)|null>(null),queue=useRef<Speech>({key:'',parts:[],spoken:0,final:false,playing:false});
 const latest=useRef({onText,onUtterance,onInterrupt,language:preferredLanguage||localLanguage,voice,thinking});latest.current={onText,onUtterance,onInterrupt,language:preferredLanguage||localLanguage,voice,thinking};
 // What you say while Jarvis thinks or speaks is kept here and sent as your next turn once he finishes.
 const pending=useRef<string[]>([]);
 const busy=()=>queue.current.playing||!!audio.current||latest.current.thinking;
 function flushPending(){if(!pending.current.length||!active.current)return false;const text=pending.current.join(' ');pending.current=[];void handleTranscript({text},true).catch(e=>{if(mounted.current&&active.current)setError(String(e))});return true}
 function release(){if(timer.current)clearInterval(timer.current);timer.current=null;stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;if(recorder.current?.state==='recording')recorder.current.stop();recorder.current=null;void context.current?.close();context.current=null}
 function forget(key=''){queue.current={key,parts:[],spoken:0,final:false,playing:false}}
 function silence(){audio.current?.pause();audio.current=null;finishPlayback.current?.();finishPlayback.current=null;if(url.current){URL.revokeObjectURL(url.current);url.current=''}}
 function unwatch(){watcher.current?.();watcher.current=null}
 // Talking over Jarvis for ~300 ms stops playback and starts your turn; echo cancellation keeps its own voice out.
 async function watch(){
  if(watcher.current||!navigator.mediaDevices?.getUserMedia)return;
  const turn=epoch.current;let stopped=false;watcher.current=()=>{stopped=true};
  try{
   const media=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});
   const ctx=new AudioContext(),analyser=ctx.createAnalyser();analyser.fftSize=1024;ctx.createMediaStreamSource(media).connect(analyser);const samples=new Float32Array(analyser.fftSize);let loud=0;
   const timer=setInterval(()=>{analyser.getFloatTimeDomainData(samples);const rms=Math.sqrt(samples.reduce((s,v)=>s+v*v,0)/samples.length);loud=rms>.04?loud+1:0;if(loud>=6&&turn===epoch.current&&active.current){unwatch();void listen(true)}},50);
   const close=()=>{clearInterval(timer);media.getTracks().forEach(t=>t.stop());void ctx.close()};
   if(stopped||turn!==epoch.current){close();return}
   watcher.current=close;
  }catch{watcher.current=null}
 }
 function end(){pending.current=[];stopLive();micMeter.current=null;setMini(false);setPanelOpen(false);setMuted(false);setSaying('');if(idle.current)clearTimeout(idle.current);active.current=false;closing.current=false;epoch.current++;request.current?.abort();submission.current?.abort();if(resumeTimer.current)clearTimeout(resumeTimer.current);unwatch();release();silence();forget();if(mounted.current){setSession(false);setState('Ready to talk')}}
 const listeningLabel=()=>awake.current||!wake.current?'Listening — go ahead':'Standby — say “Hey Jarvis”';
 function sendMode(){const l=live.current;if(l?.ws.readyState===WebSocket.OPEN)l.ws.send(JSON.stringify({standby:wake.current&&!awake.current,language:latest.current.language}))}
 function stopLive(){const l=live.current;live.current=null;if(!l)return;l.ws.onclose=null;l.ws.close();l.node.port.onmessage=null;l.node.disconnect();l.media.getTracks().forEach(t=>t.stop());void l.ctx.close()}
 // In wake-word mode, 25 s without speech returns a conversation to standby.
 function idleLater(){if(idle.current)clearTimeout(idle.current);if(!wake.current)return;idle.current=setTimeout(()=>{if(live.current&&awake.current&&!queue.current.playing){awake.current=false;sendMode();setState(listeningLabel())}},25000)}
 async function startLive(){
  setState('Opening microphone');
  try{
   const media=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1},video:false});
   if(!mounted.current||!active.current){media.getTracks().forEach(t=>t.stop());return}
   const ctx=new AudioContext({sampleRate:16000}),module=URL.createObjectURL(new Blob([PCM_WORKLET],{type:'text/javascript'}));
   await ctx.audioWorklet.addModule(module);URL.revokeObjectURL(module);
   const node=new AudioWorkletNode(ctx,'pcm16'),source=ctx.createMediaStreamSource(media),meter=ctx.createAnalyser();meter.fftSize=512;source.connect(node);source.connect(meter);micMeter.current=meter;
   // The socket is authorised only by the session cookie, and sessions live in server memory: renew it so a
   // restarted server does not refuse the voice connection (403) while every token-header request still works.
   await api('/session','POST',{token:sessionStorage.getItem('ninja-token')||''}).catch(()=>{});
   if(!mounted.current||!active.current){media.getTracks().forEach(t=>t.stop());void ctx.close();return}
   const ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/api/assistant/voice/live');ws.binaryType='arraybuffer';
   live.current={ws,ctx,media,node};
   // Without barge-in the mic is muted while Jarvis talks, so speakers cannot feed his own voice back.
   node.port.onmessage=e=>{if(ws.readyState===WebSocket.OPEN&&!mutedRef.current&&(barge.current||!queue.current.playing))ws.send(e.data)};
   ws.onopen=()=>{sendMode();setState(listeningLabel());idleLater()};
   ws.onmessage=e=>{void onLive(JSON.parse(e.data))};
   ws.onclose=()=>{if(active.current&&live.current?.ws===ws){end();setError('Live listening stopped. Start the conversation again.')}};
  }catch(e){end();setError('Microphone unavailable: '+String(e))}
 }
 async function onLive(m:{type:string;message?:string;text?:string;uncertain?:boolean;timing?:{total_ms?:number}}){
  if(!active.current)return;
  if(m.type==='speech'){idleLater();if(!busy())setState(listeningLabel())}
  else if(m.type==='error')setError(m.message||'Live listening error');
  else if(m.type==='transcript'&&typeof m.text==='string'){
   const now=performance.now();marks.current={end:now-(m.timing?.total_ms||0)};setState('Understanding you');
   try{await handleTranscript({text:m.text,uncertain:m.uncertain},true)}catch(e){if(mounted.current&&active.current)setError(String(e))}
  }
 }
 async function handleTranscript(result:Transcript,verified:boolean){
  if(busy()&&(awake.current||!wake.current)){
   if(stopsSpeech(result.text)){pending.current=[];interrupt();return}
   if(acceptedTranscript(result)&&!isEcho(result.text,queue.current.parts.join(' '))){pending.current.push(result.text);setHeard(result.text)}
   return;
  }
  const action=transcriptAction(result,awake.current||!wake.current,verified);
  if(action.kind==='ignore'){resume();return}
  if(action.kind==='greet'){setHeard(result.text);awake.current=true;sendMode();speak('Yes, sir?');return}
  if(action.kind==='end'){if(wake.current){awake.current=false;sendMode()}else closing.current=true;speak('Very well, sir.');return}
  if(action.kind==='repeat'){setError('I missed some of that. Please say it again, a little closer to the microphone.');setState('Please repeat');speak(latest.current.language==='en'?'Could you say that again?':'फिर से बोलिए, साफ़ सुनाई नहीं दिया।');return}
  if(action.kind!=='send')return;
  if(action.woke){awake.current=true;sendMode()}
  failures.current=0;setError('');marks.current.text=performance.now();setHeard(action.text);latest.current.onText(action.text);
  if(active.current&&latest.current.onUtterance){const sending=new AbortController();submission.current=sending;setState('Jarvis is thinking');await latest.current.onUtterance(action.text,sending.signal)}
  else setState('Transcript ready');
 }
 function resume(delay=350){if(live.current){setState(listeningLabel());idleLater();return}const turn=epoch.current;if(resumeTimer.current)clearTimeout(resumeTimer.current);resumeTimer.current=setTimeout(()=>{if(mounted.current&&active.current&&turn===epoch.current)void listen(true)},delay)}
 useEffect(()=>{mounted.current=true;api<Status>('/assistant/voice').then(s=>{if(mounted.current){setStatus(s);let saved='';try{saved=localStorage.getItem('jarvis-neural-voice')||''}catch{}setVoice(s.voices.includes(saved)?saved:s.default_voice||s.voices[0]||'')}}).catch(e=>{if(mounted.current)setError(String(e))});return()=>{mounted.current=false;end()}},[]);
 useEffect(()=>{end();seenReply.current=replyKey},[contextKey]);
 useEffect(()=>{if(active.current&&failure){end();setError(failure)}},[failure]);
 async function listen(automatic:boolean){
  if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==='undefined'){end();setError('Open Ninja on localhost in a browser with microphone access.');return}
  const turn=++epoch.current;request.current?.abort();unwatch();silence();forget();release();latest.current.onInterrupt?.();setState('Opening microphone');
  try{
   const media=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false});
   if(!mounted.current||turn!==epoch.current){media.getTracks().forEach(t=>t.stop());return}
   stream.current=media;const mime=['audio/webm;codecs=opus','audio/webm','audio/ogg'].find(t=>MediaRecorder.isTypeSupported(t));const recording=new MediaRecorder(media,mime?{mimeType:mime}:undefined);recorder.current=recording;const chunks:Blob[]=[];let send=true;
   const ctx=new AudioContext();context.current=ctx;await ctx.resume();if(turn!==epoch.current)return;
   const analyser=ctx.createAnalyser();analyser.fftSize=1024;ctx.createMediaStreamSource(media).connect(analyser);micMeter.current=analyser;const samples=new Float32Array(analyser.fftSize),vad=new VoiceActivity();const started=performance.now();
   recording.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
   recording.onstop=async()=>{
    if(!mounted.current||turn!==epoch.current)return;
    // 25 s without speech ends a wake-word conversation and returns to standby.
    if(!send){if(active.current){if(wake.current)awake.current=false;resume()}else setState('No speech heard');return}
    setState('Understanding you');const controller=new AbortController();request.current=controller;
    try{
     const body=new FormData();const ext=recording.mimeType.includes('ogg')?'ogg':recording.mimeType.includes('mp4')?'mp4':'webm';body.append('file',new Blob(chunks,{type:recording.mimeType}),'voice.'+ext);
     const response=await fetch('/api/assistant/voice/transcribe?language=auto',{method:'POST',signal:controller.signal,headers:{'X-Ninja-Token':sessionStorage.getItem('ninja-token')||''},body});const result=await response.json();if(!response.ok)throw new Error(result.detail||'I could not hear that clearly. Please repeat.');if(!mounted.current||turn!==epoch.current)return;
     // Standby phrases without the wake word are discarded, never shown or sent.
     if(active.current)await handleTranscript(result,false);
     else{setError('');latest.current.onText(result.text);setState('Transcript ready')}
    }catch(e){if(mounted.current&&turn===epoch.current&&!controller.signal.aborted){setError(String(e));if(active.current&&++failures.current<3){setState('Please repeat');resume(1000)}else end()}}
   };
   recording.start();setState(awake.current?'Listening — go ahead':'Standby — say “Jarvis”');
   timer.current=setInterval(()=>{if(turn!==epoch.current)return;analyser.getFloatTimeDomainData(samples);const rms=Math.sqrt(samples.reduce((s,v)=>s+v*v,0)/samples.length);const result=vad.sample(rms,performance.now());if(automatic&&result!=='listen'){send=result==='send';if(send)marks.current={end:performance.now()};release()}else if(!automatic&&performance.now()-started>=25000)release()},50);
  }catch(e){if(mounted.current&&turn===epoch.current){end();setError('Microphone unavailable: '+String(e))}}
 }
 // Sentences can be appended while earlier ones play; the final reply resumes listening.
 async function pump(){
  const q=queue.current,turn=epoch.current;if(q.playing)return;q.playing=true;
  const controller=new AbortController();request.current=controller;const current=()=>mounted.current&&turn===epoch.current&&queue.current===q;
  async function fetchPart(part:string):Promise<{blob?:Blob;error?:unknown}>{
   try{const response=await fetch('/api/assistant/voice/speak',{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json','X-Ninja-Token':sessionStorage.getItem('ninja-token')||''},body:JSON.stringify({text:part,voice:latest.current.voice})});
    if(!response.ok){const result=await response.json();throw new Error(result.detail||'Local voice unavailable. Try again in voice settings.')}
    return {blob:await response.blob()};
   }catch(error){return {error}}
  }
  try{
   if(q.spoken<q.parts.length&&!audio.current)setState('Preparing voice');
   let pending=q.spoken<q.parts.length?fetchPart(q.parts[q.spoken]):null;
   while(pending){
    const result=await pending;if(!current())return;if(!result.blob)throw result.error;
    q.spoken++;
    // Prepare the next sentence while this one plays, instead of delaying all audio.
    pending=q.spoken<q.parts.length?fetchPart(q.parts[q.spoken]):null;
    silence();url.current=URL.createObjectURL(result.blob);const player=new Audio(url.current);audio.current=player;meterPlayback(player);setSaying(q.parts[q.spoken-1]||'');
    await new Promise<void>((resolve,reject)=>{finishPlayback.current=resolve;player.onended=()=>resolve();player.onerror=()=>reject(new Error('Audio playback failed. Check your output device.'));player.play().then(()=>{if(current()){setState('Jarvis is speaking');if(marks.current.text&&!marks.current.voice){marks.current.voice=performance.now();setTiming(turnTiming(marks.current))}if(active.current&&!live.current)void watch()}}).catch(reject)});
    if(!current())return;
    if(!pending&&q.spoken<q.parts.length)pending=fetchPart(q.parts[q.spoken]);
   }
   q.playing=false;silence();
   if(q.final){unwatch();if(closing.current){end();return}setState('Ready to talk');if(active.current&&!flushPending())resume()}else setState('Jarvis is thinking');
  }catch(e){q.playing=false;if(current()&&!controller.signal.aborted){silence();forget();setError('Could not speak: '+String(e));if(active.current&&!flushPending())resume()}}
 }
 function enqueue(key:string,parts:string[],final:boolean){
  let q=queue.current;
  if(q.key!==key||!extendsSpoken(q.parts,parts)){
   // A draft that diverged waits for the final reply; a diverged final reply replaces what was said.
   if(q.key===key&&!final)return;
   if(q.playing)request.current?.abort();silence();forget(key);q=queue.current;
  }else if(!final&&parts.length===q.parts.length)return;
  q.parts=parts;q.final=final;void pump();
 }
 function speak(text=reply){release();silence();forget();enqueue('say:'+Date.now(),speechParts(text),true)}
 useEffect(()=>{
  if(!active.current){seenReply.current=replyKey;return}
  if(!voice)return;
  if(!thinking&&reply&&replyKey&&replyKey!==seenReply.current){seenReply.current=replyKey;enqueue(replyKey,speechParts(reply),true)}
  else if(thinking&&draft&&turnKey)enqueue(turnKey,draftSentences(draft),false);
 },[replyKey,reply,draft,turnKey,thinking,voice]);
 // A due reminder is spoken once Jarvis is between turns; with no voice session the Windows notification covers it.
 useEffect(()=>{
  if(!active.current){seenAnnounce.current=announceKey;return}
  if(voice&&announce&&announceKey&&announceKey!==seenAnnounce.current&&!thinking&&!queue.current.playing){seenAnnounce.current=announceKey;release();enqueue(announceKey,speechParts(announce),true)}
 },[announceKey,announce,thinking,voice,state]);
 // Jarvis's own voice is metered through a context created on the Talk click, so autoplay rules never silence it.
 function meterPlayback(player:HTMLAudioElement){const ctx=outCtx.current;if(!ctx||ctx.state!=='running'||!outMeter.current)return;try{ctx.createMediaElementSource(player).connect(outMeter.current)}catch{}}
 function start(){
  if(!outCtx.current){try{outCtx.current=new AudioContext();outMeter.current=outCtx.current.createAnalyser();outMeter.current.fftSize=512;outMeter.current.connect(outCtx.current.destination)}catch{outCtx.current=null}}
  void outCtx.current?.resume();void api('/assistant/voice/warm','POST',{}).catch(()=>{});
  active.current=true;awake.current=!wake.current;closing.current=false;failures.current=0;seenReply.current=replyKey;setSession(true);setMini(false);setHeard('');setError('');
  void (status?.live_ready?startLive():listen(true));
 }
 function interrupt(){if(live.current){request.current?.abort();silence();forget();setState(listeningLabel())}else{silence();void listen(true)}}
 // The orb breathes with your voice while listening and with Jarvis's voice while he speaks.
 useEffect(()=>{
  if(!session)return;
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches,data=new Float32Array(512);let frame=0,smooth=0;
  const tick=()=>{
   const speaking=queue.current.playing&&!!audio.current,meter=speaking?outMeter.current:micMeter.current;let level=0;
   if(meter&&!reduce&&!(mutedRef.current&&!speaking)){meter.getFloatTimeDomainData(data);let sum=0;for(let i=0;i<data.length;i++)sum+=data[i]*data[i];level=Math.min(1,Math.sqrt(sum/data.length)*(speaking?5:9))}
   smooth=smooth*.8+level*.2;orbRef.current?.style.setProperty('--level',smooth.toFixed(3));frame=requestAnimationFrame(tick);
  };
  frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame);
 },[session,mini]);
 useEffect(()=>{if(!active.current)return;if(!wakeMode)awake.current=true;sendMode();setState(current=>current.startsWith('Listening')||current.startsWith('Standby')?listeningLabel():current)},[wakeMode]);
 useEffect(()=>{if(active.current)sendMode()},[preferredLanguage,localLanguage]);
 useEffect(()=>{if(!session||mini)return;const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setMini(true)};addEventListener('keydown',key);return()=>removeEventListener('keydown',key)},[session,mini]);
 const mode=orbMode(state,muted);
 const orb=(small=false)=><div className={'orb'+(small?' small':'')} ref={orbRef} aria-hidden="true"><i/><i/><b/></div>;
 return <>
  <button type="button" className={'micButton'+(session?' on':'')} disabled={!status?.ready} aria-label={session?'Open voice mode':'Talk to Jarvis'} title={session?'Open voice mode':status?.ready?(wakeMode?'Start standby: say “Hey Jarvis”':'Talk to Jarvis'):status?.message||'Checking local voice…'} onClick={()=>{if(active.current)setMini(false);else start()}}><Icon name="mic" size={20}/></button>
  {!session&&error&&<p role="alert" className="voiceInlineError">{error}</p>}
  {session&&<div className={'voiceMode '+mode+(mini?' mini':'')} role={mini?undefined:'dialog'} aria-modal={mini?undefined:true} aria-label="Voice conversation with Jarvis">
   {mini?<button type="button" className="miniOrb" onClick={()=>setMini(false)} aria-label={'Jarvis voice: '+state+'. Open voice mode'}>{orb(true)}<span>{muted?'Muted':state}</span></button>:<>
    <div className="voiceTop"><button type="button" className="ghost" aria-expanded={panelOpen} onClick={()=>setPanelOpen(!panelOpen)}><Icon name="settings" size={18}/>Voice settings</button><button type="button" className="ghost" onClick={()=>setMini(true)}>Minimize</button></div>
    <div className="voiceStage">
     {orb()}
     <p className="voiceState" role="status" aria-live="polite">{muted?'Microphone muted':state}</p>
     <div className="captions">{showText&&heard&&<p className="heard">{heard}</p>}{showText&&saying&&<p className="saying">{saying}</p>}</div>
     {error&&<p role="alert" className="voiceError">{error}</p>}
    </div>
    <div className="voiceActions">
     {status?.live_ready&&<button type="button" aria-pressed={muted} onClick={()=>setMuted(!muted)}><Icon name={muted?'mute':'mic'} size={20}/>{muted?'Unmute':'Mute'}</button>}
     <button type="button" disabled={state!=='Jarvis is speaking'} onClick={interrupt}><Icon name="hand" size={20}/>Interrupt</button>
     <button type="button" className="danger" onClick={end}><Icon name="close" size={20}/>End</button>
    </div>
    {timing&&<small className="voiceTiming">Last turn: {timing}</small>}
    {panelOpen&&<div className="voiceSettings" role="group" aria-label="Voice settings">
     <label>Reply language<select value={latest.current.language} onChange={e=>{setLanguage(e.target.value);onLanguage?.(e.target.value)}}><option value="en">English</option><option value="hi">Hindi</option><option value="hinglish">Hinglish (Hindi + English)</option><option value="auto">Other languages / automatic</option></select></label>
     <label className="libraryCheck"><input type="checkbox" checked={showText} onChange={e=>onShowText?.(e.target.checked)}/>Show text while Jarvis listens and talks. Off: he just speaks; the full conversation stays in the chat.</label>
     <label>Voice<select value={voice} onChange={e=>{setVoice(e.target.value);try{localStorage.setItem('jarvis-neural-voice',e.target.value)}catch{}}}>{status?.voices.map(v=><option key={v}>{v}</option>)}</select></label>
     <label className="libraryCheck"><input type="checkbox" checked={wakeMode} onChange={e=>{setWakeMode(e.target.checked);try{localStorage.setItem('jarvis-wake-word',e.target.checked?'1':'0')}catch{}}}/>Wake word: wait in standby until you say “Hey Jarvis”. Other speech is discarded locally.</label>
     <label className="libraryCheck"><input type="checkbox" checked={bargeIn} onChange={e=>{setBargeIn(e.target.checked);try{localStorage.setItem('jarvis-barge-in',e.target.checked?'1':'0')}catch{}}}/>Interrupt Jarvis by talking. Turn off if your speakers make him interrupt himself.</label>
     {reply&&<button type="button" disabled={!voice} onClick={()=>speak()}>Read the last reply again</button>}
     <small>{status?.message} Say “that’s all” to finish{wakeMode?' or stay quiet 25 s to return to standby':''}. Esc minimizes.</small>
    </div>}
   </>}
  </div>}
 </>;
}
