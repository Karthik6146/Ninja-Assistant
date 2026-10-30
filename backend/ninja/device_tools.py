"""Jarvis tools for controlling this PC: apps, websites, media keys, and personal files (find by name, open safe types)."""
from typing import Literal
from pydantic import Field
from . import desktop,tools
from .agent_models import Strict


class Result(Strict):data:dict
class AppInput(Strict):app:str=Field(min_length=1,max_length=80,description='App or Settings page name as the user said it, e.g. Chrome, VLC, WhatsApp, Bluetooth settings')
class UrlInput(Strict):url:str=Field(min_length=3,max_length=2000,description='https address or bare domain, e.g. youtube.com')
class MediaInput(Strict):
    action:Literal['play_pause','next','previous','volume_up','volume_down','mute']
    steps:int=Field(default=1,ge=1,le=10,description='Volume steps of about 2% each')
class FindInput(Strict):
    query:str=Field(min_length=1,max_length=120,description='Words from the file name')
    kind:Literal['any','video','image','audio','document']='any'
class OpenInput(Strict):path:str=Field(min_length=1,max_length=2000,description='Exact path returned by file.find, or a personal folder')


for name,schema,run,permission,replay in (
    ('app.open',AppInput,lambda p,timeout,context:{'data':desktop.open_app(p.app)},'app.open',False),
    ('web.open',UrlInput,lambda p,timeout,context:{'data':desktop.open_url(p.url)},'app.open',False),
    ('media.control',MediaInput,lambda p,timeout,context:{'data':desktop.media(p.action,p.steps)},'device.control',False),
    ('file.find',FindInput,lambda p,timeout,context:{'data':desktop.find_files(p.query,p.kind)},'files.personal',True),
    ('file.open',OpenInput,lambda p,timeout,context:{'data':desktop.open_file(p.path)},'files.personal',False)):
    tools.REGISTRY[name]=tools.Tool(name,schema,Result,permission,15,run,'routine',True,replay)
