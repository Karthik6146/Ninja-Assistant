import os,subprocess,sys
from pathlib import Path
from fastapi.testclient import TestClient
from ninja import setup_routes
from ninja.api import app

GB=2**30
def specs(ram,vram=None,disk=200):return {'ram':ram*GB,'gpu':vram and {'name':'GPU','vram':vram*GB},'disk_free':disk*GB}

def test_models_are_rated_for_the_pc():
    rated,pick=setup_routes.fit(specs(16,8))
    fits={m['model']:m['fit'] for m in rated}
    # 27b spills past 8 GB of VRAM into RAM: it runs, slowly.
    assert pick=='qwen3.5:9b' and fits['qwen3.5:9b']=='gpu' and fits['qwen3.5:27b']=='cpu'
    assert {m['model']:m['fit'] for m in setup_routes.fit(specs(8,8))[0]}['qwen3.5:27b']=='no'
    assert setup_routes.fit(specs(16,6))[1]=='qwen3.5:4b'
    # No GPU: the largest that runs in RAM, capped at 4b because larger ones are too slow on a CPU.
    rated,pick=setup_routes.fit(specs(32))
    assert pick=='qwen3.5:4b' and {m['fit'] for m in rated}<={'cpu','no'}
    assert setup_routes.fit(specs(8))[1]=='qwen3.5:2b'
    assert setup_routes.fit(specs(4))[1] is None
    # Not enough free disk for the download rules a model out.
    assert setup_routes.fit(specs(16,8,disk=5))[1]=='qwen3.5:4b'

def test_setup_reports_system_and_refuses_unlisted_models():
    with TestClient(app) as client:
        client.post('/api/session',json={'token':'test-token'})
        value=client.get('/api/setup').json()
        assert value['system']['cores'] and value['system']['ram']>0 and value['models']
        assert client.post('/api/setup/pull',json={'model':'llama3:70b'},headers={'X-Ninja-Token':'test-token'}).status_code==400

def test_public_build_hides_studio_and_youtube():
    root=Path(__file__).resolve().parents[1]
    env={**os.environ,'NINJA_CREATOR':'','PYTHONPATH':str(root/'backend')}
    code=("from fastapi.testclient import TestClient\nfrom ninja.api import app\nfrom ninja import tools\n"
          "c=TestClient(app);h={'X-Ninja-Token':'test-token'}\n"
          "assert c.get('/api/status',headers=h).json()['creator'] is False\n"
          "assert c.get('/api/studio/channels',headers=h).status_code==404\n"
          "assert c.get('/api/setup',headers=h).status_code==200\n"
          "assert not [n for n in tools.REGISTRY if n.startswith('workflow.')]\n")
    done=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,cwd=root/'backend')
    assert done.returncode==0,done.stderr[-800:]

def test_voice_uses_ninjas_own_recognizer_without_clipx(monkeypatch,tmp_path):
    from ninja import voice
    def no_clipx():raise ValueError('Set the Caption Tool folder in Settings (your standalone ClipX folder).')
    monkeypatch.setattr(voice,'caption_config',no_clipx)
    monkeypatch.setenv('JARVIS_VOICE_HOME',str(tmp_path))
    root,python,script,model=voice.components()
    assert script.name=='speech-transcribe.py' and script.is_file() and python==tmp_path/'venv/Scripts/python.exe'
    assert voice.status()['ready'] is False and 'Set up voice' in voice.status()['message']
    # A configured but incomplete ClipX folder also falls back.
    monkeypatch.setattr(voice,'caption_config',lambda:(tmp_path,tmp_path/'missing.exe',tmp_path/'missing.py'))
    assert voice.components()[2].name=='speech-transcribe.py'
