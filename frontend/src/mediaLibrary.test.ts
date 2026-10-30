import {describe,it,expect} from 'vitest';
import {MediaItem,mediaMatches,mediaStatus,duration} from './mediaLibrary';
const item={id:'media',name:'Podcast',original_name:'source.mp4',missing:false,kind:'Rendered',created:1,size:100,source:'source.mp4',metadata:{duration:90,width:720,height:1280,fps:'30',codec:'h264',audio:true},edl:null,suggestions:[],exports:[],publications:[],library:{revision:0,name:'',labels:['Education'],notes:'calm editing',favourite:true,archived:false}} satisfies MediaItem;
describe('Media library filters',()=>{
 it('combines collection, labels, status and notes search',()=>{expect(mediaMatches(item,'Renders','calm','Education','Ready',[])).toBe(true);expect(mediaMatches(item,'Imports','','','All statuses',[])).toBe(false);expect(mediaMatches(item,'Favourites','','Other','Ready',[])).toBe(false)});
 it('uses saved publication evidence without treating a private upload as public',()=>{expect(mediaStatus({...item,publications:[{state:'private',channel:'A'}]},[])).toBe('Uploaded / private');expect(mediaStatus({...item,publications:[{state:'public',channel:'A'}]},[])).toBe('Published');expect(mediaStatus({...item,publications:[{state:'failed',channel:'A'}]},[])).toBe('Needs attention')});
 it('keeps archived media out of normal collections',()=>{const archived={...item,library:{...item.library,archived:true}};expect(mediaMatches(archived,'All media','','','All statuses',[])).toBe(false);expect(mediaMatches(archived,'Archive','','','Ready',[])).toBe(true)});
 it('reports missing files before readiness and formats long durations',()=>{expect(mediaStatus({...item,missing:true},[])).toBe('Missing file');expect(duration(3661)).toBe('1:01:01');expect(duration(60)).toBe('1:00')});
});
