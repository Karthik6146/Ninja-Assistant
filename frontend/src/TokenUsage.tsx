import {CSSProperties,useEffect,useState} from 'react';
import Icon from './Icons';
import {ClientProps} from './TaskPanel';

type Period={period:string;input:number;output:number;replies:number};
type Model={provider:string;model:string;input:number;output:number;replies:number};
type Usage={day:Period[];month:Period[];models:Model[]};
export const kilo=(n:number)=>n<1000?String(n):n<1e6?(n/1000).toFixed(1)+'k':(n/1e6).toFixed(1)+'M';
const full=(n:number)=>n.toLocaleString('en-IN');
const label=(period:string,by:'day'|'month')=>new Date(period+(by==='day'?'T00:00':'-01T00:00')).toLocaleDateString('en-IN',by==='day'?{day:'numeric',month:'short'}:{month:'short',year:'2-digit'});
export const CONTEXT=8192;

// This chat's size, daily (30 days) or monthly (12 months) totals with a bar chart, and the split by model.
export default function TokenUsage({api,chat}:Pick<ClientProps,'api'>&{chat?:{context:number;total:number}}){
 const [data,setData]=useState<Usage>(),[by,setBy]=useState<'day'|'month'>('day'),[pick,setPick]=useState(-1),[error,setError]=useState('');
 useEffect(()=>{api<Usage>('/assistant/usage').then(setData).catch(e=>setError(String(e)))},[]);
 const fill=chat?Math.min(100,Math.round(chat.context/CONTEXT*100)):0;
 const chatCard=chat&&<div className="usageChat"><span>This chat</span><strong>{full(chat.total)} tokens</strong>
  <div className={'meter'+(fill>=80?' warn':'')} role="meter" aria-valuemin={0} aria-valuemax={CONTEXT} aria-valuenow={chat.context} aria-label="Context used by the latest message"><i style={{width:fill+'%'}}/></div>
  <small>Latest message used {full(chat.context)} of {full(CONTEXT)} context tokens ({fill}%).{fill>=80?' Start a new chat soon: older turns will be dropped.':''}</small></div>;
 if(error)return <>{chatCard}<p className="error" role="alert">{error}</p></>;
 if(!data)return <>{chatCard}<p role="status">Loading token use…</p></>;
 const rows=data[by],sum=(r:Period|Model)=>r.input+r.output,max=Math.max(1,...rows.map(sum)),total=rows.reduce((n,r)=>n+sum(r),0);
 const active=rows.filter(sum),peak=active.reduce<Period|undefined>((a,r)=>!a||sum(r)>sum(a)?r:a,undefined),now=rows[rows.length-1];
 const shown=rows[pick<0?rows.length-1:pick],every=by==='day'?7:3,word=by==='day'?'day':'month';
 const modelMax=Math.max(1,...data.models.map(sum));
 return <section className="tokenUsage">
  {chatCard}
  <div className="segmented" role="group" aria-label="Group by">{(['day','month'] as const).map(k=><button type="button" key={k} aria-pressed={by===k} onClick={()=>{setBy(k);setPick(-1)}}>{k==='day'?'Daily':'Monthly'}</button>)}</div>
  <dl className="usageStats">
   <div><dt>{by==='day'?'Today':'This month'}</dt><dd>{kilo(sum(now))}</dd><small>{now.replies} repl{now.replies===1?'y':'ies'}</small></div>
   <div><dt>{by==='day'?'Last 30 days':'Last 12 months'}</dt><dd>{kilo(total)}</dd><small>{active.reduce((n,r)=>n+r.replies,0)} replies</small></div>
   <div><dt>Average per active {word}</dt><dd>{kilo(active.length?Math.round(total/active.length):0)}</dd><small>{active.length} active {word}{active.length===1?'':'s'}</small></div>
   <div><dt>Busiest {word}</dt><dd>{peak?kilo(sum(peak)):'—'}</dd><small>{peak?label(peak.period,by):'No use yet'}</small></div>
  </dl>
  <div className="usageBars" role="group" aria-label={(by==='day'?'Daily':'Monthly')+' tokens; choose a bar for details'} onMouseLeave={()=>setPick(-1)}>
   <span className="usageMax">{kilo(max)}</span>
   {rows.map((r,i)=><button type="button" key={r.period} aria-pressed={r===shown} aria-label={label(r.period,by)+': '+full(sum(r))+' tokens'} onMouseEnter={()=>setPick(i)} onFocus={()=>setPick(i)} onClick={()=>setPick(i)}><i style={{height:sum(r)?Math.max(2,sum(r)/max*100)+'%':0}}/></button>)}
  </div>
  <div className="usageLabels" aria-hidden="true">{rows.map((r,i)=><span key={r.period}>{(rows.length-1-i)%every===0?label(r.period,by):''}</span>)}</div>
  <p className="usageDetail" aria-live="polite"><strong>{label(shown.period,by)}</strong> · {full(sum(shown))} tokens · {full(shown.input)} in · {full(shown.output)} out · {shown.replies} repl{shown.replies===1?'y':'ies'}</p>
  {!!data.models.length&&<section className="usageModels"><h3>By model · last 30 days</h3><ul>{data.models.map(m=><li key={m.provider+m.model}><span title={m.model}>{m.model||'Unknown'}{m.provider==='cloud'&&<em>cloud</em>}</span><b>{kilo(sum(m))}</b><div className="meter"><i style={{width:sum(m)/modelMax*100+'%'}}/></div><small>{m.replies} replies · {kilo(m.replies?Math.round(sum(m)/m.replies):0)} per reply</small></li>)}</ul></section>}
  <p className="usageNote"><b>In</b> is what Jarvis reads for each reply: your message, the chat so far and tool results, so it grows as a chat gets longer. <b>Out</b> is what Jarvis writes. A new chat keeps <b>In</b> small.</p>
  <details className="usageTableBox"><summary><Icon name="chevron" size={14}/>{by==='day'?'Daily':'Monthly'} breakdown<small>{active.length} active {word}{active.length===1?'':'s'}</small></summary>
   <table className="usageTable"><thead><tr><th scope="col">{by==='day'?'Day':'Month'}</th><th scope="col">Total</th><th scope="col">In</th><th scope="col">Out</th><th scope="col" title="Replies">Rep.</th></tr></thead>
   <tbody>{active.slice().reverse().map(r=><tr key={r.period} style={{'--share':sum(r)/max*100+'%'} as CSSProperties}><th scope="row">{label(r.period,by)}</th><td><b>{kilo(sum(r))}</b></td><td title={full(r.input)}>{kilo(r.input)}</td><td title={full(r.output)}>{kilo(r.output)}</td><td>{r.replies}</td></tr>)}</tbody>
   <tfoot><tr><th scope="row">Total</th><td><b>{kilo(total)}</b></td><td>{kilo(active.reduce((n,r)=>n+r.input,0))}</td><td>{kilo(active.reduce((n,r)=>n+r.output,0))}</td><td>{active.reduce((n,r)=>n+r.replies,0)}</td></tr></tfoot></table>
   <small className="usageNote">Bar behind each row shows its share of the busiest {word}. Hover a number for the exact count.</small>
  </details>
 </section>;
}
