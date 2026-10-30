import {ReactElement} from 'react';
// One authored icon set: 24px grid, 1.75 stroke, round caps. currentColor so states recolor them.
const paths:Record<string,ReactElement>={
 jarvis:<><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21"/></>,
 studio:<><rect x="3" y="9" width="18" height="11" rx="2"/><path d="M3 9l2.2-4.6a1 1 0 0 1 .9-.6h12.8a1 1 0 0 1 .9.6L21 9M8.5 3.8 6.8 9M13.5 3.8 11.8 9M18.2 4 16.6 9"/></>,
 youtube:<><rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10 9.4v5.2l4.6-2.6z" fill="currentColor"/></>,
 activity:<path d="M3 12h4l3-7 4 14 3-7h4"/>,
 settings:<><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></>,
 stop:<><circle cx="12" cy="12" r="9"/><rect x="9" y="9" width="6" height="6" rx="1" fill="currentColor" stroke="none"/></>,
 history:<><path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1"/><path d="M3.5 4.5v4h4M12 7.5V12l3 2"/></>,
 today:<><rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/><path d="M8 14h3"/></>,
 mic:<><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/></>,
 send:<path d="M4.5 12 20 4.5 14.5 20l-2.7-6.3z"/>,
 close:<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>,
 plus:<path d="M12 5.5v13M5.5 12h13"/>,
 lock:<><rect x="5" y="10.5" width="14" height="9.5" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/></>,
 mute:<><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 10.2 5.3M18.5 11c0 .8-.1 1.5-.4 2.2M12 17.5V21M4 4l16 16"/></>,
 hand:<path d="M8 13V6.5a1.5 1.5 0 0 1 3 0V11m0-5.5V5a1.5 1.5 0 0 1 3 0v6m0-4.5a1.5 1.5 0 0 1 3 0V13c0 4-2.5 7-6.5 7-2.5 0-4-1.2-5.3-3.2L4 13.6a1.5 1.5 0 0 1 2.4-1.8L8 13"/>,
 check:<path d="M5 12.5l4.5 4.5L19 7.5"/>,
 alert:<><path d="M12 4 2.8 19.5h18.4z"/><path d="M12 10v4M12 17v.01"/></>,
 chevron:<path d="M9 6l6 6-6 6"/>,
};
export default function Icon({name,size=20,label}:{name:keyof typeof paths;size?:number;label?:string}){
 return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" role={label?'img':undefined} aria-label={label} aria-hidden={label?undefined:true}>{paths[name]}</svg>;
}
