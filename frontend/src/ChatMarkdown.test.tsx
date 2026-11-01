import {expect,test} from 'vitest';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import ChatMarkdown,{codeOf} from './ChatMarkdown';
test('renders tables and code without HTML execution or automatic remote images',()=>{
 const html=renderToStaticMarkup(<ChatMarkdown text={'## Heading\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```js\nalert(1)\n```\n\n<script>alert(2)</script>\n\n![tracker](https://example.com/pixel)\n\n[bad](javascript:alert)\n\n[good](https://example.com)'}/>);
 expect(html).toContain('<table>');expect(html).toContain('<h2>Heading</h2>');expect(html).toContain('<pre tabindex="0">');
 expect(html).not.toContain('<script>');expect(html).not.toContain('<img');expect(html).not.toContain('href="javascript:');expect(html).toContain('rel="noreferrer noopener"');
});

test('code blocks get a language label, Copy button and untouched text',()=>{
 expect(codeOf(createElement('code',{className:'language-ps1'},'Get-Process\n'))).toEqual({label:'PowerShell',text:'Get-Process'});
 expect(codeOf(createElement('code',{},'x=1\n'))).toEqual({label:'Code',text:'x=1'});
 expect(codeOf('plain')).toBeNull();
 const html=renderToStaticMarkup(<ChatMarkdown text={'Run:\n\n```bash\nls -la\n```\n\nand `pwd`'}/>);
 expect(html).toContain('<figcaption><span>Bash</span>');
 expect(html).toContain('<pre tabindex="0"><code>ls -la</code></pre>');
 expect(html).toContain('<code>pwd</code>');
});
