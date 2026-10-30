import pytest
from ninja import desktop

def test_desktop_launch_requires_interactive_session_and_known_app(monkeypatch):
    monkeypatch.setattr(desktop,'interactive',lambda:False)
    with pytest.raises(ValueError,match='unlock'):desktop.open_app('notepad')
    monkeypatch.setattr(desktop,'interactive',lambda:True)
    monkeypatch.setattr(desktop,'start_apps',lambda:[{'Name':'Windows PowerShell','AppID':'ps'},{'Name':'Terminal','AppID':'wt'}])
    for shell in ('powershell','windows terminal','cmd','regedit'):
        with pytest.raises(ValueError,match='shells'):desktop.open_app(shell)


def test_disconnected_session_blocks_default_input_desktop(monkeypatch):
    monkeypatch.setattr(desktop,'session_active',lambda:False)
    assert desktop.interactive() is False
