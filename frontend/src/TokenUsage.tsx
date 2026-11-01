import {useEffect,useState} from 'react';
import {ClientProps} from './TaskPanel';

type Period={period:string;input:number;output:number};
export const kilo=(n:number)=>n<1000?String(n):n<1e6?(n/1000).toFixed(1)+'k':(n/1e6).toFixed(1)+'M';
const label=(period:string,by:'day'|'month')=>new Date(period+(by==='day'?'T00:00':'-01T00:00')).toLocaleDateString('en-IN',by==='day'?{day:'numeric',month:'short'}:{month:'short',year:'2-digit'});

// Local Qwen token use per day (30 days) or month (12 months), one bar per period; hover a bar for its numbers.
export default function TokenUsage({api}:Pick<ClientProps,'api'>){
 const [data,setData]=useState<{day:Period[];month:Period[]}>(),[by,setBy]=useState<'day'|'month'>('day'),[error,setError]=useState('');
 useEffect(()=>{api<{day:Period[];month:Period[]}>('/assistant/usage').then(setData).catch(e=>setError(String(e)))},[]);
 if(error)return <p className="error" role="alert">{error}</p>;
 if(!data)return <p role="status">Loading token use…</p>;
 const rows=data[by],max=Math.max(1,...rows.map(r=>r.input+r.output)),total=rows.reduce((sum,r)=>sum+r.input+r.output,0);
 const w=100/rows.length,every=by==='day'?7:3;
 return <section className="tokenUsage">
  <div className="segmented" role="group" aria-label="Group by">{(['day','month'] as const).map(k=><button type="button" key={k} aria-pressed={by===k} onClick={()=>setBy(k)}>{k==='day'?'Daily':'Monthly'}</button>)}</div>
  <p className="usageTotal"><strong>{total.toLocaleString('en-IN')}</strong> tokens {by==='day'?'in the last 30 days':'in the last 12 months'}</p>
  <svg className="usageChart" viewBox="0 0 100 60" preserveAspectRatio="none" role="img" aria-label={(by==='day'?'Daily':'Monthly')+' token use bar chart'}>
   <line x1="0" x2="100" y1="60" y2="60" className="usageAxis"/>
   {rows.map((r,i)=>{const h=(r.input+r.output)/max*58;return <g key={r.period}><title>{label(r.period,by)}: {(r.input+r.output).toLocaleString('en-IN')} tokens ({r.input.toLocaleString('en-IN')} in, {r.output.toLocaleString('en-IN')} out)</title><rect className="usageHit" x={i*w} y="0" width={w} height="60"/>{h>0&&<rect className="usageBar" x={i*w+w*.15} y={60-h} width={w*.7} height={h} rx=".6"/>}</g>})}
  </svg>
  <div className="usageLabels">{rows.map((r,i)=><span key={r.period}>{(rows.length-1-i)%every===0?label(r.period,by):''}</span>)}</div>
  <details><summary>Show as table</summary><table className="usageTable"><thead><tr><th>{by==='day'?'Day':'Month'}</th><th>In</th><th>Out</th></tr></thead><tbody>{rows.filter(r=>r.input+r.output).reverse().map(r=><tr key={r.period}><td>{label(r.period,by)}</td><td>{r.input.toLocaleString('en-IN')}</td><td>{r.output.toLocaleString('en-IN')}</td></tr>)}</tbody></table></details>
 </section>;
}
