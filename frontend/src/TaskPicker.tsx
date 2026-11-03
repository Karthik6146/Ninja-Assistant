import {useEffect,useRef,useState} from 'react';
import {Task,STATE_WORDS,taskTitle,kindName,active,took,seconds} from './TaskPanel';
import {dayLabel} from './AssistantConsole';
import Icon from './Icons';

// Side-panel task chooser: the chosen task as a button, a searchable menu grouped by day below it.
export default function TaskPicker({id,jobs,select}:{id:string;jobs:Task[];select:(id:string)=>void}){
 const [open,setOpen]=useState(false),[search,setSearch]=useState(''),box=useRef<HTMLDivElement>(null);
 useEffect(()=>{if(!open)return;
  const away=(e:MouseEvent)=>{if(!box.current?.contains(e.target as Node))setOpen(false)};
  const esc=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false)};
  document.addEventListener('mousedown',away);document.addEventListener('keydown',esc);
  return()=>{document.removeEventListener('mousedown',away);document.removeEventListener('keydown',esc)}},[open]);
 const current=jobs.find(j=>j.id===id),shown=jobs.filter(j=>taskTitle(j).toLowerCase().includes(search.toLowerCase()));
 const meta=(t:Task)=>kindName(t)+' · '+new Date(t.created*1000).toLocaleTimeString('en-IN',{hour:'numeric',minute:'2-digit'})+' · '+(STATE_WORDS[t.state]||t.state)+(t.state==='completed'?' in '+took(seconds(t)):'');
 return <div className="taskPicker" ref={box}>
  <button type="button" className="taskPickerButton" aria-haspopup="listbox" aria-expanded={open} onClick={()=>setOpen(v=>!v)}>
   {current?<><i className={'activityDot '+current.state} aria-hidden="true"/><span><strong>{taskTitle(current)}</strong><small>{meta(current)}</small></span></>:<span><strong>Choose a task</strong><small>{jobs.length} recent</small></span>}<Icon name="chevron" size={14}/>
  </button>
  {open&&<div className="taskPickerMenu">
   <input type="search" autoFocus aria-label="Search tasks" placeholder="Search tasks" value={search} onChange={e=>setSearch(e.target.value)}/>
   <ul role="listbox" aria-label="Recent tasks">{shown.map((t,i)=><li key={t.id}>{(i===0||dayLabel(shown[i-1].created)!==dayLabel(t.created))&&<h4>{dayLabel(t.created)}</h4>}
    <button type="button" role="option" aria-selected={t.id===id} onClick={()=>{select(t.id);setOpen(false);setSearch('')}}><i className={'activityDot '+t.state+(active(t)?' live':'')} aria-hidden="true"/><span><strong>{taskTitle(t)}</strong><small>{meta(t)}</small></span>{t.id===id&&<Icon name="check" size={14}/>}</button></li>)}</ul>
   {!shown.length&&<p className="profileHint">No tasks match.</p>}
  </div>}
 </div>;
}
