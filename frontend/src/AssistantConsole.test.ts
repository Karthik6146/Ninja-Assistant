import {describe,it,expect} from 'vitest';
import {canChange,conversationTurns,AssistantTask,spokenReply,nearBottom,sendKey,greeting} from './AssistantConsole';
describe('assistant follow-up controls',()=>{it('allows follow-up after completion or failure and hides it on cancelled requests',()=>{expect(canChange('completed')).toBe(true);expect(canChange('failed')).toBe(true);expect(canChange('running')).toBe(true);expect(canChange('cancelled')).toBe(false)})});
describe('companion outputs',()=>{
 it('shows the public conversation without exposing internal tool prompts',()=>{
  const conversation=[{role:'user' as const,content:'What is a CMS?',revision:0},{role:'assistant' as const,content:'A content management system.',revision:0},{role:'user' as const,content:'Give an example.',revision:1}];
  expect(conversationTurns({text:'old',reply:'old',conversation} as AssistantTask)).toEqual(conversation);
  expect(conversationTurns({text:'Legacy question',reply:'Legacy answer',revision:2} as AssistantTask)).toEqual([{role:'user',content:'Legacy question',revision:0},{role:'assistant',content:'Legacy answer',revision:2}]);
 });
});


it('does not read verification notices aloud',()=>{
 expect(spokenReply('No tool action was verified for this reply.\n\nSir, nothing is running.')).toBe('Sir, nothing is running.');
 expect(spokenReply('Done, sir.')).toBe('Done, sir.');
});

it('follows new messages only while the reader is near the bottom',()=>{
 expect(nearBottom({scrollTop:900,scrollHeight:1400,clientHeight:450})).toBe(true);
 expect(nearBottom({scrollTop:200,scrollHeight:1400,clientHeight:450})).toBe(false);
});
it('sends on Enter but not Shift+Enter or while a Hindi IME is composing',()=>{
 expect(sendKey({key:'Enter',shiftKey:false,isComposing:false})).toBe(true);
 expect(sendKey({key:'Enter',shiftKey:true,isComposing:false})).toBe(false);
 expect(sendKey({key:'Enter',shiftKey:false,isComposing:true})).toBe(false);
 expect(sendKey({key:'a',shiftKey:false,isComposing:false})).toBe(false);
});

it('greets by time of day',()=>{expect(greeting(2)).toBe('Working late');expect(greeting(9)).toBe('Good morning');expect(greeting(14)).toBe('Good afternoon');expect(greeting(20)).toBe('Good evening')});

import {replyNotice} from './AssistantConsole';
describe('replyNotice',()=>{
 it('splits the verification notice from the reply text',()=>{
  expect(replyNotice('No tool action was verified for this reply.\n\nOpened Spotify.')).toEqual({notice:'No tool action was verified for this reply.',body:'Opened Spotify.'});
  expect(replyNotice('Done, sir.')).toEqual({notice:'',body:'Done, sir.'});
 });
});
