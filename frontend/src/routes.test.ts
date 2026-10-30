import {expect,it} from 'vitest';
import {route} from './routes';
it('maps areas, studio tabs and old bookmarks',()=>{
 expect(route('')).toEqual({area:'Jarvis',studio:'Video Studio'});
 expect(route('#home').area).toBe('Jarvis');
 expect(route('#studio/media-library')).toEqual({area:'Studio',studio:'Media Library'});
 expect(route('#video%20studio')).toEqual({area:'Studio',studio:'Video Studio'});
 expect(route('#automations')).toEqual({area:'Studio',studio:'Automations'});
 expect(route('#youtube').area).toBe('YouTube');
 expect(route('#nonsense').area).toBe('Jarvis');
});
