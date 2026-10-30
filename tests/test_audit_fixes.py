"""Regressions for the 2026-10-30 security audit (see ~/security-audit-skill/ninja-assistant/run-1)."""
import pytest
from fastapi.testclient import TestClient
from ninja import agent, api, config, permissions, video_sources
from ninja.studio_metadata import Metadata

client = TestClient(api.app)


def test_session_cookie_is_a_revocable_id_not_the_master_token():
    r = client.post('/api/session', json={'token': config.TOKEN})
    cookie = r.cookies.get('ninja_session')
    assert cookie and cookie != config.TOKEN and config.TOKEN not in r.headers.get('set-cookie', '')
    assert client.get('/api/status').status_code == 200          # cookie authenticates reads
    assert client.post('/api/emergency', json={}).status_code == 403  # but never mutations
    client.post('/api/session/logout', headers={'X-Ninja-Token': config.TOKEN})
    assert client.get('/api/status', cookies={'ninja_session': cookie}).status_code == 401
    assert client.get('/api/status', cookies={'ninja_token': config.TOKEN}).status_code == 401  # old cookie name is dead


def test_default_origins_trust_only_the_served_app(monkeypatch):
    import importlib
    monkeypatch.delenv('NINJA_ORIGINS', raising=False)
    monkeypatch.setattr('dotenv.load_dotenv', lambda *a, **k: None)
    fresh = importlib.reload(config)
    try:
        assert all(':5173' not in o for o in fresh.ORIGINS)
    finally:
        importlib.reload(config)


def test_shared_document_text_taints_the_conversation():
    assert 'file.read' in permissions.UNTRUSTED
    task = {}
    agent.note(task, 'file.read', {'verified': True})
    assert task.get('tainted') is True


def test_caption_tool_has_no_guessed_default(monkeypatch):
    monkeypatch.delenv('CAPTION_TOOL_PATH', raising=False)
    with pytest.raises(ValueError, match='Caption Tool folder'):
        video_sources.caption_config()


@pytest.mark.parametrize('text', ['Visit https://example.invalid now', 'see www.example.invalid', 'join bit.ly/x'])
def test_model_metadata_cannot_publish_links(text):
    with pytest.raises(ValueError, match='link'):
        Metadata(title='Valorant tips', description=text, tags=['valorant'])
    Metadata(title='Valorant tips', description='Three tips for patch 9.0, version 1.2.', tags=['valorant'])


@pytest.mark.parametrize('address,public', [('8.8.8.8', True), ('10.0.0.1', False), ('::ffff:10.0.0.1', False), ('2002:0a00:0001::1', False), ('64:ff9b::0a00:0001', False), ('2606:4700::1111', True)])
def test_fetch_blocks_private_ipv4_hidden_in_ipv6(address, public):
    from ninja.adapters import public_ip
    assert public_ip(address) is public
