"""Validated contracts for the local assistant; no credentials in model inputs."""
from typing import Literal,Annotated
from pydantic import BaseModel,ConfigDict,Field

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Scope(Strict):
    kind:Literal['personal','workspace','channel']='personal'
    id:str=Field(default='me',min_length=1,max_length=100)

class ToolContext(Strict):
    task_id:str
    scopes:list[Scope]=Field(max_length=10)
    plan_revision:int=Field(ge=0)
    idempotency_key:str
    approval_id:str|None=None
    private:bool=False
    lease_job:str|None=None
    lease_attempt:int|None=None
    tainted:bool=False

class ToolCall(Strict):
    id:str=Field(min_length=1,max_length=120)
    name:str=Field(min_length=1,max_length=100)
    arguments:dict

class AgentTurn(Strict):
    text:str=Field(default='',max_length=12000)
    calls:list[ToolCall]=Field(default_factory=list,max_length=12)
    usage:dict=Field(default_factory=dict)
    timing:dict=Field(default_factory=dict)

class Request(Strict):
    spoken:bool=False
    response_mode:Literal['assistant','companion']='assistant'
    language:Literal['auto','en','hi','hinglish']='auto'
    text:str=Field(min_length=1,max_length=6000)
    scopes:list[Scope]=Field(default_factory=lambda:[Scope()],min_length=1,max_length=10)
    documents:list[Annotated[str,Field(min_length=1,max_length=2000)]]=Field(default_factory=list,max_length=10)
    request_key:str=Field(min_length=8,max_length=100,pattern=r'^[\w-]+$')

class Instruction(Strict):
    spoken:bool|None=None
    response_mode:Literal['assistant','companion']|None=None
    language:Literal['auto','en','hi','hinglish']|None=None
    text:str=Field(min_length=1,max_length=3000)
    expected_revision:int=Field(ge=0)
    request_key:str=Field(min_length=8,max_length=100,pattern=r'^[\w-]+$')

