"""Live listener: Silero VAD + Smart Turn v3.2 end-of-turn + openWakeWord "hey jarvis". Offline, CPU, numpy + onnxruntime.

stdin records: 1-byte kind, 4-byte little-endian length, payload.
  b'A' 16 kHz mono int16 audio (multiples of 512 samples)
  b'M' JSON {"standby": bool} switches mode and starts a fresh turn
stdout: one JSON event per line: ready, speech, turn (with the WAV path), discard, wake, error.
"""
import collections,json,os,struct,sys,wave
from contextlib import redirect_stdout
from pathlib import Path
import numpy as np
import onnxruntime as ort
sys.path.insert(0,str(Path(__file__).resolve().parent))
from turn_logic import TurnDetector

RATE,FRAME=16000,512


def session(path):
    options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1;options.log_severity_level=4
    return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])


class Vad:
    """Silero v6 run frame by frame, carrying its recurrent state and 64 samples of context."""
    def __init__(self,path):
        self.model=session(path);self.reset()
    def reset(self):
        self.h=np.zeros((1,1,128),'float32');self.c=np.zeros((1,1,128),'float32');self.context=np.zeros(64,'float32')
    def __call__(self,frame):
        x=np.concatenate([self.context,frame])[None,:]
        probability,self.h,self.c=self.model.run(None,{'input':x,'h':self.h,'c':self.c})
        self.context=frame[-64:];return float(np.ravel(probability)[0])


def mel_filters(n_mels=80,n_fft=400,sr=RATE):
    # Slaney mel filterbank, adapted from faster-whisper's feature extractor (MIT, Copyright (c) 2023 SYSTRAN).
    fftfreqs=np.fft.rfftfreq(n=n_fft,d=1.0/sr);mels=np.linspace(0.0,45.245640471924965,n_mels+2)
    f_sp=200.0/3;freqs=f_sp*mels;min_log_mel=1000.0/f_sp;log_t=mels>=min_log_mel
    freqs[log_t]=1000.0*np.exp(np.log(6.4)/27.0*(mels[log_t]-min_log_mel))
    fdiff=np.diff(freqs);ramps=freqs.reshape(-1,1)-fftfreqs.reshape(1,-1)
    weights=np.maximum(0,np.minimum(-ramps[:-2]/fdiff[:-1,None],ramps[2:]/fdiff[1:,None]))
    return (weights*(2.0/(freqs[2:n_mels+2]-freqs[:n_mels]))[:,None]).astype('float32')


class SmartTurn:
    """Probability that the user finished their thought, from the whole turn's audio (last 8 s)."""
    def __init__(self,path):
        self.model=session(path);self.filters=mel_filters()
        self.window=(0.5-0.5*np.cos(2*np.pi*np.arange(400)/400)).astype('float32')  # periodic Hann
    def features(self,audio):
        audio=audio[-8*RATE:];audio=np.pad(audio,(8*RATE-len(audio),0))  # zeros go at the beginning
        audio=(audio-audio.mean())/np.sqrt(audio.var()+1e-7)
        padded=np.pad(audio,200,mode='reflect')
        frames=np.lib.stride_tricks.sliding_window_view(padded,400)[::160]*self.window
        power=np.abs(np.fft.rfft(frames,axis=1))**2
        log_spec=np.log10(np.maximum(self.filters@power.T,1e-10))[:,:-1]
        log_spec=np.maximum(log_spec,log_spec.max()-8.0)
        return ((log_spec+4.0)/4.0)[None].astype('float32')
    def __call__(self,audio):
        return float(np.ravel(self.model.run(None,{'input_features':self.features(audio)})[0])[0])


class WakeWord:
    """openWakeWord streaming pipeline: melspectrogram -> 76-frame embeddings -> hey_jarvis over 16 embeddings."""
    def __init__(self,folder):
        self.mel=session(folder/'melspectrogram.onnx');self.embed=session(folder/'embedding_model.onnx');self.model=session(folder/'hey_jarvis_v0.1.onnx')
        self.reset()
    def reset(self):
        self.raw=np.zeros(0,'float32');self.pending=0
        self.mels=np.ones((76,32),'float32');self.embeddings=collections.deque(maxlen=16);self.cooldown=0
    def __call__(self,frame):
        self.raw=np.concatenate([self.raw,frame*32768.0])[-RATE*2:];self.pending+=len(frame);fired=False
        while self.pending>=1280:
            self.pending-=1280
            end=len(self.raw)-self.pending;chunk=self.raw[max(0,end-1280-480):end]
            spec=self.mel.run(None,{'input':chunk[None,:]})[0].squeeze()/10.0+2.0
            self.mels=np.concatenate([self.mels,spec.reshape(-1,32)])[-200:]
            if len(self.mels)>=76:
                self.embeddings.append(self.embed.run(None,{'input_1':self.mels[-76:][None,:,:,None]})[0].reshape(96))
            self.cooldown=max(0,self.cooldown-1)
            if len(self.embeddings)==16 and not self.cooldown:
                score=float(np.ravel(self.model.run(None,{'x.1':np.stack(self.embeddings)[None].astype('float32')})[0])[0])
                if score>=.5:fired=True;self.cooldown=25  # ~2 s before it can fire again
        return fired


def serve(models,folder):
    vad=Vad(models/'silero_vad_v6.onnx');turn=SmartTurn(models/'smart-turn-v3.2-cpu.onnx');wake=WakeWord(models)
    detector=TurnDetector();preroll=collections.deque(maxlen=16);audio=[];count=0
    def emit(value):sys.__stdout__.write(json.dumps(value)+'\n');sys.__stdout__.flush()
    emit({'event':'ready'})
    stdin=sys.stdin.buffer
    while header:=stdin.read(5):
        if len(header)<5:return
        kind,size=header[:1],struct.unpack('<I',header[1:])[0]
        if size>RATE*4:return
        payload=stdin.read(size)
        try:
            if kind==b'M':
                mode=json.loads(payload);detector=TurnDetector(standby=bool(mode.get('standby')))
                vad.reset();wake.reset();preroll.clear();audio=[];continue
            if kind!=b'A' or size%(FRAME*2):raise ValueError('Invalid audio record')
            samples=np.frombuffer(payload,'<i2').astype('float32')/32768.0
            for frame in samples.reshape(-1,FRAME):
                heard=detector.standby and wake(frame)
                if heard:emit({'event':'wake'})
                if detector.speaking:audio.append(frame)
                else:preroll.append(frame)
                for event in detector.frame(vad(frame),lambda:turn(np.concatenate(audio)),heard):
                    if event=='speech':audio=list(preroll);emit({'event':'speech'})
                    elif event=='turn':
                        count+=1;path=folder/f'turn-{count%8}.wav'
                        with wave.open(str(path),'wb') as out:
                            out.setparams((1,2,RATE,0,'NONE','NONE'));out.writeframes((np.clip(np.concatenate(audio),-1,1)*32767).astype('<i2').tobytes())
                        emit({'event':'turn','path':str(path)});audio=[];preroll.clear()
                    else:emit({'event':'discard'});audio=[];preroll.clear()
        except Exception as error:
            emit({'event':'error','message':type(error).__name__})


if __name__=='__main__':
    os.environ.update(PYTHONIOENCODING='utf-8')
    with open(os.devnull,'w') as quiet,redirect_stdout(quiet):
        serve(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
