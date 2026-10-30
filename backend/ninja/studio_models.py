"""User-facing workflow definitions; no executable model-generated actions."""
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from pydantic import Field,model_validator
from .video_models import Strict

class Reference(Strict):
    kind:Literal['video','website','tool']='website'
    url:str=Field(max_length=2000)
    @model_validator(mode='after')
    def public_url(self):
        from urllib.parse import urlsplit
        import ipaddress
        u=urlsplit(self.url)
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):raise ValueError('References need a public HTTPS link')
        if u.hostname=='localhost' or u.hostname.endswith(('.local','.internal')):raise ValueError('Local reference addresses are not supported')
        try:address=ipaddress.ip_address(u.hostname)
        except ValueError:pass
        else:
            if not address.is_global:raise ValueError('Private reference addresses are not supported')
        if self.kind=='video':
            from .video_sources import youtube_id
            youtube_id(self.url)
        return self

class Definition(Strict):
    name:str=Field(default='My video workflow',min_length=1,max_length=100)
    mode:Literal['finished','clips','edit','research','business']='finished'
    channel:str=Field(default='',max_length=100)
    projects:list[str]=Field(default_factory=list,max_length=100)
    folder:str=Field(default='',max_length=1000)
    urls:list[str]=Field(default_factory=list,max_length=5)
    prompt:str=Field(default='',max_length=4000)
    reference:str=Field(default='',max_length=32)
    references:list[Reference]=Field(default_factory=list,max_length=5)
    rights:Literal['owned','licensed','unknown']='unknown'
    count:int=Field(default=3,ge=1,le=10)
    seconds:int=Field(default=60,ge=30,le=180)
    aspect:Literal['9:16','16:9','1:1']='9:16'
    preset:Literal['gaming','podcast','education','cinematic']='education'
    captions:bool=True
    language:Literal['auto','en','hi','hinglish']='auto'
    destination:str=Field(default='',max_length=1000)
    title:str=Field(default='',max_length=100)
    description:str=Field(default='',max_length=4500)
    tags:list[str]=Field(default_factory=list,max_length=30)
    made_for_kids:bool|None=None
    synthetic_media:bool|None=None
    timezone:str='Asia/Kolkata'
    trigger:Literal['manual','daily','folder']='manual'
    time:str=Field(default='19:00',pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')
    publish_at:str=''
    cadence_minutes:int=Field(default=1440,ge=5,le=10080)
    batch:int=Field(default=1,ge=1,le=100)
    policy:Literal['review','private','public','schedule']='review'
    automatic:bool=False
    ai_metadata:bool=False
    youtube_research:bool=False
    research_region:str=Field(default='IN',pattern=r'^[A-Z]{2}$')
    voice:str=Field(default='',max_length=200)
    thumbnail:bool=False
    visuals:Literal['image','video','supplied']='image'
    success:str=Field(default='Save verified outputs and report the result',max_length=1000)
    @model_validator(mode='after')
    def validate_settings(self):
        try:ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('Choose a valid IANA timezone, such as Asia/Kolkata')
        if self.publish_at:
            date=datetime.fromisoformat(self.publish_at.replace('Z','+00:00'))
            if date.tzinfo is None:raise ValueError('Publication time must include a timezone offset')
        if self.trigger=='folder' and self.mode!='finished':raise ValueError('Folder monitoring is available for finished-video workflows')
        return self

class Save(Strict):
    revision:int=Field(default=0,ge=0)
    definition:Definition

class Run(Strict):
    test:bool=True
    key:str=Field(min_length=8,max_length=100)
    reupload:bool=False

class Activation(Strict):
    revision:int=Field(ge=0)
    active:bool
    acknowledged:bool=False
