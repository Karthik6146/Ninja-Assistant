"""Read-only research tools for Jarvis: weather, multi-page web research and YouTube search.

Reddit is not included: it blocks anonymous access, and its official API needs an app the owner registers.

Nothing here posts, signs in on the user's behalf beyond the already connected YouTube channel, or changes data.
"""
import time
from datetime import datetime,timezone
from typing import Literal
import httpx
from pydantic import Field
from . import adapters,tools
from . import youtube_auth as auth
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


def deep(params,timeout,context):
    """Search, then read up to three pages. Unreadable pages fall back to the feed summary, labelled as such."""
    found=adapters.web_search(params.query,news=params.recent);sources=[];unread=[]
    for item in found['sources'][:6]:
        if len(sources)==3:break
        try:excerpt=(adapters.extract(item['url']).get('excerpt') or '').strip()
        except (ValueError,OSError):excerpt=''
        # Script-heavy pages often yield only their title; a feed summary is better evidence than that.
        kind='page'
        if len(excerpt)<200 and item.get('snippet'):excerpt,kind=item['snippet'],'summary'
        if len(excerpt)<40:unread.append(item['url']);continue
        sources.append({'n':len(sources)+1,'title':item.get('title') or item['url'],'url':item['url'],'date':item.get('date',''),'read':kind,'excerpt':excerpt[:2400]})
    if not sources:raise ValueError('No search result could be read. Try a different query or give me a public link.')
    return {'data':{'query':params.query,'provider':found['provider'],'sources':sources,'unread':unread,'retrieved':time.time(),
        'instructions':'Answer from these excerpts only and cite them as [1], [2], [3]. Say what the sources do not cover.'}}


class YouTubeQuery(Strict):
    query:str=Field(min_length=1,max_length=160)
    order:Literal['relevance','viewCount','date']='relevance'


def youtube(params,timeout,context):
    connected=[c for c in auth.channels() if c.get('connected')]
    if not connected:raise ValueError('Connect a YouTube channel on the YouTube page first; search uses its read-only access.')
    channel=connected[0]
    try:
        with auth.target(channel['connection'],channel['id']):
            found=auth.api('GET','search',params={'part':'snippet','type':'video','q':params.query,'maxResults':8,'order':params.order,'regionCode':'IN'})
            ids=[x['id']['videoId'] for x in found.get('items',[]) if x.get('id',{}).get('videoId')]
            videos=auth.api('GET','videos',params={'part':'snippet,statistics,contentDetails','id':','.join(ids)}) if ids else {'items':[]}
    except ValueError as error:
        raise ValueError(str(error)+'. If this keeps happening, reconnect the channel on the YouTube page; Google expires sign-ins of apps in testing mode after 7 days.') from None
    def entry(v):
        s,stats=v['snippet'],v.get('statistics',{})
        return {'title':s['title'],'channel':s.get('channelTitle',''),'views':int(stats.get('viewCount',0)),'likes':int(stats.get('likeCount',0)),
                'published':s.get('publishedAt','')[:10],'duration':v.get('contentDetails',{}).get('duration',''),'url':'https://www.youtube.com/watch?v='+v['id']}
    return {'data':{'query':params.query,'videos':[entry(v) for v in videos.get('items',[])],'retrieved':time.time(),
        'limitation':'YouTube search results for region IN; counts are public observations at retrieval time.'}}


for name,schema,callback,seconds in (('weather.now',Weather,weather,20),('research.deep',Research,deep,60),('youtube.search',YouTubeQuery,youtube,30)):
    tools.REGISTRY[name]=tools.Tool(name,schema,Result,'research.read',seconds,callback,'routine',True,True)
