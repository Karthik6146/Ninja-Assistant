import os
import pytest
from ninja import desktop

APPS=[{'Name':'Google Chrome','AppID':'Chrome'},{'Name':'VLC media player','AppID':'{6D809377}\\VideoLAN\\VLC\\vlc.exe'},
      {'Name':'OBS Studio','AppID':'OBS'},{'Name':'WhatsApp','AppID':'5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App'},
      {'Name':'Uninstall VLC','AppID':'uninstall'},{'Name':'Steam','AppID':'steam'}]


@pytest.fixture
def unlocked(monkeypatch):
    monkeypatch.setattr(desktop,'interactive',lambda:True)
    monkeypatch.setattr(desktop,'start_apps',lambda:APPS)
    launched=[]
    monkeypatch.setattr(desktop,'launch',lambda target:launched.append(target))
    return launched


def test_finds_apps_by_name_typo_and_partial(unlocked):
    assert desktop.find_app('chrome')['Name']=='Google Chrome'
    assert desktop.find_app('VLC')['Name']=='VLC media player'
    assert desktop.find_app('whatsap')['Name']=='WhatsApp'
    assert desktop.find_app('obs')['Name']=='OBS Studio'
    assert desktop.find_app('bluetooth settings')['AppID']=='ms-settings:bluetooth'


def test_unknown_app_suggests_and_uninstallers_are_never_matched(unlocked):
    with pytest.raises(ValueError,match='Steam'):desktop.find_app('steem launcher pro')
    # Asking to uninstall must never open the app instead.
    with pytest.raises(ValueError):desktop.find_app('uninstall vlc')


def test_open_app_launches_through_apps_folder(unlocked):
    result=desktop.open_app('whatsapp')
    assert unlocked==['shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App'] and result['app']=='WhatsApp'
    desktop.open_app('bluetooth settings')
    assert unlocked[-1]=='ms-settings:bluetooth'


def test_locked_session_blocks_gui_actions(monkeypatch):
    monkeypatch.setattr(desktop,'interactive',lambda:False)
    for call in (lambda:desktop.open_app('chrome'),lambda:desktop.open_url('youtube.com'),lambda:desktop.media('play_pause')):
        with pytest.raises(ValueError,match='unlock'):call()


@pytest.mark.parametrize('given,opened',[('youtube.com','https://youtube.com'),('https://www.youtube.com/watch?v=abc','https://www.youtube.com/watch?v=abc')])
def test_open_url_accepts_https_sites(unlocked,given,opened):
    assert desktop.open_url(given)['url']==opened and unlocked==[opened]


@pytest.mark.parametrize('bad',['javascript:alert(1)','file:///C:/Windows/System32/cmd.exe','http://example.com','https://user:pass@example.com','https://','ms-settings:privacy'])
def test_open_url_rejects_unsafe_targets(unlocked,bad):
    with pytest.raises(ValueError):desktop.open_url(bad)
    assert unlocked==[]


def test_media_keys_and_volume_steps(monkeypatch):
    monkeypatch.setattr(desktop,'interactive',lambda:True)
    pressed=[]
    monkeypatch.setattr(desktop,'press',lambda key:pressed.append(key))
    desktop.media('play_pause');desktop.media('volume_up',steps=3);desktop.media('mute')
    assert pressed==[0xB3,0xAF,0xAF,0xAF,0xAD]
    with pytest.raises(ValueError):desktop.media('shutdown')


@pytest.fixture
def folders(tmp_path,monkeypatch):
    videos=tmp_path/'Videos';docs=tmp_path/'Documents'
    (videos/'Valorant').mkdir(parents=True);docs.mkdir()
    (videos/'Valorant'/'valorant clutch final.mp4').write_bytes(b'x')
    (videos/'valorant raw.mkv').write_bytes(b'x')
    (docs/'Valorant notes.txt').write_text('notes')
    (docs/'valorant installer.exe').write_bytes(b'MZ')
    (docs/'.hidden').mkdir();(docs/'.hidden'/'valorant secret.txt').write_text('x')
    monkeypatch.setattr(desktop,'personal_folders',lambda:[videos,docs])
    return tmp_path


def test_find_files_matches_all_words_in_name_and_skips_hidden(folders):
    found=desktop.find_files('valorant')['files']
    names=[f['name'] for f in found]
    assert 'valorant secret.txt' not in names and set(names)=={'valorant clutch final.mp4','valorant raw.mkv','Valorant notes.txt','valorant installer.exe'}
    assert [f['name'] for f in desktop.find_files('valorant clutch')['files']]==['valorant clutch final.mp4']
    assert desktop.find_files('valorant',kind='video')['files'][0]['name'].endswith(('.mp4','.mkv'))


def test_open_file_allows_media_and_documents_only_inside_personal_folders(folders,monkeypatch):
    monkeypatch.setattr(desktop,'interactive',lambda:True)
    opened=[];monkeypatch.setattr(desktop,'launch',lambda target:opened.append(target))
    clip=folders/'Videos'/'valorant raw.mkv'
    assert desktop.open_file(str(clip))['opened']==str(clip.resolve())
    desktop.open_file(str(folders/'Videos'))
    with pytest.raises(ValueError,match='program'):desktop.open_file(str(folders/'Documents'/'valorant installer.exe'))
    outside=folders/'elsewhere.mp4';outside.write_bytes(b'x')
    with pytest.raises(ValueError,match='personal folders'):desktop.open_file(str(outside))
    with pytest.raises(ValueError):desktop.open_file(str(folders/'Videos'/'missing.mp4'))
    assert opened==[str(clip.resolve()),str((folders/'Videos').resolve())]


def test_device_tools_are_registered():
    from ninja import tools,assistant_tools  # noqa: F401
    for name in ('app.open','web.open','media.control','file.find','file.open'):assert name in tools.REGISTRY
