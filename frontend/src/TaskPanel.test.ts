import {describe,expect,it} from 'vitest';
import {friendlyStep} from './TaskPanel';

describe('friendlyStep',()=>{
 it('hides worker plumbing and renames tool and model steps',()=>{
  expect(friendlyStep('Run python.exe; timeout 7200s')).toBe('');
  expect(friendlyStep('Worker started task')).toBe('');
  expect(friendlyStep('Running media.control')).toBe('Controlled playback');
  expect(friendlyStep('Running custom.tool')).toBe('custom.tool');
  expect(friendlyStep('Qwen is choosing the next supported action')).toBe('Jarvis is thinking');
  expect(friendlyStep('Something else')).toBe('Something else');
 });
});
