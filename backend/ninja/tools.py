from dataclasses import dataclass
from typing import Callable
from pydantic import BaseModel
from . import db
from pydantic import Field

@dataclass
class Tool:
    name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    permission: str
    timeout: int
    execute: Callable
    effect: str = 'restricted'
    scoped: bool = False
    replay_safe: bool = False

REGISTRY: dict[str,Tool]={}

def invoke(name, args, granted: set[str], *, context=None):
    if db.stopped(): raise ValueError('Emergency stop is active')
    tool=REGISTRY.get(name)
    if not tool: raise ValueError('Unknown tool')
    if context is None:
        if name not in ('system.monitor','system.large_files'): raise ValueError('Assistant context required')
        if tool.permission not in granted: raise ValueError('Permission denied')
    if not isinstance(args,dict) or args.keys()-tool.input_schema.model_fields.keys(): raise ValueError('Unsupported tool arguments')
    params=tool.input_schema.model_validate(args)
    if context is not None:
        from .permissions import authorize
        authorize(name,params.model_dump(),context)
    db.audit('tool.started',{'name':name})
    # Implementations must enforce their timeout on each subprocess/network request.
    try:
        result=tool.output_schema.model_validate(tool.execute(params,timeout=tool.timeout,**({'context':context} if tool.scoped else {})))
        db.audit('tool.completed',{'name':name})
        return result.model_dump()
    except Exception:
        db.audit('tool.failed',{'name':name}); raise

class MonitorInput(BaseModel):
    process_limit: int=Field(default=200,ge=1,le=200)

class MonitorOutput(BaseModel):
    cpu_percent: float
    memory: dict
    disk: dict
    processes: list[dict]

def monitor(params,timeout):
    import psutil
    import time
    from .config import DATA
    start=time.monotonic();processes=[]
    for process in psutil.process_iter(['name']):
        if time.monotonic()-start>timeout: raise TimeoutError('Process inspection timeout')
        processes.append({'pid':process.pid,'name':process.info['name']})
        if len(processes)>=params.process_limit: break
    return {'cpu_percent':psutil.cpu_percent(interval=.1),'memory':psutil.virtual_memory()._asdict(),'disk':psutil.disk_usage(str(DATA))._asdict(),'processes':processes}

REGISTRY['system.monitor']=Tool('system.monitor',MonitorInput,MonitorOutput,'system.read',5,monitor,'routine',False,True)

class FileScanInput(BaseModel): root: str
class FileScanOutput(BaseModel):
    files: list[dict]
    visited: int
    truncated: bool

def large_files(params,timeout):
    import os,time,heapq
    from pathlib import Path
    from .config import ROOTS
    root=Path(params.root).resolve(strict=True)
    if root not in ROOTS or not root.is_dir(): raise ValueError('Select an exact configured NINJA_ROOTS folder')
    started=time.monotonic();heap=[];visited=0;truncated=False
    for folder,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if not (Path(folder)/d).is_symlink()]
        for name in names:
            if time.monotonic()-started>timeout or visited>=10000:
                truncated=True;break
            path=Path(folder)/name;visited+=1
            try:
                if path.is_symlink() or not path.resolve().is_relative_to(root): continue
                size=path.stat().st_size
                heapq.heappush(heap,(size,str(path)))
                if len(heap)>50:heapq.heappop(heap)
            except OSError:continue
        if truncated:break
    return {'files':[{'path':path,'bytes':size} for size,path in sorted(heap,reverse=True)],'visited':visited,'truncated':truncated}

REGISTRY['system.large_files']=Tool('system.large_files',FileScanInput,FileScanOutput,'system.read',15,large_files,'routine',False,True)
