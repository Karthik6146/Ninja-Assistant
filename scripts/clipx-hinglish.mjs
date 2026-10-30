// Invoke ClipX's existing transliteration; no caption generation is implemented here.
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
const [root,file]=process.argv.slice(2);
const {romanizeHindi}=await import(pathToFileURL(resolve(root,'packages/ai/src/hinglish.ts')).href);
const transcript=JSON.parse(await readFile(file,'utf8'));
transcript.words=transcript.words.map(w=>({...w,text:romanizeHindi(w.text)}));
transcript.script='hi-latn';
await writeFile(file,JSON.stringify(transcript));
