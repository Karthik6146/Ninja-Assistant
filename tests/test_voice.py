import json
from pathlib import Path
import pytest
from ninja import voice,media


def write_audio(path,seconds=1):
    import wave
    with wave.open(str(path),'wb') as stream:
        stream.setparams((1,2,16000,0,'NONE','NONE'));stream.writeframes(b'\0\0'*(16000*seconds))


def test_resident_clipx_reuses_model_and_restarts_after_config_change(monkeypatch,tmp_path):
    import sys
    root=tmp_path/'clipx';root.mkdir();script=root/'transcribe-local.py'
    model=root/'model';model.mkdir();(model/'model.bin').touch()
    (root/'faster_whisper.py').write_text("from pathlib import Path\nimport os\nclass WhisperModel:\n def __init__(self,*args,**kw):\n  assert (kw['device'],kw['compute_type'])==('cuda','int8_float16') and kw['local_files_only']\n  assert os.environ['HF_HUB_OFFLINE']=='1' and os.environ['TRANSFORMERS_OFFLINE']=='1'\n  p=Path(__file__).with_name('loads.txt');p.write_text(p.read_text()+'1' if p.exists() else '1')\n")
    script.write_text("import argparse\nfrom pathlib import Path\ndef main():\n from faster_whisper import WhisperModel\n p=argparse.ArgumentParser();p.add_argument('--audio');p.add_argument('--model');p.add_argument('--device');p.add_argument('--language');p.add_argument('--alignment');a=p.parse_args()\n assert Path(a.audio).is_file() and a.alignment=='native'\n WhisperModel(a.model,device=a.device,compute_type='int8' if a.device=='cpu' else 'int8_float16',cpu_threads=4,local_files_only=True)\n return {'words':[{'text':a.language,'confidence':.8}], 'language':a.language}\n")
    monkeypatch.setattr(voice,'components',lambda:(root,Path(sys.executable),script,model))
    monkeypatch.setattr(voice,'DATA',tmp_path/'data');voice.DATA.mkdir()
    def run(args,*a,**kw):
        assert args[0]=='ffmpeg'
        write_audio(args[-1])
        return ''
    monkeypatch.setattr(media,'run',run)
    source=tmp_path/'input.webm';source.write_bytes(b'media')
    try:
        first=voice.transcribe(source,'en');second=voice.transcribe(source,'hinglish')
        assert first['text']=='en' and not first['warm']
        assert second['text']=='hi-latn' and second['warm']
        assert (root/'loads.txt').read_text()=='1'
        assert all(v>=0 for v in second['timing'].values())
        old=voice._engine
        old.process.kill();old.process.wait()
        restarted=voice.transcribe(source,'en')
        assert not restarted['warm'] and old.process.poll() is not None
        assert not Path(old.folder.name).exists()
        script.write_text(script.read_text()+'\n# configuration changed\n')
        third=voice.transcribe(source,'en')
        assert not third['warm'] and (root/'loads.txt').read_text()=='111'
        assert not voice._engine.audio.exists()
    finally:voice.shutdown()

def test_voice_preserves_transcript_confidence_and_cleans_audio(monkeypatch,tmp_path):
    python=tmp_path/'python.exe';script=tmp_path/'transcribe.py';model=tmp_path/'model'
    python.touch();script.touch();model.mkdir();(model/'model.bin').touch()
    monkeypatch.setattr(voice,'components',lambda:(tmp_path,python,script,model))
    from types import SimpleNamespace
    class Resident:
        def __init__(self,parts):
            self.audio=tmp_path/'utterance.wav';self.fingerprint=voice._fingerprint(parts)
            self.process=SimpleNamespace(poll=lambda:None);self.warm=True
        def recognize(self,language):
            assert language=='en'
            return {'value':{'words':[{'text':'hello','confidence':.8}]},'warm':True,'recognition_ms':1}
        def close(self):pass
    monkeypatch.setattr(voice,'_engine',None);monkeypatch.setattr(voice,'_Resident',Resident)
    calls=[]
    def run(args,*a,**kw):
        calls.append((args,kw))
        if args[0]=='ffmpeg':write_audio(args[-1]);return ''
        return json.dumps({'words':[{'text':'hello','confidence':.8}],'language':'en'})
    monkeypatch.setattr(media,'run',run)
    input=tmp_path/'input.webm';input.write_bytes(b'media')
    result=voice.transcribe(input,'en')
    assert result['text']=='hello'
    assert result['warm'] and not result['uncertain'] and result['timing']['recognition_ms']==1
    assert not Path(calls[0][0][-1]).exists()
    assert input.exists() # Upload endpoint owns removal of the original.
    voice.shutdown()


@pytest.fixture
def resident_fixture(monkeypatch,tmp_path):
    import sys,wave
    root=tmp_path/'clipx';root.mkdir();script=root/'transcribe-local.py'
    model=root/'model';model.mkdir();(model/'model.bin').touch()
    (root/'faster_whisper.py').write_text('class WhisperModel:\n def __init__(self,*a,**kw):pass\n')
    script.write_text("def main():\n from faster_whisper import WhisperModel\n import sys,time\n from pathlib import Path\n WhisperModel(sys.argv[sys.argv.index('--model')+1],device='cpu',compute_type='int8',local_files_only=True)\n return {'words':[]}\n")
    monkeypatch.setattr(voice,'components',lambda:(root,Path(sys.executable),script,model))
    monkeypatch.setattr(voice,'DATA',tmp_path/'data');voice.DATA.mkdir()
    source=tmp_path/'input.webm';source.write_bytes(b'media')
    def run(args,*a,**kw):
        assert args[0]=='ffmpeg'
        write_audio(args[-1])
        return ''
    monkeypatch.setattr(media,'run',run)
    try:yield source,script,root
    finally:voice.shutdown()


def test_resident_silence_is_not_a_transcript_and_reuses_safe_engine(resident_fixture):
    source,script,root=resident_fixture
    with pytest.raises(ValueError,match='No usable speech'):voice.transcribe(source,'en')
    engine=voice._engine
    assert engine.warm and not engine.audio.exists()
    with pytest.raises(ValueError,match='No usable speech'):voice.transcribe(source,'hinglish')
    assert voice._engine is engine and not engine.audio.exists()


def test_resident_timeout_kills_only_owned_process_and_retry_recovers(monkeypatch,resident_fixture):
    import subprocess,sys
    source,script,root=resident_fixture
    original=script.read_text();script.write_text(original.replace("return {'words':[]}","time.sleep(60);return {'words':[]}"))
    monkeypatch.setattr(voice,'VOICE_TIMEOUT',.3)
    unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    try:
        with pytest.raises(TimeoutError,match='timed out'):voice.transcribe(source,'en')
        assert voice._engine is None and unrelated.poll() is None
        script.write_text(original.replace("return {'words':[]}","return {'words':[{'text':'Recovered','confidence':.9}]}"))
        value=voice.transcribe(source,'en')
        assert value['text']=='Recovered' and not value['warm']
    finally:unrelated.terminate();unrelated.wait(timeout=3)


def test_speech_exception_does_not_leak_transcript_and_removes_audio(resident_fixture):
    source,script,root=resident_fixture
    script.write_text(script.read_text().replace("return {'words':[]}","raise ValueError('PRIVATE CONTENT NOT FOR LOGS')"))
    with pytest.raises(ValueError,match='ClipX speech recognition failed') as error:voice.transcribe(source,'en')
    assert 'PRIVATE CONTENT' not in str(error.value) and voice._engine is None


def test_oversized_audio_never_starts_resident_engine(monkeypatch,resident_fixture):
    source,script,root=resident_fixture
    with source.open('wb') as file:file.truncate(20*1024**2+1)
    monkeypatch.setattr(voice,'_Resident',lambda parts:pytest.fail('Oversized audio started recognition'))
    with pytest.raises(ValueError,match='20 MiB'):voice.transcribe(source,'en')


def test_concurrent_recording_is_rejected_without_starting_another_engine(monkeypatch,resident_fixture):
    from filelock import FileLock,Timeout
    source,script,root=resident_fixture
    monkeypatch.setattr(voice,'_Resident',lambda parts:pytest.fail('Concurrent recording started another engine'))
    with FileLock(voice.DATA/'voice-cpu.lock',timeout=0):
        with pytest.raises(Timeout):voice.transcribe(source,'en')


def test_helper_rejects_path_input_and_invalid_audio(resident_fixture):
    source,script,root=resident_fixture
    engine=voice._Resident(voice.components())
    try:
        engine.process.stdin.write(json.dumps({'id':'1'*32,'language':'en','audio':str(source)}).encode()+b'\n');engine.process.stdin.flush()
        assert 'error' in engine.responses.get(timeout=3)
        engine.audio.write_bytes(b'not a WAV')
        with pytest.raises(ValueError,match='ClipX speech recognition failed'):engine.recognize('en')
        assert not engine.audio.exists()
    finally:engine.close()

def test_voice_duration_limit_and_missing_dependencies(monkeypatch,tmp_path):
    monkeypatch.setattr(voice,'components',lambda:(tmp_path,tmp_path/'missing.exe',tmp_path/'missing.py',tmp_path/'model'))
    assert not voice.status()['ready']
    with pytest.raises(ValueError,match='configured'):voice.transcribe(tmp_path/'input.wav','en')



def test_overlong_decoded_speech_never_runs_cli(monkeypatch,tmp_path):
    python=tmp_path/'python.exe';script=tmp_path/'transcribe.py';model=tmp_path/'model'
    python.touch();script.touch();model.mkdir();(model/'model.bin').touch()
    monkeypatch.setattr(voice,'components',lambda:(tmp_path,python,script,model))
    from types import SimpleNamespace
    class Resident:
        def __init__(self,parts):
            self.audio=tmp_path/'utterance.wav';self.fingerprint=voice._fingerprint(parts)
            self.process=SimpleNamespace(poll=lambda:None);self.warm=True
        def recognize(self,language):pytest.fail('Overlong input reached speech recognition')
        def close(self):pass
    monkeypatch.setattr(voice,'_engine',None);monkeypatch.setattr(voice,'_Resident',Resident)
    def run(args,*a,**kw):
        if args[0]=='ffmpeg':write_audio(args[-1],61);return ''
        pytest.fail('Overlong input reached speech recognition')
    monkeypatch.setattr(media,'run',run)
    (tmp_path/'input.webm').write_bytes(b'media')
    with pytest.raises(ValueError,match='60 seconds'):voice.transcribe(tmp_path/'input.webm','en')
    voice.shutdown()


def test_invalid_config_during_active_transcription_does_not_close_engine(monkeypatch,tmp_path):
    from filelock import FileLock,Timeout
    monkeypatch.setattr(voice,'components',lambda:(tmp_path,tmp_path/'missing.exe',tmp_path/'missing.py',tmp_path/'model'))
    monkeypatch.setattr(voice,'shutdown',lambda:pytest.fail('Another request closed the active recognizer'))
    with FileLock(voice.DATA/'voice-cpu.lock',timeout=0):
        with pytest.raises(Timeout):voice.transcribe(tmp_path/'input.wav','en')
