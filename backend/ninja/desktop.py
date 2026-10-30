"""Windows desktop control for Jarvis: open installed apps and https sites, media keys, find and open personal files.

No shell fallback and no arbitrary command execution: apps open only from the Start menu list, files only by an
allowlisted document/media type inside the owner's personal folders.
"""
import difflib,json,os,re,subprocess,time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

APPS={'notepad':'notepad.exe','calculator':'calc.exe','explorer':'explorer.exe'}
SETTINGS={'Settings':'ms-settings:','Bluetooth settings':'ms-settings:bluetooth','Wi-Fi settings':'ms-settings:network-wifi','Display settings':'ms-settings:display',
          'Sound settings':'ms-settings:sound','Windows Update':'ms-settings:windowsupdate','Apps settings':'ms-settings:appsfeatures',
          'Notification settings':'ms-settings:notifications','Battery settings':'ms-settings:batterysaver','Storage settings':'ms-settings:storagesense',
          'Default apps settings':'ms-settings:defaultapps','Mouse settings':'ms-settings:mousetouchpad','Camera privacy settings':'ms-settings:privacy-webcam',
          'Microphone privacy settings':'ms-settings:privacy-microphone'}
MEDIA={'play_pause':0xB3,'next':0xB0,'previous':0xB1,'volume_up':0xAF,'volume_down':0xAE,'mute':0xAD}
KINDS={'video':{'.mp4','.mkv','.mov','.avi','.webm','.m4v','.wmv'},'image':{'.jpg','.jpeg','.png','.gif','.webp','.bmp','.heic','.tif','.tiff'},
       'audio':{'.mp3','.wav','.m4a','.flac','.aac','.ogg','.opus'},
       'document':{'.txt','.md','.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.csv','.rtf','.odt','.ods','.odp','.srt','.vtt'}}
# Only these open; programs, scripts, shortcuts and web pages never do, so a misheard request cannot run code.
OPENABLE=set().union(*KINDS.values())
KNOWN_FOLDERS={'Desktop':'B4BFCC3A-DB2C-424C-B029-7FE99A87C641','Documents':'FDD39AD0-238F-46AF-ADB4-6C85480369C7','Downloads':'374DE290-123F-4565-9164-39C4925E467B',
               'Videos':'18989B1D-99B5-455B-841C-AB7C74E4DDFC','Pictures':'33E28130-4E1E-4676-835A-98395C3BC3BB','Music':'4BD8D571-6D19-48D3-BE97-422220080E43'}
_apps={'at':0.0,'items':[]}
# Shells and admin tools can run anything, so a voice request never opens them.
BLOCKED=re.compile(r'powershell|command prompt|\bcmd\b|terminal|registry|regedit|\bwsl\b|\bbash\b|ubuntu|group policy|gpedit|task scheduler|services\.msc',re.I)


def session_active():
    if os.name!='nt':return False
    import ctypes
    from ctypes import wintypes
    session=wintypes.DWORD()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.ProcessIdToSessionId.argtypes=[wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    if not kernel.ProcessIdToSessionId(os.getpid(),ctypes.byref(session)):return False
    wts=ctypes.WinDLL('wtsapi32',use_last_error=True);buffer=ctypes.c_void_p();size=wintypes.DWORD()
    wts.WTSQuerySessionInformationW.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_int,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(wintypes.DWORD)]
    wts.WTSFreeMemory.argtypes=[ctypes.c_void_p]
    if not wts.WTSQuerySessionInformationW(None,session,8,ctypes.byref(buffer),ctypes.byref(size)):return False
    try:return size.value>=ctypes.sizeof(ctypes.c_int) and ctypes.cast(buffer,ctypes.POINTER(ctypes.c_int)).contents.value==0
    finally:wts.WTSFreeMemory(buffer)

def interactive():
    if os.name!='nt' or not session_active():return False
    import ctypes
    from ctypes import wintypes
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.OpenInputDesktop.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    user.OpenInputDesktop.restype=wintypes.HANDLE
    user.CloseDesktop.argtypes=[wintypes.HANDLE]
    user.GetUserObjectInformationW.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    handle=user.OpenInputDesktop(0,False,1)
    if not handle:return False
    try:
        name=ctypes.create_unicode_buffer(256);needed=wintypes.DWORD()
        return bool(user.GetUserObjectInformationW(handle,2,name,ctypes.sizeof(name),ctypes.byref(needed))) and name.value.lower()=='default'
    finally:user.CloseDesktop(handle)

def require_desktop():
    if not interactive():raise ValueError('Please unlock Windows and run Ninja in your interactive user session')


def launch(target):
    if target.startswith('shell:AppsFolder\\'):
        subprocess.Popen([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'explorer.exe'),target],shell=False,close_fds=True)
    else:os.startfile(target)


def start_apps():
    """Installed apps exactly as the Start menu lists them (classic and Store apps), cached for ten minutes."""
    if time.monotonic()-_apps['at']<600 and _apps['items']:return _apps['items']
    try:
        out=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command','Get-StartApps | ConvertTo-Json -Compress'],capture_output=True,timeout=20,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0).stdout.decode('utf-8','replace')
        items=json.loads(out or '[]');items=[items] if isinstance(items,dict) else items
        items=[{'Name':str(i['Name']),'AppID':str(i['AppID'])} for i in items if i.get('Name') and i.get('AppID')]
    except (OSError,ValueError,subprocess.SubprocessError,KeyError):items=[]
    _apps.update(at=time.monotonic(),items=items);return items


def normal(text):return re.sub(r'[^a-z0-9]+',' ',text.lower()).strip()


def find_app(name):
    query=normal(name)
    if not query:raise ValueError('Say which app to open')
    if BLOCKED.search(name):raise ValueError('Jarvis does not open shells or admin tools; open them yourself if you need them')
    candidates=[a for a in start_apps() if not re.search(r'\buninstall',a['Name'],re.I) and not BLOCKED.search(a['Name'])]+[{'Name':k,'AppID':v} for k,v in SETTINGS.items()]
    def score(app):
        title=normal(app['Name']);words=title.split()
        if title==query:return 100
        if title.startswith(query):return 90
        if all(any(w.startswith(q) for w in words) for q in query.split()):return 80
        ratio=difflib.SequenceMatcher(None,query,title).ratio()
        return 60*ratio if ratio>=.8 else 0
    ranked=sorted(((score(a),a) for a in candidates),key=lambda x:-x[0])
    if ranked and ranked[0][0]>0:return ranked[0][1]
    near=sorted(candidates,key=lambda a:-max((difflib.SequenceMatcher(None,q,w).ratio() for q in query.split() for w in normal(a['Name']).split()),default=0))[:3]
    raise ValueError('No installed app matches "'+name+'". Closest: '+', '.join(a['Name'] for a in near))


def open_app(app):
    require_desktop()
    found=find_app(app)
    launch(found['AppID'] if found['AppID'].startswith('ms-settings:') else 'shell:AppsFolder\\'+found['AppID'])
    return {'app':found['Name'],'launched':True,'verification':'Launch accepted by Windows. The window itself was not inspected.'}


def open_url(url):
    require_desktop()
    url=url.strip()
    if re.fullmatch(r'[\w-]+(\.[\w-]+)+(/\S*)?',url):url='https://'+url
    parts=urlsplit(url)
    if len(url)>2000 or parts.scheme!='https' or not parts.hostname or parts.username or parts.password:
        raise ValueError('Only https web addresses can be opened, for example youtube.com')
    launch(url);return {'url':url,'opened':True,'verification':'Handed to the default browser.'}


def press(key):
    import ctypes
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.keybd_event(key,0,0,0);user.keybd_event(key,0,2,0)


def media(action,steps=1):
    require_desktop()
    if action not in MEDIA:raise ValueError('Choose play_pause, next, previous, volume_up, volume_down or mute')
    count=max(1,min(10,steps)) if action.startswith('volume_') else 1
    for _ in range(count):press(MEDIA[action])
    return {'action':action,'presses':count,'verification':'Media key sent to Windows; each volume step is about 2%.'}


def known_folder(guid):
    import ctypes,uuid
    from ctypes import wintypes
    class GUID(ctypes.Structure):_fields_=[('d1',wintypes.DWORD),('d2',wintypes.WORD),('d3',wintypes.WORD),('d4',ctypes.c_ubyte*8)]
    raw=uuid.UUID(guid).bytes_le;value=GUID.from_buffer_copy(raw);path=ctypes.c_wchar_p()
    shell=ctypes.WinDLL('shell32');ole=ctypes.WinDLL('ole32')
    if shell.SHGetKnownFolderPath(ctypes.byref(value),0,None,ctypes.byref(path))!=0:return None
    try:return Path(path.value)
    finally:ole.CoTaskMemFree(path)


def personal_folders():
    """Desktop, Documents, Downloads, Videos, Pictures and Music (OneDrive-redirected ones included) plus approved roots."""
    from .config import ROOTS
    found=[]
    for name,guid in KNOWN_FOLDERS.items():
        try:path=known_folder(guid) if os.name=='nt' else None
        except OSError:path=None
        found.append(path or Path.home()/name)
    found+=list(ROOTS)
    unique=[]
    for path in found:
        if path.is_dir() and path.resolve() not in unique:unique.append(path.resolve())
    return unique


def hidden(entry):
    if entry.name.startswith(('.','$')) or entry.name in ('node_modules','AppData'):return True
    try:return bool(getattr(entry.stat(follow_symlinks=False),'st_file_attributes',0)&0x2)
    except OSError:return True


def find_files(query,kind='any'):
    words=normal(query).split()
    if not words:raise ValueError('Say part of the file name')
    wanted=KINDS.get(kind);results=[];seen=0;started=time.monotonic();truncated=False
    folders=personal_folders()
    for root in folders:
        stack=[(root,0)]
        while stack:
            folder,depth=stack.pop()
            try:entries=list(os.scandir(folder))
            except OSError:continue
            for entry in entries:
                seen+=1
                # ponytail: bounded name walk (40k entries / 4 s); an indexed search is the upgrade if folders grow large.
                if seen>40000 or time.monotonic()-started>4:truncated=True;break
                if hidden(entry):continue
                if entry.is_dir(follow_symlinks=False):
                    if depth<6:stack.append((Path(entry.path),depth+1))
                    continue
                if wanted and Path(entry.name).suffix.lower() not in wanted:continue
                title=normal(entry.name)
                if all(w in title for w in words):
                    info=entry.stat();results.append({'name':entry.name,'path':entry.path,'folder':root.name,'size_mb':round(info.st_size/1048576,2),
                        'modified':datetime.fromtimestamp(info.st_mtime).strftime('%Y-%m-%d %H:%M'),'_m':info.st_mtime})
            if truncated:break
        if truncated:break
    results.sort(key=lambda r:-r.pop('_m'))
    return {'query':query,'files':results[:15],'total':len(results),'searched':[f.name for f in folders],'truncated':truncated}


def open_file(path):
    require_desktop()
    try:target=Path(path).resolve(strict=True)
    except OSError:raise ValueError('That file or folder no longer exists') from None
    if not any(target==root or target.is_relative_to(root) for root in personal_folders()):
        raise ValueError('Jarvis only opens items inside your personal folders (Desktop, Documents, Downloads, Videos, Pictures, Music)')
    if target.is_file() and target.suffix.lower() not in OPENABLE:
        raise ValueError('Jarvis does not open programs, scripts or shortcuts. Open it yourself if you trust it.')
    launch(str(target));return {'opened':str(target),'kind':'folder' if target.is_dir() else target.suffix.lower(),'verification':'Opened with its default Windows app.'}
