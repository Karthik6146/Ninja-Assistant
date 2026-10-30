// Energy detects pauses; the server's Silero VAD still checks for actual speech.
export class VoiceActivity {
  noise=.003; voiced=0; lastVoice=0; started=0; speaking=false;
  sample(rms:number, now:number) {
    if(!this.started)this.started=now;
    const loud=rms>Math.max(.012,this.noise*2.8);
    if(loud){this.voiced+=50;this.lastVoice=now;if(this.voiced>=200)this.speaking=true}
    else {if(!this.speaking)this.voiced=0;if(rms<.012)this.noise=.95*this.noise+.05*rms}
    return this.speaking&&now-this.lastVoice>=700?'send':now-this.started>=25000?(this.speaking?'send':'empty'):'listen';
  }
}
