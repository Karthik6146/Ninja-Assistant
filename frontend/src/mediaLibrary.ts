import {Project} from './types';
import {Task} from './TaskPanel';
export type Details={revision:number;name:string;labels:string[];notes:string;favourite:boolean;archived:boolean};
export type MediaItem=Project&{created:number;original_name:string;size:number|null;missing:boolean;kind:'Imported'|'Rendered';library:Details;exports:{file:string;revision:number}[];publications:{state:string;channel:string;remote_id?:string}[]};
export function mediaStatus(item:MediaItem,jobs:Task[]){
 if(item.missing)return 'Missing file';
 if(!item.metadata){const j=jobs.find(j=>j.project===item.id&&j.kind==='probe');return j&&['failed','cancelled'].includes(j.state)?'Needs attention':'Processing'}
 const states=item.publications.map(p=>p.state);
 if(states.some(s=>['failed','uncertain','conflict','paused','reconciliation_required'].includes(s)))return 'Needs attention';
 if(states.some(s=>['queued','running','initiating','uploading','processing','confirming','updating'].includes(s)))return 'Publishing';
 if(states.includes('public'))return 'Published';
 if(states.includes('scheduled'))return 'Scheduled';
 if(states.some(s=>['private','unlisted'].includes(s)))return 'Uploaded / private';
 return 'Ready';
}
export function duration(value?:number){if(value===undefined)return '—';const s=Math.floor(value);return (s>=3600?Math.floor(s/3600)+':':'')+String(Math.floor(s/60)%60).padStart(s>=3600?2:1,'0')+':'+String(s%60).padStart(2,'0')}
export function fileSize(value:number|null){if(value===null)return 'Unavailable';return value>=1024**3?(value/1024**3).toFixed(1)+' GB':(value/1024**2).toFixed(1)+' MB'}
export function mediaMatches(item:MediaItem,view:string,search:string,label:string,status:string,jobs:Task[]){return (view==='Archive'?item.library.archived:!item.library.archived)&&(view!=='Imports'||item.kind==='Imported')&&(view!=='Renders'||item.kind==='Rendered')&&(view!=='Favourites'||item.library.favourite)&&(!label||item.library.labels.includes(label))&&(status==='All statuses'||mediaStatus(item,jobs)===status)&&(item.name+' '+item.original_name+' '+item.library.labels.join(' ')+' '+item.library.notes).toLowerCase().includes(search.toLowerCase())}
