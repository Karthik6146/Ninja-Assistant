import {useEffect,useState} from 'react';
import {ClientProps} from './TaskPanel';
import {Project} from './types';
import {Channel} from './StudioConnections';
import StudioConnections from './StudioConnections';
import YouTubeStudio from './YouTubeStudio';
import ContentStudio from './ContentStudio';
import {useDraft} from './useDraft';

const TABS=[['uploads','Uploads'],['drafts','Drafts'],['channel','Channel profile'],['setup','Setup']] as const;
type Tab=typeof TABS[number][0];

// Laid out like YouTube Studio: who is connected on top, then one job per tab.
export default function YouTubePage({projects,...props}:ClientProps&{projects:Project[]}){
 const [tab,setTab]=useDraft<Tab>('ninja-youtube-tab','uploads'),[channels,setChannels]=useState<Channel[]>([]);
 useEffect(()=>{props.api<Channel[]>('/studio/channels').then(setChannels).catch(()=>{})},[tab]);
 return <div className="ytPage">
  <header className="ytHeader">
   {channels.length?<ul className="ytChannels">{channels.map(c=><li key={c.id}>{c.avatar?<img src={c.avatar} width={36} height={36} alt=""/>:<span className="ytAvatar" aria-hidden="true">{c.title.slice(0,1)}</span>}<div><strong>{c.title}</strong><small><i className={'setDot'+(c.connected?' ok':'')} aria-hidden="true"/>{c.connected?'Connected':'Needs reconnecting'}</small></div></li>)}</ul>
   :<p className="ytEmpty">No YouTube channel connected yet.</p>}
   <button className={channels.length?'':'primary'} onClick={()=>setTab('setup')}>{channels.length?'Manage channels':'Connect a channel'}</button>
  </header>
  <nav className="ytTabs" aria-label="YouTube sections">{TABS.map(([key,label])=><button key={key} aria-current={tab===key?'page':undefined} onClick={()=>setTab(key)}>{label}</button>)}</nav>
  {tab==='uploads'&&<YouTubeStudio {...props} view="uploads"/>}
  {tab==='drafts'&&<><ContentStudio {...props} projects={projects} youtube/><YouTubeStudio {...props} view="drafts"/></>}
  {tab==='channel'&&<YouTubeStudio {...props} view="channel"/>}
  {tab==='setup'&&<><YouTubeStudio {...props} view="setup"/><StudioConnections {...props}/></>}
 </div>;
}
