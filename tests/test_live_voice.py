import json,wave
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from ninja.api import app
from ninja import listener,voice


class FakeListener:
    """Stands in for the resident process: every audio record produces the scripted events."""
    def __init__(self,events):self.events=events;self.audio=[];self.modes=[];self.sink=None
    def attach(self,sink):self.sink=sink
    def detach(self,sink):self.sink=None
    def send_audio(self,data):
        self.audio.append(data)
        for event in self.events:self.sink(event)
    def mode(self,standby):self.modes.append(standby)


def test_live_voice_requires_session_cookie():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/api/assistant/voice/live') as ws:ws.receive_text()


def test_live_voice_streams_audio_and_returns_transcript(monkeypatch,tmp_path):
    clip=tmp_path/'turn-1.wav'
    with wave.open(str(clip),'wb') as w:w.setparams((1,2,16000,0,'NONE','NONE'));w.writeframes(b'\0\0'*1600)
    fake=FakeListener([{'event':'speech'},{'event':'turn','path':str(clip)}])
    monkeypatch.setattr(listener,'shared',lambda:fake)
    monkeypatch.setattr(voice,'transcribe',lambda path,language:{'text':'open calculator','uncertain':False,'language':language,'timing':{'total_ms':250}})
    with TestClient(app) as client:
        client.post('/api/session',json={'token':'test-token'})
        with client.websocket_connect('/api/assistant/voice/live') as ws:
            ws.send_text(json.dumps({'standby':True,'language':'hinglish'}))
            ws.send_bytes(b'\0\0'*512)
            assert ws.receive_json()=={'type':'speech'}
            result=ws.receive_json()
    assert result['type']=='transcript' and result['text']=='open calculator' and result['language']=='auto'
    assert fake.modes==[True] and fake.audio==[b'\0\0'*512]


def test_live_voice_rejects_malformed_audio(monkeypatch):
    fake=FakeListener([])
    monkeypatch.setattr(listener,'shared',lambda:fake)
    with TestClient(app) as client:
        client.post('/api/session',json={'token':'test-token'})
        with client.websocket_connect('/api/assistant/voice/live') as ws:
            ws.send_bytes(b'\0'*7)
            assert ws.receive_json()['type']=='error'
    assert fake.audio==[]


def test_transcribe_skips_decoding_for_native_wav(monkeypatch,tmp_path):
    from ninja import media
    clip=tmp_path/'turn.wav'
    with wave.open(str(clip),'wb') as w:w.setparams((1,2,16000,0,'NONE','NONE'));w.writeframes(b'\1\0'*16000)
    assert voice.native_wav(clip) is True
    other=tmp_path/'other.wav'
    with wave.open(str(other),'wb') as w:w.setparams((2,2,44100,0,'NONE','NONE'));w.writeframes(b'\0\0'*100)
    assert voice.native_wav(other) is False
