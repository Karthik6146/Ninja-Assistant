import {expect,test} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import ChatMarkdown from './ChatMarkdown';
test('renders tables and code without HTML execution or automatic remote images',()=>{
 const html=renderToStaticMarkup(<ChatMarkdown text={'## Heading\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```js\nalert(1)\n```\n\n<script>alert(2)</script>\n\n![tracker](https://example.com/pixel)\n\n[bad](javascript:alert)\n\n[good](https://example.com)'}/>);
 expect(html).toContain('<table>');expect(html).toContain('<h2>Heading</h2>');expect(html).toContain('<pre>');
 expect(html).not.toContain('<script>');expect(html).not.toContain('<img');expect(html).not.toContain('href="javascript:');expect(html).toContain('rel="noreferrer noopener"');
});
