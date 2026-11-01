import json
import http.client
import ipaddress
import os
import socket
import ssl
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit
import httpx

def ollama_url():
    url=os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
    parsed=urlsplit(url)
    if parsed.scheme!='http' or parsed.hostname not in ('localhost','127.0.0.1','::1') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Local Ollama requires a loopback HTTP URL. Configure remote inference as a cloud provider with explicit sharing consent.')
    return url

def local_model():
    from . import db
    with db.connect() as c:
        row=c.execute("SELECT value FROM preferences WHERE key='ollama_model'").fetchone()
    return row[0] if row else os.getenv('OLLAMA_MODEL','')

def cloud_ready():
    return os.getenv('CLOUD_ENABLED')=='true' and bool(os.getenv('CLOUD_API_KEY')) and os.getenv('CLOUD_URL','').startswith('https://') and bool(os.getenv('CLOUD_MODEL'))

def chat_provider():
    """'cloud' only while the user picked it and .env still configures it; otherwise the local model."""
    from . import db
    with db.connect() as c:
        row=c.execute("SELECT value FROM preferences WHERE key='chat_provider'").fetchone()
    return 'cloud' if row and row[0]=='cloud' and cloud_ready() else 'ollama'

def chat_model():
    return os.getenv('CLOUD_MODEL','') if chat_provider()=='cloud' else local_model()

def openai_messages(messages):
    """Ollama-style history to OpenAI chat format: tool calls get ids, tool results point at them,
    and tool names swap '.' for '__' (OpenAI names allow only letters, digits, _ and -)."""
    out=[];waiting=[];owner=None
    def close():
        # Calls that never got a result (a declined or cut-off batch) must not reach the API unanswered.
        if waiting and owner:
            owner['tool_calls']=[c for c in owner['tool_calls'] if c['id'] not in waiting]
            if not owner['tool_calls']:del owner['tool_calls'];owner['content']=owner['content'] or ''
        waiting.clear()
    for m in messages:
        if m.get('role')=='tool':
            if waiting:out.append({'role':'tool','tool_call_id':waiting.pop(0),'content':m.get('content','')})
            else:out.append({'role':'user','content':'Result of '+str(m.get('tool_name','a tool'))+': '+str(m.get('content',''))})
            continue
        close()
        if m.get('role')=='assistant' and m.get('tool_calls'):
            calls=[{'id':f'call_{len(out)}_{i}','type':'function','function':{'name':c['function']['name'].replace('.','__'),'arguments':json.dumps(c['function'].get('arguments',{}))}} for i,c in enumerate(m['tool_calls'])]
            owner={'role':'assistant','content':m.get('content') or None,'tool_calls':calls};out.append(owner);waiting.extend(c['id'] for c in calls)
        else:out.append({'role':m['role'],'content':m.get('content','')})
    close()
    return out

def cloud_turn(messages,schemas,max_tokens):
    """One tool turn on the OpenAI-compatible cloud API from .env; the conversation and tool results leave this PC."""
    from .agent_models import AgentTurn,ToolCall
    import time,uuid
    tools=[{**t,'function':{**t['function'],'name':t['function']['name'].replace('.','__')}} for t in schemas]
    body={'model':os.environ['CLOUD_MODEL'],'messages':openai_messages(messages),'max_tokens':max_tokens,'temperature':0,**({'tools':tools} if tools else {})}
    started=time.monotonic()
    try:
        response=httpx.post(os.environ['CLOUD_URL'].rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+os.environ['CLOUD_API_KEY']},json=body,timeout=120)
        response.raise_for_status();value=response.json();message=value['choices'][0]['message']
    except (httpx.HTTPError,ValueError,KeyError,IndexError,TypeError):raise ValueError('Cloud model request failed. Check CLOUD_URL, CLOUD_MODEL and the API key in .env, or switch back to the local model') from None
    calls=[]
    for item in (message.get('tool_calls') or [])[:12]:
        try:arguments=json.loads(item['function'].get('arguments') or '{}')
        except json.JSONDecodeError:arguments={}
        calls.append(ToolCall(id=str(item.get('id') or uuid.uuid4().hex),name=item['function']['name'].replace('__','.'),arguments=arguments if isinstance(arguments,dict) else {}))
    usage=value.get('usage') or {}
    counts={k:usage.get(v) if type(usage.get(v))==int else None for k,v in [('input_tokens','prompt_tokens'),('output_tokens','completion_tokens')]}
    return AgentTurn(text=(message.get('content') or '')[:12000],calls=calls,usage=counts,timing={'model_seconds':round(time.monotonic()-started,3)})

def unload_local_models():
    """Caller holds model.lock while handing the GPU to a local media service."""
    try:
        with httpx.Client(base_url=ollama_url(),timeout=30,trust_env=False) as client:
            response=client.get('/api/ps');response.raise_for_status()
            for model in response.json().get('models',[]):client.post('/api/generate',json={'model':model['name'],'keep_alive':0}).raise_for_status()
    except httpx.ConnectError:pass  # Ollama need not be running for media-only work.
    except httpx.HTTPError:raise ValueError('Could not release Ollama GPU memory; stop active chats or restart Ollama before retrying') from None


def release_local_model():
    """Unload only Ninja's chat model from Ollama; other models the owner runs stay as they are."""
    try:
        with httpx.Client(base_url=ollama_url(),timeout=10,trust_env=False) as client:
            client.post('/api/generate',json={'model':local_model(),'keep_alive':0})
    except (httpx.HTTPError,ValueError):pass  # Ollama already stopped or not configured.


def warm_local_model():
    """Preload the chat model when a voice session starts; skipped while media work owns the GPU."""
    from filelock import FileLock, Timeout
    from .config import DATA
    try:
        with FileLock(DATA/'model.lock',timeout=0), httpx.Client(base_url=ollama_url(),timeout=60,trust_env=False) as client:
            # Same num_ctx as agent_turn, or Ollama reloads the model on the first real turn.
            client.post('/api/generate',json={'model':local_model(),'keep_alive':-1,'options':{'num_ctx':8192}})
        return True
    except (Timeout,httpx.HTTPError):return False


def see(prompt,images,*,max_tokens=400):
    """One local vision answer about base64 JPEG images. Same num_ctx and keep_alive as agent_turn, so the chat model is not reloaded."""
    from filelock import FileLock, Timeout
    from .config import DATA
    body={'model':local_model(),'stream':False,'think':False,'keep_alive':-1,'options':{'num_ctx':8192,'num_predict':max_tokens,'temperature':0},
          'messages':[{'role':'user','content':prompt,'images':images}]}
    try:
        with FileLock(DATA/'model.lock',timeout=20),httpx.Client(trust_env=False,timeout=httpx.Timeout(180,connect=5)) as client:
            value=client.post(ollama_url()+'/api/chat',json=body).raise_for_status().json()
    except Timeout:raise ValueError('The model is busy with another step; ask again in a moment') from None
    except httpx.HTTPError:raise ValueError('The local model could not look at the picture; check that Ollama is running') from None
    text=value.get('message',{}).get('content','').strip()
    if not text:raise ValueError('The model returned no description')
    return text


def provider_status():
    selected=local_model()
    local={'id':'ollama','name':'Ollama','scope':'local','model':selected,'models':[], 'available':False,'message':'Start Ollama, then refresh connections.'}
    try:
        response=httpx.get(ollama_url()+'/api/tags',timeout=3)
        response.raise_for_status()
        local['models']=[m['name'] for m in response.json()['models']]
        local['available']=selected in local['models']
        local['message']='Ready' if local['available'] else 'Choose an installed model in Settings.'
    except (httpx.HTTPError,ValueError,KeyError):pass
    enabled=cloud_ready()
    return [local,{'id':'cloud','name':'Cloud API','scope':'external','model':os.getenv('CLOUD_MODEL',''),'models':[os.getenv('CLOUD_MODEL')] if enabled else [],'available':enabled,'message':'Configured; availability verified on request. Explicit sharing consent required.' if enabled else 'Disabled. Configure CLOUD_ENABLED, URL, model and API key in .env.'}]


def stream_chat(messages, provider, model, on_chunk, structured=False, on_usage=None):
    """Visible answer tokens only; child-process cancellation bounds blocked requests."""
    import json
    from filelock import FileLock, Timeout
    from .config import DATA
    if sum(len(m['content']) for m in messages)>24000:
        raise ValueError('Conversation context exceeds 24,000 characters. Start a new conversation or shorten attachments.')
    if provider=='ollama':
        model=model or local_model()
        if not model:raise ValueError('Select an installed Ollama model in Settings.')
        url=ollama_url()+'/api/chat'
        headers={};body={'model':model,'stream':True,'think':False,'messages':messages,'options':{'num_predict':2048}}
        if structured:
            body['format']={'type':'object','properties':{'text':{'type':'string'},'citations':{'type':'array','items':{'type':'integer'}}},'required':['text','citations']}
    elif provider=='cloud' and os.getenv('CLOUD_ENABLED')=='true':
        url=os.getenv('CLOUD_URL','').rstrip('/')+'/chat/completions'
        if not url.startswith('https://') or not os.getenv('CLOUD_API_KEY') or not os.getenv('CLOUD_MODEL'):raise ValueError('Cloud provider is not configured.')
        headers={'Authorization':'Bearer '+os.environ['CLOUD_API_KEY']}
        body={'model':os.environ['CLOUD_MODEL'],'stream':True,'stream_options':{'include_usage':True},'messages':messages,'max_tokens':2048}
    else:raise ValueError('Cloud sharing is disabled. Use Ollama or explicitly configure a cloud provider.')
    text='';done=False;usage={'input_tokens':None,'output_tokens':None}
    try:
        with FileLock(DATA/'model.lock',timeout=0), httpx.stream('POST',url,headers=headers,json=body,timeout=httpx.Timeout(120,connect=5)) as response:
            if response.status_code>=400:raise ValueError(f'Model request returned HTTP {response.status_code}. Check the selected model and provider settings.')
            for line in response.iter_lines():
                if not line:continue
                if provider=='cloud':
                    if not line.startswith('data:'):continue
                    line=line[5:].strip()
                    if line=='[DONE]':done=True;break
                data=json.loads(line)
                if data.get('error'):raise ValueError('Provider rejected generation. Check model availability and provider logs.')
                counts=data if provider=='ollama' else data.get('usage') or {}
                keys=('prompt_eval_count','eval_count') if provider=='ollama' else ('prompt_tokens','completion_tokens')
                reported={name:counts.get(key) for name,key in zip(usage,keys)}
                if any(type(v)==int and v>=0 for v in reported.values()):
                    for name,value in reported.items():
                        if type(value)==int and value>=0:usage[name]=value
                    if on_usage:on_usage(dict(usage),provider,body['model'])
                if provider=='ollama':
                    chunk=data.get('message',{}).get('content','');done=bool(data.get('done'))
                else:
                    choices=data.get('choices',[])
                    chunk=choices[0].get('delta',{}).get('content','') if choices else ''
                    if choices and choices[0].get('finish_reason'):done=True
                if chunk:
                    text+=chunk
                    if len(text)>100000:raise ValueError('Model response exceeded output limit')
                    on_chunk(text)
                if provider=='ollama' and done:break
    except Timeout:raise ValueError('Another model step is running. Retry after it finishes.') from None
    except httpx.HTTPError:raise ValueError('Model connection failed or timed out. Start Ollama/check the provider, then retry this task.') from None
    except json.JSONDecodeError:raise ValueError('Provider sent an invalid stream. Check API compatibility.') from None
    if not done or not text.strip():raise ValueError('Provider stream ended without a complete answer. Partial text is saved in Activity; retry explicitly.')
    return {'text':text,'provider':provider,'model':body['model'],'usage':usage}

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden: self.parts.append(data.strip())

def public_ip(text):
    ip=ipaddress.ip_address(text)
    if ip.version==6:
        embedded=ip.ipv4_mapped or ip.sixtofour or (ipaddress.IPv4Address(int(ip)&0xFFFFFFFF) if ip in ipaddress.ip_network('64:ff9b::/96') else None)
        if embedded and not embedded.is_global:return False
    return ip.is_global and not ip.is_multicast

def public_addresses(url):
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):
        raise ValueError('Only public HTTPS URLs on port 443 are permitted')
    addresses={r[4][0] for r in socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)}
    if not addresses or any(not public_ip(a) for a in addresses):
        raise ValueError('Private, loopback, reserved, and local network URLs are blocked')
    return u,addresses

def extract(url,hops=3):
    u,addresses=public_addresses(url)
    # Pin the validated IP at connection time, preserving hostname TLS verification.
    import truststore
    # Windows' certificate verifier: same strictness, but it fetches intermediates that some sites forget to send.
    conn=http.client.HTTPSConnection(u.hostname,443,timeout=15,context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
    sock=socket.create_connection((sorted(addresses)[0],443),timeout=15)
    conn.sock=conn._context.wrap_socket(sock,server_hostname=u.hostname)
    try:
        conn.request('GET',(u.path or '/')+('?' + u.query if u.query else ''),headers={'User-Agent':'NinjaAssistant/0.1','Accept':'text/html,text/plain'})
        response=conn.getresponse()
        if response.status in (301,302,303,307,308) and response.getheader('Location') and hops:
            from urllib.parse import urljoin
            # Each hop goes through the same public-address check and pinning.
            return extract(urljoin(url,response.getheader('Location')),hops-1)
        if response.status!=200: raise ValueError(f'Source returned {response.status}')
        if not any(t in response.getheader('Content-Type','') for t in ('text/html','text/plain')): raise ValueError('Unsupported source type')
        raw=response.read(1_000_001)
        if len(raw)>1_000_000: raise ValueError('Source exceeds 1 MB limit')
        html=raw.decode('utf-8',errors='replace')
        import trafilatura
        # Main article text without menus, footers and cookie banners; one paragraph per line.
        excerpt=trafilatura.extract(html,url=url,include_comments=False,include_tables=True,deduplicate=True) or ''
        if len(excerpt)<200:
            parser=Text(); parser.feed(html); excerpt='\n'.join(p for p in parser.parts if p)
        excerpt=excerpt[:16000]
        return {'url':url,'retrieved':datetime.now(timezone.utc).isoformat(),'excerpt':excerpt,'status':'retrieved','verification':'Source excerpt only; claims have not been independently verified'}
    finally: conn.close()

def complete(prompt, provider='ollama', *, schema=None):
    from filelock import FileLock, Timeout
    from .config import DATA
    try:
        with FileLock(DATA/'model.lock',timeout=0):
            return _complete(prompt,provider,schema=schema)
    except Timeout:
        raise ValueError('Another model step is running; try again after it completes')

def _complete(prompt, provider='ollama', *, schema=None):
    # No tools or shell access; explicit cloud opt-in, configurable names, bounded output.
    if len(prompt)>24000: raise ValueError('Model input exceeds 24000 characters')
    if schema is not None and provider!='ollama':raise ValueError('Structured metadata requires the local Ollama model')
    if provider=='ollama':
        model=local_model()
        if not model: raise ValueError('Ollama disconnected: configure OLLAMA_MODEL')
        # Reserve the bounded generation budget for a visible answer.
        body={'model':model,'stream':False,'think':False,'messages':[{'role':'user','content':prompt}],'options':{'num_predict':1024}}
        if schema is not None:body['format']=schema;body['options']['temperature']=0
        response=httpx.post(ollama_url()+'/api/chat',json=body,timeout=120)
        response.raise_for_status(); data=response.json()
        if not data.get('message',{}).get('content','').strip():
            raise ValueError('Ollama returned no visible reply. Try a shorter request or another configured model.')
        return {'text':data['message']['content'],'usage':{'output_tokens':data.get('eval_count'),'input_tokens':data.get('prompt_eval_count')},'provider':'ollama'}
    if provider!='cloud' or os.getenv('CLOUD_ENABLED')!='true': raise ValueError('Cloud sharing is disabled')
    url=os.getenv('CLOUD_URL',''); key=os.getenv('CLOUD_API_KEY',''); model=os.getenv('CLOUD_MODEL','')
    if not url.startswith('https://') or not key or not model: raise ValueError('Cloud provider is disconnected')
    response=httpx.post(url.rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+key},json={'model':model,'max_tokens':1024,'messages':[{'role':'user','content':prompt}]},timeout=120)
    response.raise_for_status(); data=response.json()
    return {'text':data['choices'][0]['message']['content'],'usage':data.get('usage',{}),'provider':'cloud'}


def agent_turn(messages, schemas, *, job, on_text=None, max_tokens=2048, retried=False):
    """Native local tool turn; partial text is provisional until done and validated."""
    from filelock import FileLock
    from .config import DATA
    from .agent_models import AgentTurn,ToolCall
    from . import db,media
    import uuid,time
    if db.cancelled(job):raise media.Cancelled()
    if len(db.encode(messages))+len(db.encode(schemas))>70000:raise ValueError('Assistant context is too large; narrow the request')
    if not 128<=max_tokens<=2048:raise ValueError('Invalid assistant response limit')
    if chat_provider()=='cloud':
        answer=cloud_turn(messages,schemas,max_tokens)
        if on_text and answer.text:on_text(answer.text)
        return answer
    model=local_model()
    if not model:raise ValueError('Select an installed Ollama model in Settings')
    body={'model':model,'messages':messages,'tools':schemas,'stream':on_text is not None,'think':False,'keep_alive':-1,'options':{'num_predict':max_tokens,'num_ctx':8192,'temperature':0}}
    started=time.monotonic();first_text=None
    try:
        with FileLock(DATA/'model.lock',timeout=0), httpx.Client(trust_env=False,timeout=httpx.Timeout(120,connect=5)) as client:
            if on_text is None:
                response=client.post(ollama_url()+'/api/chat',json=body)
                response.raise_for_status()
                if len(response.content)>200000:raise ValueError('Model tool response exceeded the size limit')
                value=response.json()
            else:
                text='';call_items=[];value={};size=0
                with client.stream('POST',ollama_url()+'/api/chat',json=body) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if db.cancelled(job):raise media.Cancelled()
                        if not line:continue
                        size+=len(line.encode('utf-8'))
                        if size>200000:raise ValueError('Model tool response exceeded the size limit')
                        try:chunk=json.loads(line)
                        except json.JSONDecodeError:raise ValueError('Local model returned an invalid response stream') from None
                        if not isinstance(chunk,dict) or chunk.get('error'):raise ValueError('Local model returned an unusable response stream')
                        if type(chunk.get('done')) is not bool:raise ValueError('Invalid model completion flag')
                        message=chunk.get('message',{})
                        if not isinstance(message,dict):raise ValueError('Invalid model message')
                        content=message.get('content') or ''
                        if not isinstance(content,str):raise ValueError('Invalid model text')
                        if content:
                            if first_text is None:first_text=time.monotonic()-started
                            text+=content
                            if len(text)>12000:raise ValueError('Model reply exceeded the size limit')
                            on_text(text)
                        items=message.get('tool_calls') or []
                        if not isinstance(items,list):raise ValueError('Invalid model tool calls')
                        call_items.extend(items)
                        if len(call_items)>12:raise ValueError('Model tool response exceeded the tool limit')
                        if chunk.get('done') is True:
                            value=chunk
                            value['message']={'content':text,'tool_calls':call_items}
                            break
    except httpx.HTTPStatusError as error:
        # Qwen sometimes writes a tool call Ollama cannot parse (seen with Windows paths such as D:\Notes\ideas.txt).
        # One retry with forward slashes in the newest user turn, which Windows paths accept too.
        if error.response.status_code==500 and not retried:
            last=max((i for i,m in enumerate(messages) if m.get('role')=='user'),default=None)
            if last is not None and '\\' in messages[last].get('content',''):
                fixed=messages[:last]+[dict(messages[last],content=messages[last]['content'].replace('\\','/'))]+messages[last+1:]
                return agent_turn(fixed,schemas,job=job,on_text=on_text,max_tokens=max_tokens,retried=True)
        raise ValueError('Local model request failed. Start Ollama or choose an installed tool-capable model, then retry') from None
    except httpx.HTTPError:raise ValueError('Local model request failed. Start Ollama or choose an installed tool-capable model, then retry') from None
    if db.cancelled(job):raise media.Cancelled()
    if not isinstance(value,dict) or value.get('done') is not True or value.get('error'):raise ValueError('Local model did not finish a usable tool response')
    message=value.get('message') or {};calls=[]
    if not isinstance(message,dict) or not isinstance(message.get('content') or '',str) or not isinstance(message.get('tool_calls') or [],list):raise ValueError('Invalid model message')
    if len(message.get('tool_calls') or [])>12 or len(message.get('content') or '')>12000:raise ValueError('Model tool response exceeded the size limit')
    for item in message.get('tool_calls') or []:
        if not isinstance(item,dict) or not isinstance(item.get('function'),dict):raise ValueError('Invalid model tool call')
        function=item['function']
        calls.append(ToolCall(id=str(item.get('id') or uuid.uuid4().hex),name=function.get('name',''),arguments=function.get('arguments',{})))
    counts={k:value.get(v) if type(value.get(v))==int and value[v]>=0 else None for k,v in [('input_tokens','prompt_eval_count'),('output_tokens','eval_count')]}
    timing={'model_seconds':round(time.monotonic()-started,3)}
    if first_text is not None:timing['first_text_seconds']=round(first_text,3)
    for name,field in [('load_seconds','load_duration'),('prompt_seconds','prompt_eval_duration'),('generation_seconds','eval_duration')]:
        if type(value.get(field))==int and value[field]>=0:timing[name]=round(value[field]/1e9,3)
    return AgentTurn(text=message.get('content') or '',calls=calls,usage=counts,timing=timing)



def _wikipedia(client,query):
    response=client.get('https://en.wikipedia.org/w/api.php',params={'action':'opensearch','search':query,'limit':5,'namespace':0,'format':'json'},headers={'User-Agent':'NinjaAssistant/0.1 (local user-requested research)'})
    response.raise_for_status()
    if len(response.content)>1000000:raise ValueError('Search response exceeds size limit')
    value=response.json()
    return {'provider':'Wikipedia','sources':[{'title':title,'url':url} for title,url in zip(value[1],value[3])]} if value[3] else None


def _duckduckgo(client,query):
    import re
    from html import unescape
    from urllib.parse import parse_qs,urlsplit
    response=client.get('https://html.duckduckgo.com/html/',params={'q':query},headers={'User-Agent':'NinjaAssistant/0.1 (local user-requested research)'})
    response.raise_for_status()
    if len(response.content)>2000000:raise ValueError('Search response exceeds size limit')
    def text(markup):return ' '.join(unescape(re.sub(r'<[^>]+>','',markup)).split())
    sources=[]
    # Result links are DuckDuckGo redirects carrying the address in uddg; ads use another link form and are skipped.
    for block in response.text.split('class="result results_links')[1:]:
        link=re.search(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>',block,re.S)
        target=(parse_qs(urlsplit(unescape(link[1])).query).get('uddg') or [''])[0] if link else ''
        if not target.startswith('https://'):continue
        snippet=re.search(r'class="result__snippet"[^>]*>(.*?)</a>',block,re.S)
        sources.append({'title':text(link[2]) or 'Source','url':target,'snippet':text(snippet[1])[:400] if snippet else ''})
    return {'provider':'DuckDuckGo','sources':sources[:8]} if sources else None


def _bing(client,query):
    import xml.etree.ElementTree as ET
    response=client.get('https://www.bing.com/search',params={'q':query,'format':'rss'},headers={'User-Agent':'NinjaAssistant/0.1 (local user-requested research)'})
    response.raise_for_status()
    if len(response.content)>1000000:raise ValueError('Search response exceeds size limit')
    items=ET.fromstring(response.content).findall('./channel/item')
    sources=[{'title':item.findtext('title') or 'Source','url':item.findtext('link'),'snippet':(item.findtext('description') or '')[:300]} for item in items if item.findtext('link')][:6]
    return {'provider':'Bing RSS','sources':sources} if sources else None


def search_sources(query,web_first=False):
    """Bounded discovery. Topic lookups try Wikipedia first; current-events research (web_first) tries the web first."""
    import xml.etree.ElementTree as ET
    query=query.strip()
    if not query or len(query)>200:raise ValueError('Use a short public research query')
    with httpx.Client(timeout=15,follow_redirects=False,trust_env=False) as client:
        for provider in ((_duckduckgo,_bing,_wikipedia) if web_first else (_wikipedia,_duckduckgo,_bing)):
            try:
                found=provider(client,query)
                if found:return found
            except (httpx.HTTPError,ET.ParseError,ValueError,IndexError,KeyError):pass
    raise ValueError('Public search is unavailable. Supply an accessible public HTTPS source link and retry.')


def _bing_news(client,query):
    import xml.etree.ElementTree as ET
    from urllib.parse import parse_qs,urlsplit
    response=client.get('https://www.bing.com/news/search',params={'q':query,'format':'rss'},headers={'User-Agent':'NinjaAssistant/0.1 (local user-requested research)'})
    response.raise_for_status()
    if len(response.content)>1000000:raise ValueError('Search response exceeds size limit')
    sources=[]
    for item in ET.fromstring(response.content).findall('./channel/item'):
        # News links are Bing click-throughs; the article address is in their url parameter.
        target=(parse_qs(urlsplit(item.findtext('link') or '').query).get('url') or [''])[0]
        if target.startswith('https://'):sources.append({'title':item.findtext('title') or 'Source','url':target,'snippet':(item.findtext('description') or '')[:400],'date':item.findtext('pubDate') or ''})
    from email.utils import parsedate_to_datetime
    def when(source):
        try:return parsedate_to_datetime(source['date']).timestamp()
        except (TypeError,ValueError):return 0
    # Newest first: "latest" questions otherwise get last year's articles.
    sources.sort(key=when,reverse=True)
    return {'provider':'Bing News RSS','sources':sources[:6]} if sources else None


def top_news():
    """India top stories from Google News' public RSS: headline, outlet and time. A query such as "today's news"
    sent to a search engine returned unrelated items (a vaccine story, a football transfer, a quote)."""
    import xml.etree.ElementTree as ET
    with httpx.Client(timeout=15,follow_redirects=False,trust_env=False) as client:
        response=client.get('https://news.google.com/rss',params={'hl':'en-IN','gl':'IN','ceid':'IN:en'},headers={'User-Agent':'NinjaAssistant/0.1 (local user-requested research)'})
    response.raise_for_status()
    if len(response.content)>2000000:raise ValueError('News response exceeds size limit')
    items=ET.fromstring(response.content).findall('./channel/item')[:8]
    return {'provider':'Google News top stories (India)','sources':[{'title':i.findtext('title') or '','date':i.findtext('pubDate') or ''} for i in items if i.findtext('title')]}


def web_search(query,news=False):
    """Web results first; news=True asks Bing News for recent, dated articles."""
    if not news:return search_sources(query,web_first=True)
    import xml.etree.ElementTree as ET
    with httpx.Client(timeout=15,follow_redirects=False,trust_env=False) as client:
        try:
            found=_bing_news(client,query.strip()[:200])
            if found:return found
        except (httpx.HTTPError,ET.ParseError,ValueError):pass
    return search_sources(query,web_first=True)


def private_reply(messages):
    # Local inference only: no tools, archive, memory retrieval or token ledger.
    from filelock import FileLock
    from .config import DATA
    from . import db
    if db.stopped():raise ValueError('Emergency stop is active')
    if len(db.encode(messages))>24000:raise ValueError('Private context exceeds 24,000 characters; clear the session')
    model=local_model()
    if not model:raise ValueError('Select an installed local model in Settings')
    payload={'model':model,'messages':[{'role':'system','content':'You are Jarvis in a private conversation. No tools or external access are available. Never claim to save memories or perform actions.'},*messages],'stream':False,'think':False,'keep_alive':0,'options':{'num_predict':1024}}
    try:
        with FileLock(DATA/'model.lock',timeout=0),httpx.Client(trust_env=False,timeout=httpx.Timeout(120,connect=5)) as client:
            response=client.post(ollama_url()+'/api/chat',json=payload);response.raise_for_status()
            if len(response.content)>200000:raise ValueError('Private model response exceeds size limit')
            value=response.json()
    except httpx.HTTPError:raise ValueError('Local private reply failed; start Ollama or select an installed model') from None
    text=value.get('message',{}).get('content','')
    if not value.get('done') or not text.strip():raise ValueError('Local model returned no complete private reply')
    return {'text':text,'usage':{'input_tokens':value.get('prompt_eval_count'),'output_tokens':value.get('eval_count')}}
