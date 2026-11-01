"""Windows desktop control for Jarvis: open installed apps and https sites, media keys, find and open personal files.

No shell fallback and no arbitrary command execution: apps open only from the Start menu list, files only by an
allowlisted document/media type inside the owner's personal folders.
"""
import difflib,json,os,re,subprocess,time
from datetime import datetime,timedelta,timezone
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


# A Windows reminder toast (stays until dismissed, plays the reminder sound). Title and text go in environment
# variables and are set as XML text, so nothing the user said is parsed as markup or as PowerShell.
TOAST=("[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]|Out-Null;"
       "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom.XmlDocument,ContentType=WindowsRuntime]|Out-Null;"
       "$x=[Windows.Data.Xml.Dom.XmlDocument]::new();"
       "$x.LoadXml('<toast scenario=\"reminder\"><visual><binding template=\"ToastGeneric\"><text></text><text></text></binding></visual>"
       "<actions><action content=\"Dismiss\" arguments=\"dismiss\" activationType=\"system\"/></actions><audio src=\"ms-winsoundevent:Notification.Reminder\"/></toast>');"
       "$t=$x.GetElementsByTagName('text');$t.Item(0).InnerText=$env:NINJA_TITLE;$t.Item(1).InnerText=$env:NINJA_TEXT;"
       # Windows PowerShell's own app id: toasts need a registered app, and Ninja is not installed as one.
       "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe').Show([Windows.UI.Notifications.ToastNotification]::new($x))")


def notify(title,text):
    subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',TOAST],capture_output=True,timeout=20,check=True,
                   env={**os.environ,'NINJA_TITLE':title[:100],'NINJA_TEXT':text[:300]},creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def powershell(script,env=None,timeout=15):
    out=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',script],capture_output=True,timeout=timeout,
                       env={**os.environ,**(env or {})},creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if out.returncode!=0:raise ValueError('Windows did not allow that: '+out.stderr.decode('utf-8','replace').strip()[:200])
    return out.stdout


def clipboard():
    require_desktop()
    # UTF-8 output so Hindi and emoji survive.
    return powershell('[Console]::OutputEncoding=[Text.Encoding]::UTF8;Get-Clipboard -Raw').decode('utf-8','replace').rstrip('\r\n')


def set_clipboard(text):
    require_desktop()
    powershell('Set-Clipboard -Value $env:NINJA_CLIP',{'NINJA_CLIP':text})


# Physical pixels (DPI-aware), primary screen, scaled to 1600 px wide JPEG; returned as base64 and never written to disk.
SCREENSHOT=("Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
            "Add-Type -Name U -Namespace W -MemberDefinition '[DllImport(\"user32.dll\")] public static extern bool SetProcessDPIAware();';[W.U]::SetProcessDPIAware()|Out-Null;"
            "$b=[Windows.Forms.Screen]::PrimaryScreen.Bounds;$full=New-Object Drawing.Bitmap $b.Width,$b.Height;"
            "[Drawing.Graphics]::FromImage($full).CopyFromScreen($b.Location,[Drawing.Point]::Empty,$b.Size);"
            "$w=[Math]::Min(1600,$b.Width);$small=New-Object Drawing.Bitmap $full,$w,([int]($b.Height*$w/$b.Width));"
            "$m=New-Object IO.MemoryStream;$small.Save($m,[Drawing.Imaging.ImageFormat]::Jpeg);[Convert]::ToBase64String($m.ToArray())")


def screenshot():
    require_desktop()
    return powershell(SCREENSHOT,timeout=20).decode('ascii').strip()


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


# Windows media sessions (the players shown in the volume flyout): real pause/resume and what is playing.
# The play/pause key only toggles, so "pause it" with nothing playing started music.
SESSIONS=r"""[Console]::OutputEncoding=[Text.Encoding]::UTF8;Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask=([System.WindowsRuntimeSystemExtensions].GetMethods()|Where-Object{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0]
function Await($op,[Type]$type){$t=$asTask.MakeGenericMethod($type).Invoke($null,@($op));$t.Wait(-1)|Out-Null;$t.Result}
[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]|Out-Null
$m=Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
$current=$m.GetCurrentSession();$out=@()
foreach($s in $m.GetSessions()){
 $p=Await ($s.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
 $status=[string]$s.GetPlaybackInfo().PlaybackStatus;$acted=$false
 if($env:NINJA_MEDIA -eq 'pause' -and $status -eq 'Playing'){$acted=Await ($s.TryPauseAsync()) ([bool])}
 if($env:NINJA_MEDIA -eq 'resume' -and $current -and $s.SourceAppUserModelId -eq $current.SourceAppUserModelId -and $status -ne 'Playing'){$acted=Await ($s.TryPlayAsync()) ([bool])}
 $out+=[pscustomobject]@{app=($s.SourceAppUserModelId -replace '\.exe$','' -replace '^.*!','');status=$status;title=(@($p.Artist,$p.Title)|Where-Object{$_})-join ' - ';acted=$acted}}
ConvertTo-Json -Compress -InputObject @($out)"""


def media_sessions(action='status'):
    require_desktop()
    out=powershell(SESSIONS,{'NINJA_MEDIA':action},timeout=20).decode('utf-8','replace').strip()
    return json.loads(out) if out else []


def pause_or_resume(action):
    sessions=media_sessions(action);acted=[s for s in sessions if s.get('acted')]
    if acted:return {'action':action,'players':[f"{s['app']}: {s['title']}" for s in acted],'verification':'Windows media session reported the change.'}
    if action=='pause':return {'action':'pause','players':[],'verification':'Nothing was playing, so nothing changed.'}
    # "Play music" with no player open: start Spotify and resume what it last played.
    launch('spotify:')
    for _ in range(10):
        time.sleep(1)
        acted=[s for s in media_sessions('resume') if s.get('acted') or s.get('status')=='Playing']
        if acted:return {'action':'resume','players':[f"{s['app']}: {s['title']}" for s in acted],'verification':'Opened Spotify and resumed it.'}
    raise ValueError('Spotify opened but did not start playing; ask which song to play.')


def media(action,steps=1):
    if action in ('pause','resume'):return pause_or_resume(action)
    require_desktop()
    if action not in MEDIA:raise ValueError('Choose pause, resume, play_pause, next, previous, volume_up, volume_down or mute')
    count=max(1,min(10,steps)) if action.startswith('volume_') else 1
    for _ in range(count):press(MEDIA[action])
    return {'action':action,'presses':count,'verification':'Media key sent to Windows; each volume step is about 2%.'}


def spotify_title():
    """The Spotify window title: "Artist - Song" while playing, "Spotify Premium"/"Spotify Free" when paused, '' if closed."""
    out=powershell('(Get-Process Spotify -ErrorAction SilentlyContinue | Where-Object MainWindowTitle | Select-Object -First 1 -ExpandProperty MainWindowTitle)')
    return out.decode('utf-8','replace').strip()


_spotify={'token':'','until':0.0}


def spotify_api_track(query):
    """Spotify's own search (client-credentials app in .env: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET). No user sign-in."""
    import httpx
    client_id,secret=os.getenv('SPOTIFY_CLIENT_ID',''),os.getenv('SPOTIFY_CLIENT_SECRET','')
    if not client_id or not secret:return None
    with httpx.Client(timeout=10,trust_env=False) as client:
        if time.time()>_spotify['until']:
            token=client.post('https://accounts.spotify.com/api/token',data={'grant_type':'client_credentials'},auth=(client_id,secret)).raise_for_status().json()
            _spotify.update(token=token['access_token'],until=time.time()+token.get('expires_in',3600)-60)
        items=client.get('https://api.spotify.com/v1/search',params={'q':query,'type':'track','limit':1,'market':'IN'},
                         headers={'Authorization':'Bearer '+_spotify['token']}).raise_for_status().json()['tracks']['items']
    return (items[0]['id'],items[0]['name']+' - '+', '.join(a['name'] for a in items[0]['artists'])) if items else None


def spotify_track(query):
    """A Spotify track id: Spotify's API when configured, else DuckDuckGo's results for open.spotify.com track pages.
    DuckDuckGo answers with a bot check after many searches; that is respected, and the caller opens Spotify's search."""
    import httpx
    from . import adapters
    try:
        found=spotify_api_track(query)
        if found:return found
    except (httpx.HTTPError,KeyError,ValueError):pass
    try:
        with httpx.Client(timeout=10,follow_redirects=False,trust_env=False) as client:results=adapters._duckduckgo(client,'site:open.spotify.com/track '+query)
    except (httpx.HTTPError,ValueError):return None
    for item in (results or {}).get('sources',[]):
        match=re.search(r'open\.spotify\.com/(?:intl-[\w-]+/)?track/(\w{22})',item.get('url',''))
        if match:return match.group(1),re.sub(r'\s*[|].*$','',item.get('title') or '')
    return None


# Presses the Play button of the Spotify search result that best matches the song, through Windows UI Automation
# (the screen-reader interface). It must match at least half the words, so a library playlist is never pressed instead.
# Spotify exposes its buttons only after the first accessibility request, hence the caller's retries.
SPOTIFY_PRESS=r"""Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$words=@(($env:NINJA_SONG.ToLower() -split '\W+')|Where-Object{$_.Length -gt 1})
$proc=Get-Process Spotify -ErrorAction SilentlyContinue|Where-Object MainWindowHandle -ne 0|Select-Object -First 1
if(-not $proc){'{}';exit}
$root=[System.Windows.Automation.AutomationElement]::FromHandle($proc.MainWindowHandle)
$cond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
$best=$null;$score=0
foreach($b in $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,$cond)){
 $name=$b.Current.Name;if($name -notmatch '^Play '){continue}
 $s=@($words|Where-Object{$name.ToLower() -match ('\b'+[regex]::Escape($_)+'\b')}).Count
 if($s -gt $score){$best=$b;$score=$s}}
if($best -and $score*2 -ge $words.Count){$best.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke();ConvertTo-Json -Compress @{pressed=$best.Current.Name}}else{'{}'}"""


def wait_playing(seconds=8):
    """The song Spotify's window names once it plays, else ''."""
    for _ in range(int(seconds*2)):
        time.sleep(.5);now=spotify_title()
        if now and not now.lower().startswith('spotify'):return now
    return ''


def play_song(query):
    """Spotify app: a track link starts playback on Windows; without one (no link found), Spotify's search opens and
    the best-matching result's Play button is pressed. Either way the window title confirms what is playing."""
    require_desktop()
    from urllib.parse import quote
    found=spotify_track(query)
    if found:
        launch('spotify:track:'+found[0])
    else:
        launch('spotify:search:'+quote(query));time.sleep(1.5)
        pressed=''
        for _ in range(8):
            pressed=json.loads(powershell(SPOTIFY_PRESS,{'NINJA_SONG':query},timeout=20).decode('utf-8','replace').strip() or '{}').get('pressed','')
            if pressed:break
            time.sleep(.7)
        if not pressed:
            return {'opened':'Spotify search','query':query,'playing':False,'verification':'Spotify search is open but no result matched well enough to press; ask the user to pick the song.'}
    now=wait_playing()
    if now:return {'playing':now,'app':'Spotify','verification':'Spotify window shows this song playing.'}
    return {'opened':query,'app':'Spotify','playing':False,'verification':'Sent to Spotify, but its window did not show the song playing within 8 seconds.'}


def play_video(query):
    """Top YouTube result for the query, played in the default browser (yt-dlp search; no API key or sign-in)."""
    require_desktop()
    import yt_dlp
    try:
        with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'extract_flat':True,'skip_download':True,'noplaylist':True,'socket_timeout':15}) as ydl:
            entries=ydl.extract_info('ytsearch1:'+query,download=False).get('entries') or []
    except yt_dlp.utils.DownloadError:raise ValueError('YouTube search did not answer; try again') from None
    if not entries:raise ValueError('No YouTube video found for '+query)
    video=entries[0];url='https://www.youtube.com/watch?v='+video['id']
    launch(url)
    return {'playing':video.get('title') or query,'channel':video.get('channel') or video.get('uploader') or '','url':url,'app':'browser',
            'verification':'Opened in the default browser, where YouTube starts it; the page itself was not inspected.'}


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


# Spoken names for things people store under other words.
SYNONYMS={'signature':('signature','sign'),'resume':('resume','cv'),'cv':('resume','cv'),'photo':('photo','img','image','pic'),
          'invoice':('invoice','bill','receipt'),'bill':('invoice','bill','receipt'),'screenshot':('screenshot','screen shot','capture')}
INDEX_KIND={'video':"System.Kind='video'",'image':"System.Kind='picture'",'audio':"System.Kind='music'",'document':"System.Kind='document'",'pdf':"System.FileExtension='.pdf'"}
SINCE={'today':0,'yesterday':1,'week':7,'month':31}
# Windows Search (the Start-menu index): name and content matches in ~0.1 s. The query text is built here from
# cleaned words only and handed over in an environment variable, never spliced into the PowerShell command.
INDEX_SCRIPT=("$c=New-Object -ComObject ADODB.Connection;$c.Open(\"Provider=Search.CollatorDSO;Extended Properties='Application=Windows';\");"
              "$r=$c.Execute($env:NINJA_SEARCH_SQL);$o=@();while(-not $r.EOF){$o+=[pscustomobject]@{p=[string]$r.Fields.Item('System.ItemPathDisplay').Value;"
              "m=([datetime]$r.Fields.Item('System.DateModified').Value).ToLocalTime().ToString('s');s=[int64]$r.Fields.Item('System.Size').Value};$r.MoveNext()};"
              "ConvertTo-Json -Compress -InputObject @($o)")


def named(words,filename):
    """Every spoken word (or a synonym) starts a word of the file name: 'sign' matches 'sign.png', not 'design.png'."""
    tokens=normal(filename).split()
    return all(any(t.startswith(o) for o in SYNONYMS.get(w,(w,)) for t in tokens) for w in words)


def exact(words,filename):
    """The spoken word itself (not only a synonym) starts a word of the name: ranks 'signature1.jpg' above 'signADB.pdf'."""
    tokens=normal(filename).split()
    return all(any(t.startswith(w) for t in tokens) for w in words)


# Spoken filler that is never part of the file being looked for.
FILLER={'my','the','a','an','of','for','from','file','files','find','show','open','please','me','mera','meri','mere','wala','wali','wale','ki','ka','ke','dhundo','dikhao',
        'downloaded','saved','recent','latest','last','new','today','yesterday','week','month','this'}
# A type word sets the type filter instead of being searched for ("the PDF I downloaded yesterday").
TYPE_WORDS={'pdf':'pdf','pdfs':'pdf','video':'video','videos':'video','clip':'video','clips':'video','photo':'image','photos':'image','image':'image','images':'image',
            'picture':'image','pictures':'image','pic':'image','pics':'image','song':'audio','songs':'audio','audio':'audio','music':'audio','document':'document','documents':'document','doc':'document',
            'recording':'video','recordings':'video'}


def search_words(query,kind='any',modified='any'):
    """(words, kind). Words may be empty only when a type or date narrows the search."""
    # Screen recordings are named by date, so "screen" would match nothing.
    words=[w for w in normal(query).replace('screen recording','recording').split() if (len(w)>1 or w.isdigit()) and w not in FILLER]
    for w in list(words):
        if w in TYPE_WORDS:
            words.remove(w);kind=kind if kind!='any' else TYPE_WORDS[w]
    if not words and kind=='any' and modified=='any':raise ValueError('Say part of the file name, something written in it, or a type and day')
    return words[:6],kind


def since_date(modified,now=None):
    if modified not in SINCE:return None
    now=now or datetime.now()
    return (now.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=SINCE[modified]))


def index_sql(words,kind,since,folders):
    scopes=' OR '.join("SCOPE='file:"+f.as_posix().replace("'","")+"'" for f in folders)
    def term(w):
        options=SYNONYMS.get(w,(w,))
        return '('+' OR '.join(f"System.FileName LIKE '%{o}%' OR CONTAINS(*,'\"{o}*\"')" for o in options)+')'
    where=['('+scopes+')']+[term(w) for w in words]
    if kind in INDEX_KIND:where.append(INDEX_KIND[kind])
    if since:where.append("System.DateModified >= '"+since.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')+"'")
    return 'SELECT TOP 60 System.ItemPathDisplay, System.DateModified, System.Size FROM SYSTEMINDEX WHERE '+' AND '.join(where)+' ORDER BY System.DateModified DESC'


def index_search(words,kind,since,folders):
    """Rows from Windows Search, or None when the index is unavailable (the caller then walks the folders)."""
    try:
        out=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',INDEX_SCRIPT],capture_output=True,text=True,timeout=8,
                           env={**os.environ,'NINJA_SEARCH_SQL':index_sql(words,kind,since,folders)},creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except (OSError,subprocess.TimeoutExpired):return None
    if out.returncode!=0:return None
    text=out.stdout.strip()
    rows=json.loads(text) if text else []
    return [rows] if isinstance(rows,dict) else rows


def walk_search(words,kind,since,folders):
    """Name-only fallback when Windows Search is off."""
    wanted=KINDS.get(kind) or ({'.pdf'} if kind=='pdf' else None);rows=[];seen=0;started=time.monotonic()
    for root in folders:
        stack=[(root,0)]
        while stack and seen<=40000 and time.monotonic()-started<=4:
            folder,depth=stack.pop()
            try:entries=list(os.scandir(folder))
            except OSError:continue
            for entry in entries:
                seen+=1
                if hidden(entry):continue
                if entry.is_dir(follow_symlinks=False):
                    if depth<6:stack.append((Path(entry.path),depth+1))
                    continue
                if wanted and Path(entry.name).suffix.lower() not in wanted:continue
                if named(words,entry.name):
                    info=entry.stat()
                    if since and info.st_mtime<since.timestamp():continue
                    rows.append({'p':entry.path,'m':datetime.fromtimestamp(info.st_mtime).isoformat(timespec='seconds'),'s':info.st_size})
    return rows


def find_files(query,kind='any',modified='any'):
    words,kind=search_words(query,kind,modified);since=since_date(modified);folders=personal_folders()
    rows=index_search(words,kind,since,folders);engine='windows-search'
    # Unindexed folders (or the index switched off): fall back to the bounded name walk.
    if not rows:rows=walk_search(words,kind,since,folders);engine='name-walk'
    allowed=[f.resolve() for f in folders];results=[]
    for row in rows:
        path=Path(row['p'])
        if any(part.startswith(('.','$')) for part in path.parts) or not any(path.is_relative_to(f) for f in allowed):continue
        by_name=named(words,path.name)
        rank=2 if exact(words,path.name) else 1 if by_name else 0
        results.append({'name':path.name,'path':str(path),'folder':next(f.name for f in allowed if path.is_relative_to(f)),'size_mb':round(int(row.get('s') or 0)/1048576,2),
                        'modified':row['m'][:16].replace('T',' '),'match':'name' if by_name else 'content','_rank':rank})
    # Exact word in the name, then a synonym in the name, then a match inside the file; newest first in each group.
    results.sort(key=lambda r:r['modified'],reverse=True);results.sort(key=lambda r:-r['_rank'])
    ordered=[{k:v for k,v in r.items() if k!='_rank'} for r in results]
    # The model often reads "latest" as today; with nothing that new, offer the newest matches from any date.
    if not ordered and modified!='any' and (words or kind!='any'):
        wider=find_files(query,kind)
        if wider['files']:return wider|{'note':f'Nothing from {modified}; these are the newest matches from any date. '+wider['note']}
    return {'query':query,'files':ordered[:8],'total':len(ordered),'engine':engine,'searched':[f.name for f in folders],
            'note':'Files are already in best-match order (the first is the best). Several match: mention the first two or three in this order and ask which one.' if len(ordered)>1 else ''}


def open_file(path):
    require_desktop()
    # "Downloads" or "my downloads folder" names a personal folder directly.
    named=None if re.search(r'[\\/]',path) else next((root for root in personal_folders() if root.name.lower() in normal(path).split()),None)
    try:target=named or Path(path).resolve(strict=True)
    except OSError:raise ValueError('That file or folder no longer exists') from None
    if not any(target==root or target.is_relative_to(root) for root in personal_folders()):
        raise ValueError('Jarvis only opens items inside your personal folders (Desktop, Documents, Downloads, Videos, Pictures, Music)')
    if target.is_file() and target.suffix.lower() not in OPENABLE:
        raise ValueError('Jarvis does not open programs, scripts or shortcuts. Open it yourself if you trust it.')
    launch(str(target));return {'opened':str(target),'kind':'folder' if target.is_dir() else target.suffix.lower(),'verification':'Opened with its default Windows app.'}
