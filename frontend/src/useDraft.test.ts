import {expect,it} from 'vitest';
import {restoreDraft} from './useDraft';
it('keeps saved work while adding fields introduced by an upgrade',()=>{
 expect(restoreDraft({text:'my unsent message'},{text:'',instruction:'',language:'hinglish'})).toEqual({text:'my unsent message',instruction:'',language:'hinglish'});
 expect(restoreDraft('invalid old object',{text:''})).toEqual({text:''});
 expect(restoreDraft(['saved'],['default'])).toEqual(['saved']);
});
