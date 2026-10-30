export function uploadMedia(file:File,progress:(value:number)=>void,signal?:AbortSignal):Promise<{id:string;job:string}>{
 return new Promise((resolve,reject)=>{
  const xhr=new XMLHttpRequest();xhr.open('POST','/api/import/upload');xhr.setRequestHeader('X-Ninja-Token',sessionStorage.getItem('ninja-token')||'');
  xhr.upload.onprogress=e=>{if(e.lengthComputable)progress(Math.round(e.loaded/e.total*100))};
  const abort=()=>xhr.abort();signal?.addEventListener('abort',abort,{once:true});
  xhr.onloadend=()=>signal?.removeEventListener('abort',abort);
  xhr.onerror=()=>reject(Error('Upload interrupted. Check Ninja is running, then retry.'));
  xhr.onabort=()=>reject(Error('Upload cancelled. Choose the file again to retry.'));
  xhr.onload=()=>{try{const body=JSON.parse(xhr.responseText);if(xhr.status>=200&&xhr.status<300)resolve(body);else reject(Error(typeof body.detail==='string'?body.detail:'Upload failed; check the file format and size.'))}catch{reject(Error('Ninja returned an invalid upload response. Reconnect and retry.'))}};
  const data=new FormData();data.append('file',file);xhr.send(data);
 });
}
