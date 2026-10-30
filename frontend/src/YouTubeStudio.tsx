import {useEffect, useState} from 'react';

type API = <T>(route:string, method?:string, body?:unknown)=>Promise<T>;
type Props = {api:API; action:(fn:()=>Promise<void>)=>Promise<void>; busy:boolean};
export type Operation = {id:string;kind:string;state:string;remote_id:string|null;offset:number;remote_status?:{publishAt?:string};params:Record<string,unknown>};
type Profile = {audience:string;language:string;pillars:string;tone:string};
type Overview = {connection:{configured:boolean;connected:boolean;channel:{id:string;title:string}|null;permissions:string[]};profile:Profile;operations:Operation[]};
type Package = {id:string;name:string;scenes:{id:string;script:string}[]};

export default function YouTubeStudio({api,action,busy}:Props) {
  const [data,setData]=useState<Overview|null>(null), [packages,setPackages]=useState<Package[]>([]);
  const [profile,setProfile]=useState<Profile>({audience:'',language:'Hinglish',pillars:'',tone:'clear and practical'});
  const [manage,setManage]=useState(true), [analytics,setAnalytics]=useState(false), [link,setLink]=useState('');
  const [selected,setSelected]=useState(''), [brief,setBrief]=useState(''), [evidence,setEvidence]=useState(''), [scene,setScene]=useState('');
  const [kids,setKids]=useState(''), [synthetic,setSynthetic]=useState(''), [notice,setNotice]=useState('');
  async function refresh(initial=false) {
    const next=await api<Overview>('/youtube');setData(next);
    if(initial)setProfile(next.profile);
    setPackages(await api<Package[]>('/packages'));
  }
  useEffect(()=>{action(()=>refresh(true))},[]);
  async function queue(route:string,body:unknown){const result=await api<{job:string}>(route,'POST',body);setNotice('Queued job '+result.job+'. Check Jobs, then Refresh YouTube for the result.');await refresh()}
  return <>
    <section className="card"><div className="sectionTitle"><h2>YouTube automation</h2><button disabled={busy} onClick={()=>action(()=>refresh())}>Refresh YouTube</button></div>
      <p>Plan with Ollama, review a final render, upload privately, then approve visibility or a YouTube schedule. Paid image, voice and video generation are not connected.</p>
      {notice&&<p role="status">{notice}</p>}
      <h3>1. Connect your channel</h3>
      <p>Create a Google Cloud OAuth <strong>Desktop app</strong> client and enable YouTube Data API v3. Add your Google account as a test user if the consent screen is in testing. Enable YouTube Analytics API for analytics reports. See <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noreferrer">Google Cloud credentials</a>.</p>
      <label>Import downloaded Desktop client JSON<input type="file" accept=".json,application/json" disabled={busy||data?.connection.connected} onChange={e=>{const file=e.target.files?.[0];if(file)action(async()=>{if(file.size>64000)throw Error('Client JSON exceeds 64 KB');await api('/youtube/client','POST',JSON.parse(await file.text()));await refresh()})}}/></label>
      <div className="inline"><label><input type="checkbox" checked={manage} onChange={e=>setManage(e.target.checked)}/> Allow visibility changes and scheduling</label><label><input type="checkbox" checked={analytics} onChange={e=>setAnalytics(e.target.checked)}/> Request analytics reports</label></div>
      <div className="inline"><button disabled={busy||!data?.connection.configured} onClick={()=>action(async()=>{const result=await api<{url:string}>('/youtube/connect','POST',{manage,analytics});setLink(result.url)})}>Prepare Google sign-in</button>{link&&<a href={link} target="_blank" rel="noreferrer">Sign in with Google →</a>}<button disabled={busy||!data?.connection.connected} onClick={()=>action(async()=>{await api('/youtube/disconnect','POST',{});setLink('');await refresh()})}>Disconnect locally</button></div>
      <p>{data?.connection.connected?`Connected: ${data.connection.channel?.title} · ${data.connection.channel?.id}`:'No connected YouTube channel.'}</p>
      {data?.connection.channel&&<p>Use channel ID <code>{data.connection.channel.id}</code> in the draft’s account field below. Permissions: {data.connection.permissions.join(', ')}.</p>}
      <p>Google login happens on Google’s website. Ninja never asks for your Google password. Tokens are encrypted for this Windows user. Sign-in returns to 127.0.0.1:8000.</p>
    </section>
    <section className="card"><h3>2. Channel profile & production planning</h3>
      {(['audience','language','pillars','tone'] as const).map(key=><label key={key}>{key}<input value={profile[key]} onChange={e=>setProfile({...profile,[key]:e.target.value})}/></label>)}
      <button disabled={busy} onClick={()=>action(async()=>{await api('/youtube/profile','PUT',profile);setNotice('Channel profile saved.')})}>Save channel profile</button>
      <label>Content package<select value={selected} onChange={e=>{setSelected(e.target.value);setScene('')}}><option value="">Create or choose a package below, then Refresh YouTube</option>{packages.map(p=><option value={p.id} key={p.id}>{p.name}</option>)}</select></label>
      <label>Topic, format and production brief<textarea value={brief} onChange={e=>setBrief(e.target.value)} maxLength={4000}/></label>
      <label>Source notes with URLs or citations · claims still need your review<textarea value={evidence} onChange={e=>setEvidence(e.target.value)} maxLength={6000}/></label>
      <label>Scope<select value={scene} onChange={e=>setScene(e.target.value)}><option value="">New title, description, tags, thumbnail brief and scene outline</option>{packages.find(p=>p.id===selected)?.scenes.map(s=><option value={s.id} key={s.id}>Repair scene: {s.script.slice(0,70)||s.id}</option>)}</select></label>
      <button disabled={busy||!selected||!brief.trim()} onClick={()=>action(()=>queue('/youtube/generate',{package:selected,brief,evidence,scene:scene||null,provider:'ollama'}))}>Generate review draft with Ollama</button>
      <p>Generated text remains a proposal until you apply it. A new outline replaces the scene list; a scene repair changes only the selected scene and clears stale narration and timing. Review facts and asset rights yourself.</p>
    </section>
    <section className="card"><h3>3. Prepare the private upload</h3><p>Use the content desk below to save metadata, select a completed final render, resolve all rights and review the exact YouTube draft. Then prepare an upload for the selected package above.</p>
      <label>Audience designation<select value={kids} onChange={e=>setKids(e.target.value)}><option value="">Choose explicitly…</option><option value="yes">Made for kids</option><option value="no">Not made for kids</option></select></label>
      <label>Realistic altered or synthetic content disclosure<select value={synthetic} onChange={e=>setSynthetic(e.target.value)}><option value="">Choose explicitly…</option><option value="yes">Yes</option><option value="no">No</option></select></label>
      <button disabled={busy||!selected||!kids||!synthetic||!data?.connection.connected} onClick={()=>action(()=>queue('/youtube/prepare',{package:selected,made_for_kids:kids==='yes',synthetic_media:synthetic==='yes'}))}>Check video & prepare exact upload review</button>
      <p>Preparing does not upload. Every upload starts private. Unverified Google API projects may be restricted to private videos. API quota and processing delays are controlled by Google.</p>
    </section>
    <section className="card"><h3>4. Reviews, recovery & analytics</h3><p>After a queued job finishes, refresh this panel. An approved YouTube schedule runs on Google’s servers; Ninja’s emergency stop cannot cancel it. To cancel, review and approve private visibility with an empty schedule.</p>
      {!data?.operations.length&&<p>No YouTube operations yet.</p>}
      {data?.operations.map(op=><OperationCard key={op.id} op={op} api={api} action={action} busy={busy} refresh={refresh} notify={setNotice}/>)}
    </section>
  </>;
}

export function OperationCard({op,api,action,busy,refresh,notify}:Props&{op:Operation;refresh:()=>Promise<void>;notify:(s:string)=>void}) {
  const [visibility,setVisibility]=useState('private'),[schedule,setSchedule]=useState(''),[video,setVideo]=useState('');
  const snapshot=op.params.snapshot as {draft?:{title?:string;schedule?:string}}|undefined;
  const today=new Date().toISOString().slice(0,10);
  const [start,setStart]=useState(today.slice(0,8)+'01'),[end,setEnd]=useState(today);
  async function post(suffix:string,body:unknown={}){const result=await api<{job?:string}>('/youtube/operations/'+op.id+'/'+suffix,'POST',body);notify(result.job?'Queued job '+result.job+'. Check Jobs for results.':'Saved. Review the updated operation below.');await refresh()}
  return <article className="card"><h4>{op.kind} · {op.state}</h4><p>Operation {op.id}{op.kind==='upload'?` · ${op.offset} bytes confirmed`:''}</p>
    {op.remote_id&&<a href={'https://studio.youtube.com/video/'+op.remote_id+'/edit'} target="_blank" rel="noreferrer">Open confirmed video in YouTube Studio →</a>}
    <p>Target channel: {String(op.params.channel||'Unspecified')} ? {snapshot?.draft?.title||op.kind}</p>{snapshot?.draft?.schedule&&<p>Publication: {snapshot.draft.schedule}</p>}<details><summary>Exact technical review details</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:420,overflow:'auto'}}>{JSON.stringify(op.params,null,2)}</pre></details>
    {op.state==='review'&&<button className="primary" disabled={busy} onClick={()=>action(()=>post(op.kind==='draft'?'apply':'approve'))}>{op.kind==='draft'?'Apply this production draft':op.kind==='upload'?'Approve this exact PRIVATE upload':'Approve this exact visibility / schedule change'}</button>}
    {['paused','initiating','uploading','updating','reconciliation_required'].includes(op.state)&&<><button disabled={busy} onClick={()=>action(()=>post('resume'))}>Resume / verify existing operation</button>{op.kind==='upload'&&<><label>Confirmed matching video ID from YouTube Studio<input value={video} maxLength={11} onChange={e=>setVideo(e.target.value)}/></label><p>Check that this is the same reviewed video file and channel. Google cannot verify the local file hash.</p><button disabled={busy||video.length!==11} onClick={()=>action(()=>post('reconcile',{video}))}>Confirm matching video & reconcile</button></>}</>}
    {op.kind==='upload'&&op.remote_id&&<>
      <label>Desired visibility<select value={visibility} onChange={e=>setVisibility(e.target.value)}><option value="private">Private / cancel existing schedule</option><option value="unlisted">Unlisted</option><option value="public">Public now</option></select></label>
      <label>Optional publish time · ISO with timezone, for private videos only<input placeholder="2026-10-10T18:00:00+05:30" value={schedule} onChange={e=>setSchedule(e.target.value)}/></label>
      <button disabled={busy} onClick={()=>action(()=>post('visibility',{visibility,publish_at:schedule||null}))}>Prepare visibility / schedule review</button>
      <div className="inline"><label>Report start<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>Report end<input type="date" value={end} max={today} onChange={e=>setEnd(e.target.value)}/></label><button disabled={busy||!start||!end} onClick={()=>action(()=>post('analytics',{start,end}))}>Retrieve real analytics</button></div><p>Statistics and report data appear in the completed Jobs result. Missing data stays unavailable; no simulated metrics are used.</p>
    </>}
  </article>;
}
