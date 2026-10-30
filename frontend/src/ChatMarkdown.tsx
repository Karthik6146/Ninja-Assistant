import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// Third-party URLs (research, references, editor links) may carry any scheme; only http(s) become links.
export const safeHref=(url?:string)=>url&&/^https?:\/\//i.test(url)?url:undefined;
export default function ChatMarkdown({text}:{text:string}){
 return <div className="chatMarkdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml components={{
  a:({href,children})=>href&&/^https?:\/\//i.test(href)?<a href={href} target="_blank" rel="noreferrer noopener">{children}</a>:<span>{children}</span>,
  img:({alt})=><span>[Image: {alt||'not loaded'}]</span>,
  table:({children})=><div className="markdownTable" tabIndex={0} role="region" aria-label="Scrollable table"><table>{children}</table></div>
 }}>{text}</Markdown></div>;
}
