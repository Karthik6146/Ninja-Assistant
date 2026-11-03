import {useEffect,useMemo,useRef,useState} from 'react';
import TaskPanel,{ClientProps,Task,STATE_WORDS,taskTitle,kindName,seconds,took,active} from './TaskPanel';
import {dayLabel} from './AssistantConsole';

const FILTERS:[string,(t:Task)=>boolean][]=[['All',()=>true],['Working',active],['Done',t=>t.state==='completed'],['Failed',t=>t.state==='failed'],['Stopped',t=>t.state==='cancelled']];

// Activity: every recent task on the left (newest first, grouped by day), the chosen task on the right.
export default function ActivityPage({id,select,jobs,...props}:ClientProps&{id:string;select:(id:string)=>void;jobs:Task[]}){
 const [filter,setFilter]=useState('All'),[search,setSearch]=useState('');
 // Open the newest task when nothing is chosen, so the right side is never empty.
 // On arrival a stale or deleted selection also falls back to the newest; later picks (e.g. Show task) are kept.
 const arrived=useRef(false);
 useEffect(()=>{if(!jobs.length)return;if(!id||(!arrived.current&&!jobs.some(j=>j.id===id)))select(jobs[0].id);arrived.current=true},[id,jobs.length]);
 const test=FILTERS.find(([name])=>name===filter)![1];
 const shown=useMemo(()=>jobs.filter(t=>test(t)&&taskTitle(t).toLowerCase().includes(search.toLowerCase())),[jobs,filter,search]);
 const failed=jobs.filter(t=>t.state==='failed').length,done=jobs.filter(t=>t.state==='completed');
 const average=done.length?Math.round(done.reduce((n,t)=>n+seconds(t),0)/done.length):0;
 return <section className="activityBoard" aria-label="Recent tasks">
  <dl className="activityStats">
   <div><dt>Working now</dt><dd>{jobs.filter(active).length}</dd></div>
   <div><dt>Finished</dt><dd>{done.length}<small> of {jobs.length}</small></dd></div>
   <div className={failed?'bad':''}><dt>Failed</dt><dd>{failed}</dd></div>
   <div><dt>Average time</dt><dd>{took(average)}</dd></div>
  </dl>
  <div className="activitySplit">
   <div className="activityList">
    <div className="activityTools"><input type="search" aria-label="Search tasks" placeholder="Search tasks" value={search} onChange={e=>setSearch(e.target.value)}/>
     <div className="activityFilters" role="group" aria-label="Filter tasks">{FILTERS.map(([name,f])=><button type="button" key={name} aria-pressed={filter===name} onClick={()=>setFilter(name)}>{name}<small>{jobs.filter(f).length}</small></button>)}</div></div>
    <ul>{shown.map((t,i)=><li key={t.id}>{(i===0||dayLabel(shown[i-1].created)!==dayLabel(t.created))&&<h4>{dayLabel(t.created)}</h4>}
     <button type="button" aria-current={t.id===id||undefined} onClick={()=>select(t.id)}><i className={'activityDot '+t.state} aria-hidden="true"/><span><strong>{taskTitle(t)}</strong><small>{kindName(t)} · {new Date(t.created*1000).toLocaleTimeString('en-IN',{hour:'numeric',minute:'2-digit'})} · {active(t)?STATE_WORDS[t.state]:STATE_WORDS[t.state]+(t.state==='completed'?' in '+took(seconds(t)):'')}</small></span></button></li>)}</ul>
    {!shown.length&&<p className="profileHint">{jobs.length?'No tasks match this filter.':'No tasks yet. Ask Jarvis something.'}</p>}
   </div>
   <TaskPanel {...props} id={id} select={select} jobs={jobs} embedded/>
  </div>
 </section>;
}
