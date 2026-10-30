import {describe,it,expect} from 'vitest';
import {normalizeEDL} from './types';
describe('legacy edit loading',()=>{it('preserves clip order and revision while supplying safe caption defaults',()=>{const clips=[{start:10,end:15},{start:0,end:4}];const edit=normalizeEDL({revision:7,clips});expect(edit.clips).toEqual(clips);expect(edit.revision).toBe(7);expect(edit.style.active_word).toBe(false);expect(edit.music).toBeNull()})});
