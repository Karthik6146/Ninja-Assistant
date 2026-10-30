"""Local CPU neural speech. Fixed models and output; bounded pipe requests only."""
import json,os,re,sys,wave
from contextlib import redirect_stdout
from pathlib import Path


def serve(models,output):
    import numpy as np
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    engine=None
    while line:=sys.stdin.buffer.readline(20001):
        value={}
        try:
            if len(line)>20000 or not line.endswith(b'\n'):return
            value=json.loads(line)
            if (not isinstance(value,dict) or set(value)!={'id','text','voice'}
                or not re.fullmatch('[a-f0-9]{32}',value['id'])
                or not isinstance(value['text'],str) or not 1<=len(value['text'])<=3000
                or value['voice'] not in ('hm_omega','hf_alpha','am_michael','af_heart','bm_george')):
                raise ValueError('Invalid speech request')
            if engine is None:
                options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
                session=ort.InferenceSession(str(models/'kokoro-v1.0.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
                engine=Kokoro.from_session(session,str(models/'voices-v1.0.bin'))
            text=re.sub(r'https?://\S+',' link ',value['text'])
            text=re.sub(r'[`*#_]','',text)
            # One continuous utterance, with the correct G2P language per script.
            parts=re.findall(r'[\u0900-\u097f][\u0900-\u097f\s,।!?]*|[^\u0900-\u097f]+',text)
            phonemes=' '.join(engine.tokenizer.phonemize(p,'hi' if re.search('[\u0900-\u097f]',p) else 'en-gb' if value['voice'].startswith('b') else 'en-us') for p in parts if p.strip())
            audio,rate=engine.create(phonemes,voice=value['voice'],lang='hi',is_phonemes=True)
            if not 0<len(audio)<=rate*180 or not np.isfinite(audio).all():raise ValueError('Invalid speech output')
            with wave.open(str(output),'wb') as wav:
                wav.setparams((1,2,rate,0,'NONE','NONE'));wav.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
            result={'id':value['id'],'ok':True}
        except Exception:
            output.unlink(missing_ok=True)
            result={'id':value.get('id') if isinstance(value,dict) else None,'error':'Neural speech failed. Check the local voice installation and retry.'}
        sys.__stdout__.write(json.dumps(result)+'\n');sys.__stdout__.flush()


if __name__=='__main__':
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    with open(os.devnull,'w') as quiet,redirect_stdout(quiet):
        serve(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
