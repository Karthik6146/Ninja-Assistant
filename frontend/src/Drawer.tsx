import {ReactNode,useEffect,useRef} from 'react';
import Icon from './Icons';

// Native <dialog> gives focus trapping, Esc to close and an inert page behind it.
export default function Drawer({open,onClose,title,side='left',children}:{open:boolean;onClose:()=>void;title:string;side?:'left'|'right';children:ReactNode}){
 const ref=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const d=ref.current;if(!d)return;if(open&&!d.open)d.showModal();if(!open&&d.open)d.close()},[open]);
 return <dialog ref={ref} className={'drawer '+side} aria-label={title} onClose={onClose} onClick={e=>{if(e.target===ref.current)onClose()}}>
  <div className="drawerHead"><h2>{title}</h2><button className="iconButton" type="button" onClick={onClose} aria-label={'Close '+title}><Icon name="close"/></button></div>
  <div className="drawerBody">{open&&children}</div>
 </dialog>;
}
