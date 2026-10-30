import re
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Caption(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(max_length=2000)
    words: list[dict] = Field(default_factory=list)
    @model_validator(mode='after')
    def timing(self):
        if self.end<=self.start: raise ValueError('Caption end must follow start')
        for w in self.words:
            if not self.start<=w['start']<w['end']<=self.end: raise ValueError('Word outside caption')
        return self

class Clip(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    @model_validator(mode='after')
    def timing(self):
        if self.end<=self.start: raise ValueError('Clip end must follow start')
        return self

class Style(BaseModel):
    font: str = Field(default='Arial', pattern=r'^[\w \-]{1,60}$')
    size: int = Field(default=32,ge=12,le=100)
    colour: str = Field(default='#ffffff',pattern=r'^#[0-9a-fA-F]{6}$')
    outline_colour: str = Field(default='#000000',pattern=r'^#[0-9a-fA-F]{6}$')
    outline: int = Field(default=2,ge=0,le=8)
    placement: Literal['top','middle','bottom']='bottom'
    active_word: bool=False

class EDL(BaseModel):
    version: Literal[1]=1
    revision: int=Field(default=0,ge=0)
    clips: list[Clip] = Field(min_length=1,max_length=50)
    captions: list[Caption]=Field(default_factory=list,max_length=10000)
    aspect: Literal['9:16','16:9','1:1']='9:16'
    crop_x: float=Field(default=0.5,ge=0,le=1)
    crop_y: float=Field(default=0.5,ge=0,le=1)
    volume: float=Field(default=1,ge=0,le=3)
    music: str|None=None
    music_volume: float=Field(default=0.2,ge=0,le=2)
    style: Style=Field(default_factory=Style)

class RenderRequest(BaseModel):
    preview: bool=True
    revision: int
    encoder: Literal['libx264','h264_nvenc','h264_qsv','h264_amf']='libx264'
