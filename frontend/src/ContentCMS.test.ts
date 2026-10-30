import {describe,it,expect} from 'vitest';
import {contentStatus} from './ContentCMS';
import {defaults} from './StudioForm';
import {Operation} from './YouTubeStudio';

describe('CMS status follows publishing evidence',()=>{
 const run={id:'run',job:'job',workflow:'flow',test:false,created:1,definition:defaults('clips'),items:[{name:'clip',state:'queued',operation:'upload'}],task:{state:'completed',step:'Rendered'}};
 const upload:Operation={id:'upload',kind:'upload',state:'private',offset:0,remote_id:'video',params:{}};
 it('never labels an exported or private video published',()=>{
  expect(contentStatus(run,[upload])).toBe('Uploaded / private');
  expect(contentStatus(run,[{...upload,state:'public'}])).toBe('Published');
  expect(contentStatus(run,[{...upload,state:'scheduled'}])).toBe('Scheduled');
 });
 it('surfaces failed visibility changes and superseded runs',()=>{
  expect(contentStatus(run,[upload,{...upload,id:'status',kind:'status',state:'failed',params:{upload:'upload'}}])).toBe('Needs attention');
  expect(contentStatus({...run,superseded_by:'new'},[upload])).toBe('Revised');
 });
});
