import {expect,it} from 'vitest';
import {VoiceActivity} from './voiceActivity';
it('ignores silence and isolated clicks',()=>{
 const vad=new VoiceActivity();let result='';
 for(let t=50;t<=25200;t+=50)result=vad.sample(t%500===0?.05:.002,t);
 expect(result).toBe('empty');
});
it('waits through short pauses and ends after speech plus a 700 ms pause',()=>{
 const vad=new VoiceActivity();
 for(let t=50;t<=1000;t+=50)expect(vad.sample(.05,t)).toBe('listen');
 expect(vad.sample(.002,1600)).toBe('listen');
 expect(vad.sample(.05,1650)).toBe('listen');
 expect(vad.sample(.002,2300)).toBe('listen');
 expect(vad.sample(.002,2350)).toBe('send');
});
