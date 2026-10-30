// Run from the separately installed OpenChatCut folder.
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
const {createServer}=await import(pathToFileURL(resolve('node_modules/vite/dist/node/index.js')).href);
const server=await createServer({configFile:resolve('config/vite.config.ts'),server:{host:'127.0.0.1',open:false,warmup:{clientFiles:[]}}});
await server.listen();server.printUrls();
