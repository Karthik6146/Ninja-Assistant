"""Explicit local speech setup. No downloads occur during normal conversations."""
import argparse,hashlib,json,subprocess,sys,urllib.request,venv
from pathlib import Path

def install(root):
    folder=root/'data/services/jarvis-voice';folder.mkdir(parents=True,exist_ok=True)
    python=folder/'venv/Scripts/python.exe'
    if not python.exists():venv.EnvBuilder(with_pip=True).create(folder/'venv')
    subprocess.run([str(python),'-m','pip','install','-r',str(Path(__file__).with_name('voice-requirements.lock'))],check=True)
    models=folder/'models';models.mkdir(exist_ok=True);records=[]
    release='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
    stt='https://huggingface.co/Systran/faster-whisper-small/resolve/536b0662742c02347bc0e980a01041f333bce120/'
    sources=[('kokoro-v1.0.onnx',release+'kokoro-v1.0.onnx'),('voices-v1.0.bin',release+'voices-v1.0.bin')]
    sources += [('whisper-small/'+name,stt+name) for name in ('config.json','model.bin','tokenizer.json','vocabulary.txt')]
    # Live listener: Silero VAD (MIT, pinned faster-whisper tag), Smart Turn v3.2 (BSD-2), openWakeWord hey_jarvis
    # (code Apache-2.0; pre-trained models CC BY-NC-SA 4.0: personal, non-commercial use only).
    wake='https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/'
    sources += [('listener/silero_vad_v6.onnx','https://github.com/SYSTRAN/faster-whisper/raw/v1.2.1/faster_whisper/assets/silero_vad_v6.onnx'),
                ('listener/smart-turn-v3.2-cpu.onnx','https://huggingface.co/pipecat-ai/smart-turn-v3/resolve/main/smart-turn-v3.2-cpu.onnx')]
    sources += [('listener/'+name,wake+name) for name in ('melspectrogram.onnx','embedding_model.onnx','hey_jarvis_v0.1.onnx')]
    sources += [('licenses/smart-turn-BSD-2.txt','https://raw.githubusercontent.com/pipecat-ai/smart-turn/main/LICENSE'),('licenses/openWakeWord-Apache-2.0.txt','https://raw.githubusercontent.com/dscripka/openWakeWord/main/LICENSE')]
    sources += [('licenses/kokoro-onnx-MIT.txt','https://raw.githubusercontent.com/thewh1teagle/kokoro-onnx/main/LICENSE'),('licenses/Kokoro-model-card.md','https://huggingface.co/hexgrad/Kokoro-82M/raw/main/README.md'),('licenses/faster-whisper-MIT.txt','https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/LICENSE'),('licenses/phonemizer-GPL.txt','https://raw.githubusercontent.com/bootphon/phonemizer/master/LICENSE')]
    expected={r['file']:r['sha256'] for r in json.loads((root/'docs/voice-model-sources.json').read_text(encoding='utf-8'))}
    for name,url in sources:
        dest=models/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            print('Downloading '+name,flush=True)
            temporary=dest.with_suffix(dest.suffix+'.partial')
            with urllib.request.urlopen(url,timeout=120) as source,temporary.open('wb') as output:
                while chunk:=source.read(1024*1024):output.write(chunk)
            temporary.replace(dest)
        digest=hashlib.sha256(dest.read_bytes()).hexdigest()
        if name in expected and not name.startswith('licenses/') and digest!=expected[name]:
            dest.unlink();raise SystemExit(f'{name}: SHA-256 {digest} does not match docs/voice-model-sources.json; removed it. Re-run or check the source.')
        records.append({'file':name,'source':url,'bytes':dest.stat().st_size,'sha256':digest})
    (folder/'sources.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    freeze=subprocess.check_output([str(python),'-m','pip','freeze'],text=True)
    (folder/'requirements-lock.txt').write_text(freeze,encoding='utf-8')
    print('Installed speech environment: '+str(folder))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,required=True)
    install(parser.parse_args().project.resolve(strict=True))
