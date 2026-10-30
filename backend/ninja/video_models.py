"""Versioned, editor-independent supported render contract. No executable model output."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)

class Segment(Strict):
    asset:str=Field(min_length=1,max_length=100,pattern=r'^[\w-]+$')
    start:float=Field(ge=0)
    end:float=Field(gt=0)
    speed:float=Field(default=1,ge=.5,le=2)
    crop_x:float=Field(default=.5,ge=0,le=1)
    crop_y:float=Field(default=.5,ge=0,le=1)
    zoom:float=Field(default=1,ge=1,le=1.3)
    volume:float=Field(default=1,ge=0,le=2)
    @model_validator(mode='after')
    def ordered(self):
        if self.end<=self.start:raise ValueError('Segment end must follow start')
        return self

class AudioCue(Strict):
    project:str=Field(pattern=r'^[a-f0-9]{32}$')
    start:float=Field(ge=0,le=1800)
    source_start:float=Field(default=0,ge=0)
    duration:float=Field(gt=0,le=30)
    volume:float=Field(default=.5,ge=0,le=1)

class EditPlan(Strict):
    version:Literal[1]=1
    revision:int=Field(default=0,ge=0)
    segments:list[Segment]=Field(min_length=1,max_length=40)
    aspect:Literal['9:16','16:9','1:1']='9:16'
    preset:Literal['gaming','podcast','education','cinematic']='education'
    title:str=Field(default='',max_length=120)
    effects:list[Literal['fade','contrast','slow_zoom']]=Field(default_factory=list,max_length=3)
    captions:bool=True
    fps:Literal[24,30,60]=30
    audio_project:str=Field(default='',max_length=32,pattern=r'^(?:[a-f0-9]{32})?$')
    audio_volume:float=Field(default=.15,ge=0,le=1)
    sound_effects:list[AudioCue]=Field(default_factory=list,max_length=20)
    notes:str=Field(default='',max_length=2000)
    @model_validator(mode='after')
    def bounded(self):
        duration=sum((s.end-s.start)/s.speed for s in self.segments)
        if duration>1800:raise ValueError('An edit may be at most 30 minutes')
        if any(c.start+c.duration>duration for c in self.sound_effects):raise ValueError('Sound effect exceeds edit duration')
        return self

PRESETS={
 'gaming':dict(effects=['contrast'],notes='Clean cuts; modest contrast. Manual crop keeps the action visible.'),
 'podcast':dict(effects=[],notes='Speech boundaries, steady framing, readable captions.'),
 'education':dict(effects=['fade'],notes='Restrained fades and clear captions; preserve explanations.'),
 'cinematic':dict(effects=['fade','slow_zoom'],notes='Gentle zoom and fades. Supply licensed audio explicitly.'),
}

class VideoRequest(Strict):
    clips:bool=False
    name:str=Field(default='Video workflow',min_length=1,max_length=100)
    urls:list[str]=Field(default_factory=list,max_length=10)
    projects:list[str]=Field(default_factory=list,max_length=20)
    folder:str=Field(default='',max_length=1000)
    prompt:str=Field(default='',max_length=4000)
    reference:str=Field(default='',max_length=32,pattern=r'^(?:[a-f0-9]{32})?$')
    count:int=Field(default=3,ge=1,le=10)
    seconds:int=Field(default=60,ge=30,le=180)
    preset:Literal['gaming','podcast','education','cinematic']='education'
    aspect:Literal['9:16','16:9','1:1']='9:16'
    destination:str=Field(default='',max_length=1000)
    rights:Literal['owned','licensed','unknown']='unknown'
    captions:bool=True
    language:Literal['auto','en','hi','hinglish']='auto'
    rank_model:bool=True
    @model_validator(mode='after')
    def inputs(self):
        if not (self.urls or self.projects or self.folder):raise ValueError('Supply a YouTube URL, imported footage or an approved folder')
        if self.rights=='unknown':raise ValueError('Confirm ownership or permission to reuse the source footage')
        return self
