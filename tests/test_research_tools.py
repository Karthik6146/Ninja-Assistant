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


def test_new_tools_are_registered_read_only():
    from ninja import tools,assistant_tools  # noqa: F401
    for name in ('weather.now','research.deep'):
        tool=tools.REGISTRY[name];assert tool.effect=='routine' and tool.permission=='research.read'


def test_relevant_keeps_matching_paragraphs_in_page_order():
    page='\n'.join(['Menu Home About Contact Subscribe to our newsletter today', 'A heat pump moves heat from outside air into the house in winter.',
                    'Our company was founded in 1990 and has many happy customers.', 'In summer the heat pump reverses and moves heat out of the house.'])
    kept=rt.relevant(page,'how does a heat pump work',limit=140)
    assert kept.splitlines()==['A heat pump moves heat from outside air into the house in winter.','In summer the heat pump reverses and moves heat out of the house.']


def test_duckduckgo_results_unwrap_links_and_skip_ads():
    page=('<div class="result results_links result--ad"><a class="result__a" href="https://duckduckgo.com/y.js?ad=1">Ad</a></div>'
          '<div class="result results_links web-result"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.rtings.com%2Fmouse&amp;rut=x">Best <b>Mouse</b></a>'
          '<a class="result__snippet" href="#">The <b>G305</b> &amp; more</a></div>')
    client=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,text=page)))
    assert rt.adapters._duckduckgo(client,'mouse')=={'provider':'DuckDuckGo','sources':[{'title':'Best Mouse','url':'https://www.rtings.com/mouse','snippet':'The G305 & more'}]}


def test_news_is_newest_first():
    rss=('<rss><channel>'+''.join(f'<item><title>{t}</title><link>https://www.bing.com/news/apiclick.aspx?url=https%3A%2F%2Fn.test%2F{t}</link><pubDate>{d}</pubDate></item>'
         for t,d in (('old','Tue, 22 Sep 2026 10:00:00 GMT'),('new','Tue, 27 Oct 2026 10:00:00 GMT')))+'</channel></rss>')
    client=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,text=rss)))
    assert [s['title'] for s in rt.adapters._bing_news(client,'valorant patch')['sources']]==['new','old']


def test_general_news_uses_top_stories_and_topics_still_search(monkeypatch):
    monkeypatch.setattr(rt.adapters,'top_news',lambda:{'provider':'Google News top stories (India)','sources':[{'title':'Chopper crash in Uttarakhand - The Hindu','date':'Fri, 30 Oct 2026'}]})
    searched=[]
    monkeypatch.setattr(rt.adapters,'web_search',lambda q,news=False:searched.append(q) or {'provider':'x','sources':[{'title':'T','url':'https://t.test/','snippet':'Tech stocks fell sharply after earnings this week.'}]})
    monkeypatch.setattr(rt.adapters,'extract',lambda url:{'excerpt':''})
    data=rt.deep(rt.Research(query="Tell me today's news",recent=True),60,None)['data']
    assert data['sources'][0]=={'n':1,'title':'Chopper crash in Uttarakhand - The Hindu','date':'Fri, 30 Oct 2026'} and searched==[]
    rt.deep(rt.Research(query='technology news today',recent=True),60,None)
    assert searched==['technology news today']
