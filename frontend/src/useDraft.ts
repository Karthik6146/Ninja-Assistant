import {useEffect,useState} from 'react';
export function restoreDraft<T>(saved:unknown,initial:T):T{
 if(initial&&typeof initial==='object'&&!Array.isArray(initial))return saved&&typeof saved==='object'&&!Array.isArray(saved)?{...initial,...saved}:initial;
 return (saved??initial) as T;
}
export function useDraft<T>(key:string,initial:T){
 const [value,setValue]=useState<T>(()=>{try{return restoreDraft(JSON.parse(localStorage.getItem(key)||'null'),initial)}catch{return initial}});
 useEffect(()=>{localStorage.setItem(key,JSON.stringify(value))},[key,value]);
 return [value,setValue] as const;
}
