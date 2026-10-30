import {describe,expect,it} from 'vitest';
import {acceptedTranscript,speechParts,draftSentences,extendsSpoken,wakeText,endsConversation,turnTiming,transcriptAction,orbMode,stopsSpeech,isEcho} from './VoiceControls';
describe('voice conversation acceptance',()=>{
 it('keeps uncertain speech and silence out of automatic task execution',()=>{
  expect(acceptedTranscript({text:'publish this',uncertain:true})).toBe(false);
  expect(acceptedTranscript({text:'  '})).toBe(false);
  expect(acceptedTranscript({text:'… .'})).toBe(false);
 });
 it('accepts clear English, Hindi and Hinglish without forcing translation',()=>{
  for(const text of ['What is a CMS?','सीएमएस क्या है?','Jarvis, CMS kya hota hai?'])expect(acceptedTranscript({text,uncertain:false})).toBe(true);
 });
});

it('splits Hindi and English sentences for early playback',()=>{expect(speechParts('नमस्ते। What is next? Let us talk.')).toEqual(['नमस्ते।','What is next?','Let us talk.']);expect(speechParts('')).toEqual([])});

it('speaks only finished draft sentences and continues when the final reply extends them',()=>{
 expect(draftSentences('Yes sir. The thumbnail is')).toEqual(['Yes sir.']);
 expect(extendsSpoken(['Yes sir.'],speechParts('Yes sir. It is rendering.'))).toBe(true);
 expect(extendsSpoken(['I am generating it.'],speechParts('No tool action was verified. Sorry.'))).toBe(false);
 expect(extendsSpoken([],[])).toBe(true);
});

it('wakes only on Jarvis and passes along the rest of the request',()=>{
 expect(wakeText('Jarvis, open Calculator')).toBe('open Calculator');
 expect(wakeText('Hey Jarvis.')).toBe('');
 expect(wakeText('जार्विस, मुझे एक image बनाओ')).toBe('मुझे एक image बनाओ');
 expect(wakeText('the weather is nice today')).toBeNull();
 expect(wakeText('I told Jarvis yesterday')).toBeNull();
});
it('recognises conversation-ending phrases',()=>{
 for(const text of ["That's all, Jarvis.",'Thank you Jarvis','बस','bas itna hi','Goodbye.'])expect(endsConversation(text)).toBe(true);
 expect(endsConversation('Thank you, now generate an image')).toBe(false);
});

it('reports how long a voice turn took from end of speech to first audio',()=>{
 expect(turnTiming({end:1000,text:1520,voice:3100})).toBe('You stopped → text 0.52 s · → Jarvis speaking 2.10 s');
 expect(turnTiming({end:1000,text:1520})).toBe('');
});

it('splits a long sentence at a clause so the first words can be spoken sooner',()=>{
 expect(speechParts('CMS एक software है, जिससे बिना coding के website का content आसानी से बदल सकते हैं।')).toEqual(['CMS एक software है,','जिससे बिना coding के website का content आसानी से बदल सकते हैं।']);
 expect(speechParts('Yes, sir.')).toEqual(['Yes, sir.']);
});

it('speaks a short opener on its own before the rest of a long reply',()=>{
 expect(speechParts('जी सर, CMS एक software है जिससे आप website का content आसानी से बदल सकते हैं।')[0]).toBe('जी सर,');
});

describe('what Jarvis does with a transcript',()=>{
 const clear=(text:string)=>({text,uncertain:false});
 it('sends ordinary speech in a conversation',()=>{
  expect(transcriptAction(clear('Open calculator'),true,false)).toEqual({kind:'send',text:'Open calculator',woke:false});
 });
 it('in standby needs the wake word unless the listener already verified it',()=>{
  expect(transcriptAction(clear('the weather is nice'),false,false).kind).toBe('ignore');
  expect(transcriptAction(clear('Jarvis, open calculator'),false,false)).toEqual({kind:'send',text:'open calculator',woke:true});
  expect(transcriptAction(clear('Hey Travis, open calculator'),false,true)).toEqual({kind:'send',text:'Hey Travis, open calculator',woke:true});
  expect(transcriptAction(clear('Hey Jarvis.'),false,true).kind).toBe('greet');
 });
 it('ends on goodbye phrases and asks again when unclear',()=>{
  expect(transcriptAction(clear("That's all, Jarvis."),true,false).kind).toBe('end');
  expect(transcriptAction({text:'mumble',uncertain:true},true,false).kind).toBe('repeat');
  expect(transcriptAction({text:'mumble',uncertain:true},false,false).kind).toBe('ignore');
 });
});

it('maps voice states to the orb look',()=>{
 expect(orbMode('Listening — go ahead',false)).toBe('listening');
 expect(orbMode('Standby — say “Hey Jarvis”',false)).toBe('standby');
 expect(orbMode('Jarvis is thinking',false)).toBe('thinking');
 expect(orbMode('Jarvis is speaking',false)).toBe('speaking');
 expect(orbMode('Listening — go ahead',true)).toBe('muted');
 expect(orbMode('Ready to talk',false)).toBe('idle');
});

describe('speech while Jarvis talks',()=>{
 it('only stop words interrupt',()=>{
  expect(stopsSpeech('Stop.')).toBe(true);expect(stopsSpeech('Jarvis, ruko')).toBe(true);expect(stopsSpeech('रुको')).toBe(true);
  expect(stopsSpeech('stopwatch kholo')).toBe(false);expect(stopsSpeech('also check my email')).toBe(false);
 });
 it('treats his own words leaking into the mic as echo',()=>{
  const said='Of course, sir. You have one message from Vinay.';
  expect(isEcho('you have one message from vinay',said)).toBe(true);
  expect(isEcho('and remind me at 7 PM',said)).toBe(false);
 });
});
