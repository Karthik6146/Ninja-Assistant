from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from ninja import desktop


def test_index_query_is_built_from_cleaned_words_only():
    words, _ = desktop.search_words("signature'; DROP x -- \"evil\"")
    sql = desktop.index_sql(words, 'image', None, [Path('C:/Users/Me/Pictures')])
    assert words == ['signature', 'drop', 'evil'] and "'" not in ''.join(words)
    assert "System.Kind='picture'" in sql and "SCOPE='file:C:/Users/Me/Pictures'" in sql
    assert "System.FileName LIKE '%sign%'" in sql  # synonym


def test_date_filter():
    assert desktop.since_date('yesterday', datetime(2026, 10, 30, 15, 0)) == datetime(2026, 10, 29)
    assert desktop.since_date('any') is None
    # The index stores UTC: 29 Oct 00:00 IST is 28 Oct 18:30 UTC.
    ist = timezone(timedelta(hours=5, minutes=30))
    assert "System.DateModified >= '2026-10-28 18:30:00'" in desktop.index_sql(['pdf'], 'pdf', datetime(2026, 10, 29, tzinfo=ist), [Path('C:/x')])


def test_exact_word_ranks_above_synonym(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, 'personal_folders', lambda: [tmp_path])
    rows = [{'p': str(tmp_path / 'contract signADB.pdf'), 'm': '2026-10-30T10:00:00', 's': 1},
            {'p': str(tmp_path / 'signature1.jpg'), 'm': '2026-01-01T10:00:00', 's': 1}]
    monkeypatch.setattr(desktop, 'index_search', lambda *a: rows)
    assert desktop.find_files('signature')['files'][0]['name'] == 'signature1.jpg'


def test_names_match_whole_word_starts():
    assert desktop.named(['signature'], 'sign.png') and desktop.named(['resume'], 'My CV 2026.pdf')
    assert not desktop.named(['signature'], 'Untitled design.png')


def test_results_stay_inside_personal_folders_and_names_rank_first(monkeypatch, tmp_path):
    home = tmp_path / 'Documents'; home.mkdir()
    monkeypatch.setattr(desktop, 'personal_folders', lambda: [home])
    rows = [{'p': str(home / 'notes.txt'), 'm': '2026-10-30T10:00:00', 's': 10},
            {'p': str(home / 'resume.pdf'), 'm': '2026-01-01T10:00:00', 's': 10},
            {'p': str(tmp_path / 'outside' / 'resume.pdf'), 'm': '2026-10-30T10:00:00', 's': 10}]
    monkeypatch.setattr(desktop, 'index_search', lambda *a: rows)
    found = desktop.find_files('resume')
    assert [f['name'] for f in found['files']] == ['resume.pdf', 'notes.txt']
    assert found['files'][0]['match'] == 'name' and found['files'][1]['match'] == 'content' and 'ask which one' in found['note']


@pytest.mark.parametrize('index_rows', [None, []])
def test_falls_back_to_name_walk(monkeypatch, tmp_path, index_rows):
    (tmp_path / 'Valorant clip.mp4').write_bytes(b'x')
    monkeypatch.setattr(desktop, 'personal_folders', lambda: [tmp_path])
    monkeypatch.setattr(desktop, 'index_search', lambda *a: index_rows)
    found = desktop.find_files('valorant', 'video')
    assert found['engine'] == 'name-walk' and found['files'][0]['name'] == 'Valorant clip.mp4'


def test_spoken_filler_is_ignored():
    assert desktop.search_words('find my signature file') == (['signature'], 'any')
    assert desktop.search_words('mera resume wala') == (['resume'], 'any')


def test_type_words_become_filters():
    assert desktop.search_words('PDF', 'any', 'yesterday') == ([], 'pdf')
    assert desktop.search_words('valorant clip') == (['valorant'], 'video')
    with pytest.raises(ValueError):
        desktop.search_words('my file')


def test_screen_recordings_search_by_type():
    assert desktop.search_words('my latest screen recording') == ([], 'video')


def test_dated_search_widens_when_nothing_is_that_new(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, 'personal_folders', lambda: [tmp_path])
    old = [{'p': str(tmp_path / '2026-03-07 13-01-57.mp4'), 'm': '2026-03-07T13:01:57', 's': 1}]
    monkeypatch.setattr(desktop, 'index_search', lambda words, kind, since, folders: [] if since else old)
    monkeypatch.setattr(desktop, 'walk_search', lambda *a: [])
    found = desktop.find_files('recording', 'any', 'today')
    assert found['files'][0]['name'] == '2026-03-07 13-01-57.mp4' and found['note'].startswith('Nothing from today')
