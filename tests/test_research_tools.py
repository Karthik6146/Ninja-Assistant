import contextlib
import httpx
import pytest
from ninja import research_tools as rt


def fake(routes):
    """httpx client whose responses come from {path prefix: json}; records requested URLs."""
    seen=[]
    def handler(request):
        seen.append(str(request.url))
        for prefix,body in routes.items():
            if request.url.path.startswith(prefix):return httpx.Response(200,json=body)
        return httpx.Response(404,json={})
    return (lambda:httpx.Client(transport=httpx.MockTransport(handler))),seen


def test_weather_reports_place_now_and_requested_day(monkeypatch):
    client,seen=fake({'/v1/search':{'results':[{'name':'Noida','admin1':'Uttar Pradesh','country':'India','latitude':28.58,'longitude':77.33,'timezone':'Asia/Kolkata'}]},
        '/v1/forecast':{'current':{'temperature_2m':24.1,'apparent_temperature':25.0,'relative_humidity_2m':61,'precipitation':0,'weather_code':2,'wind_speed_10m':9.4},
                        'daily':{'time':['2026-10-28','2026-10-29'],'temperature_2m_max':[30.2,29.0],'temperature_2m_min':[18.4,17.9],'precipitation_probability_max':[5,40],'weather_code':[2,61]}}})
    monkeypatch.setattr(rt,'client',client)
    data=rt.weather(rt.Weather(place='Noida',day='tomorrow'),10,None)['data']
    assert data['place']=='Noida, Uttar Pradesh, India'
    assert data['now']['temperature_c']==24.1 and data['now']['conditions']=='Partly cloudy'
    assert data['day']=={'date':'2026-10-29','max_c':29.0,'min_c':17.9,'rain_chance_percent':40,'conditions':'Light rain'}
    assert any('api.open-meteo.com' in url for url in seen)


def test_weather_unknown_place_is_an_honest_error(monkeypatch):
    client,_=fake({'/v1/search':{}})
    monkeypatch.setattr(rt,'client',client)
    with pytest.raises(ValueError,match='find'):rt.weather(rt.Weather(place='Nowhereville'),10,None)


def test_deep_research_reads_pages_and_numbers_only_read_sources(monkeypatch):
    monkeypatch.setattr(rt.adapters,'web_search',lambda q,news=False:{'provider':'Bing RSS','sources':[{'title':'A','url':'https://a.test/1'},{'title':'B','url':'https://b.test/2'},{'title':'C','url':'https://c.test/3','snippet':'Summary of C long enough to be useful evidence for the answer.'}]})
    def extract(url):
        if 'b.test' in url:raise ValueError('blocked')
        return {'url':url,'excerpt':('Body of '+url+' ')*20 if 'a.test' in url else 'C','status':'retrieved'}
    monkeypatch.setattr(rt.adapters,'extract',extract)
    data=rt.deep(rt.Research(query='best mic under 5000'),60,None)['data']
    assert [s['n'] for s in data['sources']]==[1,2]
    assert [s['url'] for s in data['sources']]==['https://a.test/1','https://c.test/3']
    assert data['sources'][0]['read']=='page' and data['sources'][1]=={'n':2,'title':'C','url':'https://c.test/3','date':'','read':'summary','excerpt':'Summary of C long enough to be useful evidence for the answer.'}
    assert data['unread']==['https://b.test/2']


def test_youtube_search_uses_a_connected_channel(monkeypatch):
    monkeypatch.setattr(rt.auth,'channels',lambda:[{'id':'UC1','connection':'c1','connected':True}])
    monkeypatch.setattr(rt.auth,'target',lambda connection,channel:contextlib.nullcontext())
    calls=[]
    def api(method,resource,**kw):
        calls.append(resource)
        if resource=='search':return {'items':[{'id':{'videoId':'v1'}}]}
        return {'items':[{'id':'v1','snippet':{'title':'Valorant tips','channelTitle':'Pro','publishedAt':'2026-10-01T00:00:00Z'},'statistics':{'viewCount':'12000','likeCount':'900'},'contentDetails':{'duration':'PT45S'}}]}
    monkeypatch.setattr(rt.auth,'api',api)
    data=rt.youtube(rt.YouTubeQuery(query='Valorant tips'),20,None)['data']
    assert calls==['search','videos'] and data['videos'][0]=={'title':'Valorant tips','channel':'Pro','views':12000,'likes':900,'published':'2026-10-01','duration':'PT45S','url':'https://www.youtube.com/watch?v=v1'}


def test_youtube_search_without_channel_says_how_to_connect(monkeypatch):
    monkeypatch.setattr(rt.auth,'channels',lambda:[])
    with pytest.raises(ValueError,match='Connect'):rt.youtube(rt.YouTubeQuery(query='x'),20,None)


def test_new_tools_are_registered_read_only():
    from ninja import tools,assistant_tools  # noqa: F401
    for name in ('weather.now','research.deep','youtube.search'):
        tool=tools.REGISTRY[name];assert tool.effect=='routine' and tool.permission=='research.read'
