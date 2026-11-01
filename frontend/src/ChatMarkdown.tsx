import {Children,isValidElement,ReactElement,ReactNode,useState} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// Third-party URLs (research, references, editor links) may carry any scheme; only http(s) become links.
export const safeHref=(url?:string)=>url&&/^https?:\/\//i.test(url)?url:undefined;
const LANGS:Record<string,string>={js:'JavaScript',javascript:'JavaScript',ts:'TypeScript',tsx:'TSX',jsx:'JSX',py:'Python',python:'Python',sh:'Shell',bash:'Bash',shell:'Shell',zsh:'Shell',ps1:'PowerShell',powershell:'PowerShell',cmd:'Command Prompt',bat:'Batch',json:'JSON',html:'HTML',css:'CSS',sql:'SQL',java:'Java',c:'C',cpp:'C++',cs:'C#',go:'Go',rust:'Rust',yaml:'YAML',yml:'YAML',md:'Markdown',xml:'XML',kotlin:'Kotlin',php:'PHP'};
// The language label and code text of a fenced block, as react-markdown hands it to <pre>.
export const codeOf=(children:ReactNode)=>{
 const code=Children.toArray(children)[0];
 if(!isValidElement(code))return null;
 const props=(code as ReactElement<{className?:string;children?:ReactNode}>).props;
 const lang=/language-([\w+#-]+)/.exec(props.className||'')?.[1]?.toLowerCase()||'';
 return {label:LANGS[lang]||lang||'Code',text:String(props.children??'').replace(/\n$/,'')};
};
// Code answers look like an editor: language and Copy on top, monospace text that scrolls sideways instead of wrapping.
function CodeBlock({children}:{children?:ReactNode}){
 const [copied,setCopied]=useState(false),code=codeOf(children);
 if(!code)return <pre>{children}</pre>;
 const copy=()=>navigator.clipboard.writeText(code.text).then(()=>{setCopied(true);setTimeout(()=>setCopied(false),1500)}).catch(()=>{});
 return <figure className="codeBlock"><figcaption><span>{code.label}</span><button type="button" onClick={copy} aria-label={'Copy '+code.label+' code'}>{copied?'Copied':'Copy'}</button></figcaption><pre tabIndex={0}><code>{code.text}</code></pre></figure>;
}
export default function ChatMarkdown({text}:{text:string}){
 return <div className="chatMarkdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{
  a:({href,children})=>href&&/^https?:\/\//i.test(href)?<a href={href} target="_blank" rel="noreferrer noopener">{children}</a>:<span>{children}</span>,
  img:({alt})=><span>[Image: {alt||'not loaded'}]</span>,
  pre:({children})=><CodeBlock>{children}</CodeBlock>,
  table:({children})=><div className="markdownTable" tabIndex={0} role="region" aria-label="Scrollable table"><table>{children}</table></div>
 }}>{text}</Markdown></div>;
}
