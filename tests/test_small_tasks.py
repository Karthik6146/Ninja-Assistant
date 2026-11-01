from ninja import device_tools, permissions, tools


def test_notes_are_appended_and_searchable(monkeypatch, tmp_path):
    monkeypatch.setattr(device_tools, 'notes_file', lambda: tmp_path / 'Jarvis Notes.md')
    for text in ('Wifi password is on the router sticker', 'Call   the plumber\non Monday'):
        device_tools.add_note(device_tools.NoteInput(text=text), 15, None)
    saved = (tmp_path / 'Jarvis Notes.md').read_text(encoding='utf-8')
    assert saved.startswith('# Jarvis notes') and saved.count('\n- ') == 2 and 'Call the plumber on Monday' in saved
    found = device_tools.read_notes(device_tools.NotesQuery(query='wifi'), 15, None)['data']
    assert found['total'] == 1 and found['notes'][0].endswith('Wifi password is on the router sticker')


def test_screen_and_clipboard_text_is_untrusted_and_read_only():
    for name in ('clipboard.read', 'screen.look'):
        assert name in permissions.READS and tools.REGISTRY[name].permission in permissions.UNTRUSTED
    # Writing the clipboard is an action: after untrusted text it needs the user's confirmation.
    assert 'clipboard.write' not in permissions.READS and 'note.add' not in permissions.READS


def test_folders_open_by_name_but_full_paths_open_the_file(monkeypatch, tmp_path):
    from ninja import desktop
    downloads = tmp_path / 'Downloads'; downloads.mkdir(); (downloads / 'report.pdf').write_bytes(b'x')
    opened = []
    monkeypatch.setattr(desktop, 'personal_folders', lambda: [downloads])
    monkeypatch.setattr(desktop, 'require_desktop', lambda: None)
    monkeypatch.setattr(desktop, 'launch', opened.append)
    desktop.open_file('my Downloads folder'); desktop.open_file(str(downloads / 'report.pdf'))
    assert opened == [str(downloads), str((downloads / 'report.pdf').resolve())]


def test_small_actions_skip_confirmation_after_untrusted_text_but_risky_ones_do_not():
    assert {'media.play','media.control','app.open','file.open'}<=permissions.SMALL
    assert not {'web.open','clipboard.write','file.write','memory.remember','workflow.draft'}&permissions.SMALL
    assert tools.REGISTRY['media.play'].permission=='device.control'


def test_media_play_presses_keys_for_generic_requests(monkeypatch):
    from ninja import device_tools, desktop
    pressed, searched = [], []
    monkeypatch.setattr(desktop, 'media', lambda action, steps=1: pressed.append(action) or {'action': action})
    monkeypatch.setattr(desktop, 'play_song', lambda q: searched.append(q) or {'playing': q})
    for query in ('music', 'next song', 'I feel it coming The Weeknd'):
        device_tools.play(device_tools.PlayInput(query=query), 30, None)
    assert pressed == ['resume', 'next'] and searched == ['I feel it coming The Weeknd']
