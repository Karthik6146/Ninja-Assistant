import pytest
from ninja import watch


def test_only_personal_videos_are_watched(monkeypatch, tmp_path):
    home = tmp_path / 'Videos'; home.mkdir()
    (home / 'clip.mp4').write_bytes(b'x'); (home / 'notes.txt').write_text('x'); (tmp_path / 'other.mp4').write_bytes(b'x')
    monkeypatch.setattr(watch.desktop, 'personal_folders', lambda: [home])
    assert watch.local(str(home / 'clip.mp4')) == (home / 'clip.mp4').resolve()
    for refused in ('notes.txt', '../other.mp4', 'missing.mp4'):
        with pytest.raises(ValueError):
            watch.local(str(home / refused))


def test_long_speech_is_thinned_but_spans_the_video():
    lines = [(i * 10, 'word ' * 20) for i in range(600)]
    text = watch.script(lines)
    assert len(text) <= watch.SPEECH_CHARS and text.startswith('[0:00]') and '[1:3' in text  # still reaches past 1:30:00
    assert watch.clock(75) == '1:15' and watch.clock(3725) == '1:02:05'


def test_youtube_is_downloaded_once_then_reused(monkeypatch, tmp_path):
    monkeypatch.setattr(watch, 'DATA', tmp_path)
    calls = []
    def fetch(url, folder):
        calls.append(url); path = folder / 'video.mp4'; path.write_bytes(b'x')
        return path, 'Me at the zoo', [(1.2, 'here we are in front of the elephants')]
    monkeypatch.setattr(watch, 'youtube', fetch)
    monkeypatch.setattr(watch.media, 'probe', lambda path: {'duration': 19.0, 'audio': True})
    monkeypatch.setattr(watch, 'frames', lambda *a: [(1.0, 'aW1n')])
    seen = []
    monkeypatch.setattr(watch, 'look', lambda shots, speech, title, duration, question: seen.append((speech, question)) or 'Elephants at a zoo.')
    first = watch.describe(watch.Watch(source='https://youtu.be/jNQXAC9IVRw'), 150)['data']
    again = watch.describe(watch.Watch(source='youtube.com/watch?v=jNQXAC9IVRw', question='what animal?'), 150)['data']
    assert len(calls) == 1 and first['speech_from'] == again['speech_from'] == 'captions'
    assert seen[1] == ('[0:01] here we are in front of the elephants', 'what animal?') and again['description'] == 'Elephants at a zoo.'
