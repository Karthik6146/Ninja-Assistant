import {useEffect,useState} from 'react';
import {ClientProps} from './TaskPanel';
export type Channel={id:string;title:string;avatar?:string;connection:string;connected:boolean;health:string;defaults?:Record<string,unknown>};
// YouTube Setup tab, below Google sign-in: extra channels for Studio profiles, media folders and local video services.
export default function StudioConnections({api,action,busy}:ClientProps){
 const [channels,setChannels]=useState<Channel[]>([]),[url,setURL]=useState(''),[path,setPath]=useState(''),[roots,setRoots]=useState<string[]>([]),[configured,setConfigured]=useState(false),[services,setServices]=useState<Record<string,{ready?:boolean;message?:string}>>({});
 async function refresh(){const [c,r,y]=await Promise.all([api<Channel[]>('/studio/channels'),api<string[]>('/studio/folders'),api<{connection:{configured:boolean}}>('/youtube')]);setChannels(c);setRoots(r);setConfigured(y.connection.configured)}
 useEffect(()=>{action(refresh)},[]);
 return <>
 <section className="ytPanel"><div className="ytPanelHead"><h3>Channels for Studio profiles</h3><button onClick={()=>action(refresh)}>Refresh</button></div><p>Each channel is verified by Google and keeps its own queue. Switching views never moves a queued upload to another channel.</p>
  {channels.map(c=><div className="setRow" key={c.id}><i className={'setDot'+(c.connected?' ok':'')} aria-hidden="true"/><div><strong>{c.title}</strong><small>{c.id} · {c.health}</small></div><button disabled={busy||!c.connected} onClick={()=>action(async()=>{await api('/studio/disconnect','POST',{connection:c.connection});await refresh()})}>Disconnect</button></div>)}
  {!channels.length&&<p className="profileHint">No channels yet. Local editing and test runs still work.</p>}
  <div className="inline"><button disabled={busy||!configured} onClick={()=>action(async()=>setURL((await api<{url:string}>('/studio/connect','POST',{manage:true,analytics:false})).url))}>Add a channel</button>{url&&<a className="button primary" href={url} target="_blank" rel="noreferrer">Continue to Google ↗</a>}</div>
  {!configured&&<small className="ytNote">Import the OAuth client JSON above first.</small>}{url&&<small className="ytNote">Pick the channel on Google's page, then come back and press Refresh.</small>}
 </section>
 <section className="ytPanel"><h3>Media folders</h3><p>Folders on this PC that Studio may read videos from.</p>
  {roots.map(r=><div className="setRow" key={r}><i className="setDot ok" aria-hidden="true"/><div><strong>{r}</strong></div></div>)}
  <form className="setAdd" onSubmit={e=>{e.preventDefault();if(path.trim())action(async()=>{setRoots(await api('/studio/folders','POST',{path}));setPath('')})}}><input aria-label="Folder path" value={path} onChange={e=>setPath(e.target.value)} placeholder="D:\Videos\Ready"/><button disabled={busy||!path.trim()}>Add folder</button></form>
 </section>
 <section className="ytPanel"><div className="ytPanelHead"><h3>Local video services</h3><button disabled={busy} onClick={()=>action(async()=>setServices(await api('/video/integrations')))}>Check</button></div>
  {Object.entries(services).map(([name,s])=><div className="setRow" key={name}><i className={'setDot'+(s.ready?' ok':'')} aria-hidden="true"/><div><strong>{name}</strong><small>{s.ready?'Ready':s.message||'Not running'}</small></div></div>)}
  {!Object.keys(services).length&&<p>Press Check to see whether the editor and ComfyUI are running.</p>}
  <details><summary>How to start them</summary><p>Run from the Ninja project folder and keep the window open:</p><pre>powershell -ExecutionPolicy Bypass -File scripts/start-video-service.ps1 -Service Editor{'\n'}powershell -ExecutionPolicy Bypass -File scripts/start-video-service.ps1 -Service ComfyUI</pre><p>Captions use ClipX (see Settings). Windows narration voices appear in the idea wizard.</p></details>
 </section></>;
}
