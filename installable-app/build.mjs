import {readFileSync,readdirSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
function walk(dir){return readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(dir+'/'+e.name):[dir+'/'+e.name]);}
const files=walk('public').filter(p=>!p.endsWith('/sw.js')).sort();const hash=createHash('sha256');for(const file of files)hash.update(file).update(readFileSync(file));const paths=files.map(p=>'/'+p.slice(7));
writeFileSync('public/sw.js',`const CACHE='samay-installed-${hash.digest('hex').slice(0,16)}';const SHELL=${JSON.stringify(paths)};
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('samay-installed-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(url.origin!==self.location.origin||event.request.method!=='GET'||url.pathname.startsWith('/api/')||url.pathname.startsWith('/backend/'))return;if(event.request.mode==='navigate'){event.respondWith(fetch(event.request).catch(()=>caches.match('/index.html')));return;}if(SHELL.includes(url.pathname))event.respondWith(caches.open(CACHE).then(cache=>cache.match(url.pathname,{ignoreVary:true})).then(cached=>cached||fetch(event.request)));});`);
