import {readdirSync,writeFileSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const assets=readdirSync('dist/assets').map(f=>'/assets/'+f);
const version=createHash('sha256').update(assets.join('')).digest('hex').slice(0,12);
writeFileSync('dist/sw.js',`const CACHE='samay-${version}';const ASSETS=${JSON.stringify(['/', '/index.html','/manifest.webmanifest','/icon-192.png','/icon-512.png',...assets])};
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('samay-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(u.origin!==location.origin||u.pathname.startsWith('/api/')||e.request.method!=='GET')return;if(e.request.mode==='navigate'){e.respondWith(fetch(e.request).catch(()=>caches.match('/index.html')));return;}if(ASSETS.includes(u.pathname))e.respondWith(caches.match(u.pathname,{ignoreVary:true}).then(c=>c||fetch(e.request)));});`);
