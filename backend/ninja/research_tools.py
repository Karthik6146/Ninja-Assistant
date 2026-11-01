"""Read-only research tools for Jarvis: weather and multi-page web research.

Reddit is not included: it blocks anonymous access, and its official API needs an app the owner registers.

Nothing here posts, signs in on the user's behalf, or changes data.
"""
import re,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from typing import Literal
import httpx
from pydantic import Field
from . import adapters,tools
from .agent_models import Strict

AGENT='NinjaAssistant/0.1 (personal local assistant; read-only)'


class Result(Strict):data:dict


def client():
    return httpx.Client(timeout=15,follow_redirects=False,trust_env=False,headers={'User-Agent':AGENT})


def get_json(url,params=None):
    with client() as c:
        response=c.get(url,params=params)
        response.raise_for_status()
        if len(response.content)>2_000_000:raise ValueError('Response exceeds the size limit')
        return response.json()


# WMO weather interpretation codes used by Open-Meteo.
CODES={0:'Clear sky',1:'Mainly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Freezing fog',51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',
       56:'Freezing drizzle',57:'Freezing drizzle',61:'Light rain',63:'Rain',65:'Heavy rain',66:'Freezing rain',67:'Freezing rain',71:'Light snow',
       73:'Snow',75:'Heavy snow',77:'Snow grains',80:'Rain showers',81:'Rain showers',82:'Violent rain showers',85:'Snow showers',86:'Snow showers',
       95:'Thunderstorm',96:'Thunderstorm with hail',99:'Thunderstorm with hail'}


class Weather(Strict):
    place:str=Field(min_length=1,max_length=100)
    day:Literal['today','tomorrow','day_after']='today'


def weather(params,timeout,context):
    found=get_json('https://geocoding-api.open-meteo.com/v1/search',{'name':params.place.split(',')[0].strip(),'count':1,'language':'en','format':'json'})
    if not found.get('results'):raise ValueError('I could not find a place called '+params.place+'. Try the nearest city name.')
    spot=found['results'][0]
    forecast=get_json('https://api.open-meteo.com/v1/forecast',{'latitude':spot['latitude'],'longitude':spot['longitude'],'timezone':spot.get('timezone','auto'),'forecast_days':3,
        'current':'temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m',
        'daily':'temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code'})
    now,daily=forecast['current'],forecast['daily'];i=['today','tomorrow','day_after'].index(params.day)
    return {'data':{'place':', '.join(v for v in (spot.get('name'),spot.get('admin1'),spot.get('country')) if v),
        'now':{'temperature_c':now['temperature_2m'],'feels_like_c':now['apparent_temperature'],'humidity_percent':now['relative_humidity_2m'],
               'precipitation_mm':now['precipitation'],'wind_kmh':now['wind_speed_10m'],'conditions':CODES.get(now['weather_code'],'Unknown')},
        'day':{'date':daily['time'][i],'max_c':daily['temperature_2m_max'][i],'min_c':daily['temperature_2m_min'][i],
               'rain_chance_percent':daily['precipitation_probability_max'][i],'conditions':CODES.get(daily['weather_code'][i],'Unknown')},
        'source':'Open-Meteo forecast','retrieved':time.time()}}


class Query(Strict):query:str=Field(min_length=1,max_length=200)


class Research(Strict):
    query:str=Field(min_length=1,max_length=200)
    recent:bool=Field(default=False,description='True for news, latest updates, prices, releases or anything time-sensitive')


def relevant(text,query,limit=2400):
    """The paragraphs that mention the most query words, kept in page order, within limit characters."""
    words={w for w in re.findall(r'\w+',query.lower()) if len(w)>2}
    paragraphs=[p.strip() for p in text.split('\n') if len(p.strip())>=40]
    keep=set();size=0
    for i in sorted(range(len(paragraphs)),key=lambda i:-sum(w in paragraphs[i].lower() for w in words)):
        if size+len(paragraphs[i])<=limit:keep.add(i);size+=len(paragraphs[i])
    return '\n'.join(paragraphs[i] for i in sorted(keep))


def read(url):
    try:return (adapters.extract(url).get('excerpt') or '').strip()
    except (ValueError,OSError):return ''


# Words that ask for news without naming a topic ("tell me today's news", "aaj ki khabar batao").
GENERAL_NEWS={'tell','me','today','todays','s','the','top','latest','news','headlines','headline','what','is','are','whats','in','of','aaj','ki','ka','kya','hai','khabar','khabrein','batao','give','any','new','current','india','indian'}


def deep(params,timeout,context):
    """Search, then read the top pages in parallel and keep three. Unreadable pages fall back to the search snippet, labelled as such."""
    if params.recent and set(re.findall(r'[a-z]+',params.query.lower()))<=GENERAL_NEWS:
        try:
            found=adapters.top_news()
            return {'data':found|{'query':params.query,'retrieved':time.time(),'sources':[dict(s,n=i+1) for i,s in enumerate(found['sources'])],
                    'instructions':'These are headlines only. Name the three or four most important in a sentence or two; offer to look into any of them.'}}
        except (httpx.HTTPError,ValueError):pass  # fall through to a normal news search
    found=adapters.web_search(params.query,news=params.recent);sources=[];unread=[]
    candidates=found['sources'][:6]
    with ThreadPoolExecutor(len(candidates) or 1) as pool:pages=list(pool.map(read,[item['url'] for item in candidates]))
    for item,page in zip(candidates,pages):
        if len(sources)==3:break
        # Script-heavy pages often yield only their title; the search snippet is better evidence than that.
        excerpt,kind=relevant(page,params.query),'page'
        if len(excerpt)<200 and item.get('snippet'):excerpt,kind=item['snippet'],'summary'
        if len(excerpt)<40:unread.append(item['url']);continue
        sources.append({'n':len(sources)+1,'title':item.get('title') or item['url'],'url':item['url'],'date':item.get('date',''),'read':kind,'excerpt':excerpt})
    if not sources:raise ValueError('No search result could be read. Try a different query or give me a public link.')
    return {'data':{'query':params.query,'provider':found['provider'],'sources':sources,'unread':unread,'retrieved':time.time(),
        'instructions':'Answer from these excerpts only and cite them as [1], [2], [3]. Say what the sources do not cover.'}}


for name,schema,callback,seconds in (('weather.now',Weather,weather,20),('research.deep',Research,deep,60)):
    tools.REGISTRY[name]=tools.Tool(name,schema,Result,'research.read',seconds,callback,'routine',True,True)
