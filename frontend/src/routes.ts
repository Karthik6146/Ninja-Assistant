// Areas of the app and their URL hashes. Old bookmarks (#home, #video studio, #recordings…) still land in the right place.
export type Area='Jarvis'|'Studio'|'YouTube'|'Activity'|'Settings';
export const AREAS:{name:Area;icon:'jarvis'|'studio'|'youtube'|'activity'|'settings'}[]=[{name:'Jarvis',icon:'jarvis'},{name:'Studio',icon:'studio'},{name:'YouTube',icon:'youtube'},{name:'Activity',icon:'activity'},{name:'Settings',icon:'settings'}];
export const STUDIO=['Video Studio','Automations','Media Library','Content'] as const;
export type StudioTab=typeof STUDIO[number];
export const slug=(value:string)=>value.toLowerCase().replace(/ /g,'-');
export function route(hash:string):{area:Area;studio:StudioTab}{
 const [head,sub]=decodeURIComponent(hash.replace(/^#/,'')).toLowerCase().split('/');
 const legacy:Record<string,[Area,StudioTab?]>={'':['Jarvis'],home:['Jarvis'],'media library':['Studio','Media Library'],recordings:['Studio','Media Library'],'video studio':['Studio','Video Studio'],automations:['Studio','Automations']};
 const found=AREAS.find(a=>slug(a.name)===head);
 const [area,tab]=found?[found.name,STUDIO.find(t=>slug(t)===sub)]:legacy[head]||['Jarvis'];
 return {area,studio:tab||'Video Studio'};
}

