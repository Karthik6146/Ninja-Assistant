import {Fragment, useEffect, useState} from 'react';

type API = <T>(route:string, method?:string, body?:unknown)=>Promise<T>;
type Props = {api:API; action:(fn:()=>Promise<void>)=>Promise<void>; busy:boolean};
export type Operation = {id:string;kind:string;state:string;remote_id:string|null;offset:number;remote_status?:{publishAt?:string};params:Record<string,unknown>};
type Profile = {audience:string;language:string;pillars:string;tone:string};
type Overview = {connection:{configured:boolean;connected:boolean;channel:{id:string;title:string}|null;permissions:string[]};profile:Profile;operations:Operation[]};
type Package = {id:string;name:string;scenes:{id:string;script:string}[]};

export default function YouTubeStudio({api,action,busy,view}:Props&{view?:'uploads'|'drafts'|'channel'|'setup'}) {
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
  async function queue(route:string,body:unknown){const result=await api<{job:string}>(route,'POST',body);setNotice('Started. Follow it in Activity, then press Refresh under Uploads.');await refresh()}
  const [open,setOpen]=useState('');
  const title=(op:Operation)=>(op.params.snapshot as {draft?:{title?:string}}|undefined)?.draft?.title||KIND[op.kind]||op.kind;
  const ops=data?.operations||[];
  return <>
    {notice&&<p role="status" className="cmsNotice">{notice}</p>}
    {(!view||view==='uploads')&&<section className="ytPanel" aria-label="Uploads">
      <div className="ytPanelHead"><p>{ops.length?ops.length+' operation'+(ops.length>1?'s':''):'Nothing uploaded yet'} · every upload starts private</p><button disabled={busy} onClick={()=>action(()=>refresh())}>Refresh</button></div>
      {!!ops.length&&<table className="ytTable"><thead><tr><th>Video</th><th>Status</th><th>Type</th><th>Channel</th><th/></tr></thead><tbody>
        {ops.map(op=><Fragment key={op.id}><tr className={open===op.id?'open':''}><td><strong>{title(op)}</strong>{op.remote_id&&<a href={'https://studio.youtube.com/video/'+op.remote_id+'/edit'} target="_blank" rel="noreferrer">Open in YouTube Studio ↗</a>}</td><td><span className={'ytState '+op.state}>{STATE[op.state]||op.state.replaceAll('_',' ')}</span></td><td>{KIND[op.kind]||op.kind}</td><td>{String(op.params.channel||'—')}</td><td><button onClick={()=>setOpen(open===op.id?'':op.id)} aria-expanded={open===op.id}>{op.state==='review'?'Review':open===op.id?'Close':'Details'}</button></td></tr>
        {open===op.id&&<tr className="ytDetail"><td colSpan={5}><OperationCard op={op} api={api} action={action} busy={busy} refresh={refresh} notify={setNotice}/></td></tr>}</Fragment>)}
      </tbody></table>}
      {!ops.length&&<p className="profileHint">Prepare an upload from the Drafts tab. It shows up here for your review before anything is sent to YouTube.</p>}
      <small className="ytNote">A schedule you approve runs on Google's servers, so Ninja's Stop button cannot cancel it. To cancel, set the video back to private here.</small>
    </section>}
    {(!view||view==='drafts')&&<div className="ytGrid">
      <section className="ytPanel"><h3>Write a draft with Ollama</h3><p>Title, description, tags, a thumbnail brief and a scene outline. Nothing changes until you apply it.</p>
        <label>Content package<select value={selected} onChange={e=>{setSelected(e.target.value);setScene('')}}><option value="">Choose a package</option>{packages.map(p=><option value={p.id} key={p.id}>{p.name}</option>)}</select></label>
        <label>Brief<textarea value={brief} onChange={e=>setBrief(e.target.value)} maxLength={4000} placeholder="Topic, format, length and the angle you want"/></label>
        <label>Sources <span>links or notes; check every claim yourself</span><textarea value={evidence} onChange={e=>setEvidence(e.target.value)} maxLength={6000}/></label>
        <label>Scope<select value={scene} onChange={e=>setScene(e.target.value)}><option value="">Full draft: metadata and scene outline</option>{packages.find(p=>p.id===selected)?.scenes.map(s=><option value={s.id} key={s.id}>Fix one scene: {s.script.slice(0,60)||s.id}</option>)}</select></label>
        <button className="primary" disabled={busy||!selected||!brief.trim()} onClick={()=>action(()=>queue('/youtube/generate',{package:selected,brief,evidence,scene:scene||null,provider:'ollama'}))}>Write draft</button>
      </section>
      <section className="ytPanel"><h3>Prepare a private upload</h3><p>Pick a package with a finished render and a reviewed YouTube draft. Preparing does not upload; you approve it under Uploads.</p>
        <label>Package<select value={selected} onChange={e=>{setSelected(e.target.value);setScene('')}}><option value="">Choose a package</option>{packages.map(p=><option value={p.id} key={p.id}>{p.name}</option>)}</select></label>
        <label>Made for kids?<select value={kids} onChange={e=>setKids(e.target.value)}><option value="">Choose</option><option value="no">No</option><option value="yes">Yes</option></select></label>
        <label>Realistic altered or synthetic content?<select value={synthetic} onChange={e=>setSynthetic(e.target.value)}><option value="">Choose</option><option value="no">No</option><option value="yes">Yes</option></select></label>
        <button className="primary" disabled={busy||!selected||!kids||!synthetic||!data?.connection.connected} onClick={()=>action(()=>queue('/youtube/prepare',{package:selected,made_for_kids:kids==='yes',synthetic_media:synthetic==='yes'}))}>Prepare upload</button>
        {!data?.connection.connected&&<small className="ytNote">Connect a channel in Setup first.</small>}
      </section>
    </div>}
    {(!view||view==='channel')&&<section className="ytPanel"><h3>Channel profile</h3><p>Ollama uses this for every draft it writes for this channel.</p>
      <div className="ytFields">{([['audience','Audience','Who watches, e.g. Indian students learning tech'],['language','Language','Hinglish'],['pillars','Content pillars','Main topics, comma separated'],['tone','Tone','clear and practical']] as const).map(([key,label,hint])=><label key={key}>{label}<input value={profile[key]} placeholder={hint} onChange={e=>setProfile({...profile,[key]:e.target.value})}/></label>)}</div>
      <button className="primary" disabled={busy} onClick={()=>action(async()=>{await api('/youtube/profile','PUT',profile);setNotice('Channel profile saved.')})}>Save profile</button>
    </section>}
    {(!view||view==='setup')&&<section className="ytPanel"><h3>Google sign-in</h3>
      <div className="setRow"><i className={'setDot'+(data?.connection.connected?' ok':'')} aria-hidden="true"/><div><strong>{data?.connection.connected?data.connection.channel?.title:'No channel signed in'}</strong><small>{data?.connection.connected?data.connection.channel?.id+' · '+data.connection.permissions.join(', '):data?.connection.configured?'OAuth client ready. Sign in below.':'Import a Google OAuth client to begin.'}</small></div>{data?.connection.connected&&<button disabled={busy} onClick={()=>action(async()=>{await api('/youtube/disconnect','POST',{});setLink('');await refresh()})}>Disconnect</button>}</div>
      <ol className="ytSteps">
        <li className={data?.connection.configured?'done':''}><strong>Create a Desktop app OAuth client</strong><span>In <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noreferrer">Google Cloud credentials</a>, enable YouTube Data API v3 (and YouTube Analytics API for reports). Add yourself as a test user.</span></li>
        <li className={data?.connection.configured?'done':''}><strong>Import its JSON file</strong><label className="button">Choose JSON file<input type="file" accept=".json,application/json" disabled={busy||data?.connection.connected} onChange={e=>{const file=e.target.files?.[0];if(file)action(async()=>{if(file.size>64000)throw Error('Client JSON exceeds 64 KB');await api('/youtube/client','POST',JSON.parse(await file.text()));await refresh()});e.target.value=''}}/></label></li>
        <li className={data?.connection.connected?'done':''}><strong>Sign in with Google</strong>
          <div className="ytChecks"><label><input type="checkbox" checked={manage} onChange={e=>setManage(e.target.checked)}/>Allow visibility changes and scheduling</label><label><input type="checkbox" checked={analytics} onChange={e=>setAnalytics(e.target.checked)}/>Allow analytics reports</label></div>
          <div className="inline"><button disabled={busy||!data?.connection.configured} onClick={()=>action(async()=>{const result=await api<{url:string}>('/youtube/connect','POST',{manage,analytics});setLink(result.url)})}>Get sign-in link</button>{link&&<a className="button primary" href={link} target="_blank" rel="noreferrer">Sign in with Google ↗</a>}</div></li>
      </ol>
      <small className="ytNote">Sign-in happens on Google's site; Ninja never sees your password. Tokens are encrypted for this Windows user.</small>
    </section>}
  </>;
}

const STATE:Record<string,string>={review:'Needs your review',draft:'Draft',queued:'Queued',running:'Working',initiating:'Starting',uploading:'Uploading',processing:'Processing',confirming:'Confirming',private:'Private',unlisted:'Unlisted',public:'Public',scheduled:'Scheduled',failed:'Failed',paused:'Paused',uncertain:'Check needed',conflict:'Conflict',reconciliation_required:'Check needed',applied:'Applied',completed:'Done',cancelled:'Cancelled'};
const KIND:Record<string,string>={upload:'Upload',visibility:'Visibility change',draft:'Ollama draft',analytics:'Analytics'};

export function OperationCard({op,api,action,busy,refresh,notify}:Props&{op:Operation;refresh:()=>Promise<void>;notify:(s:string)=>void}) {
  const [visibility,setVisibility]=useState('private'),[schedule,setSchedule]=useState(''),[video,setVideo]=useState('');
  const snapshot=op.params.snapshot as {draft?:{title?:string;schedule?:string}}|undefined;
  const today=new Date().toISOString().slice(0,10);
  const [start,setStart]=useState(today.slice(0,8)+'01'),[end,setEnd]=useState(today);
  async function post(suffix:string,body:unknown={}){const result=await api<{job?:string}>('/youtube/operations/'+op.id+'/'+suffix,'POST',body);notify(result.job?'Started. Follow it in Activity.':'Saved. Review the updated row.');await refresh()}
  return <article className="ytOperation"><p className="ytMeta">Operation <code>{op.id}</code>{op.kind==='upload'?` · ${op.offset.toLocaleString('en-IN')} bytes confirmed`:''}</p>
    {op.remote_id&&<a href={'https://studio.youtube.com/video/'+op.remote_id+'/edit'} target="_blank" rel="noreferrer">Open confirmed video in YouTube Studio →</a>}
    <p className="ytMeta">Channel {String(op.params.channel||'not set')} · {snapshot?.draft?.title||op.kind}</p>{snapshot?.draft?.schedule&&<p>Publication: {snapshot.draft.schedule}</p>}<details><summary>Exact request sent to YouTube</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:420,overflow:'auto'}}>{JSON.stringify(op.params,null,2)}</pre></details>
    {op.state==='review'&&<button className="primary" disabled={busy} onClick={()=>action(()=>post(op.kind==='draft'?'apply':'approve'))}>{op.kind==='draft'?'Apply this production draft':op.kind==='upload'?'Approve this exact PRIVATE upload':'Approve this exact visibility / schedule change'}</button>}
    {['paused','initiating','uploading','updating','reconciliation_required'].includes(op.state)&&<><button disabled={busy} onClick={()=>action(()=>post('resume'))}>Resume / verify existing operation</button>{op.kind==='upload'&&<><label>Confirmed matching video ID from YouTube Studio<input value={video} maxLength={11} onChange={e=>setVideo(e.target.value)}/></label><p>Check that this is the same reviewed video file and channel. Google cannot verify the local file hash.</p><button disabled={busy||video.length!==11} onClick={()=>action(()=>post('reconcile',{video}))}>Confirm matching video & reconcile</button></>}</>}
    {op.kind==='upload'&&op.remote_id&&<>
      <label>Desired visibility<select value={visibility} onChange={e=>setVisibility(e.target.value)}><option value="private">Private / cancel existing schedule</option><option value="unlisted">Unlisted</option><option value="public">Public now</option></select></label>
      <label>Optional publish time · ISO with timezone, for private videos only<input placeholder="2026-10-10T18:00:00+05:30" value={schedule} onChange={e=>setSchedule(e.target.value)}/></label>
      <button disabled={busy} onClick={()=>action(()=>post('visibility',{visibility,publish_at:schedule||null}))}>Prepare visibility / schedule review</button>
      <div className="inline"><label>Report start<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>Report end<input type="date" value={end} max={today} onChange={e=>setEnd(e.target.value)}/></label><button disabled={busy||!start||!end} onClick={()=>action(()=>post('analytics',{start,end}))}>Retrieve real analytics</button></div><p className="ytMeta">The report appears in Activity when it finishes. Missing numbers stay missing; nothing is estimated.</p>
    </>}
  </article>;
}
