/* Static-only service worker. Never cache enterprise API, private or customer data. */
const CACHE_VERSION='cloudtech-static-v1';
const OFFLINE_PAGE='/offline.html';
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(CACHE_VERSION).then(cache=>cache.add(OFFLINE_PAGE)));
 self.skipWaiting();
});
self.addEventListener('activate',event=>{
 event.waitUntil(Promise.all([
  caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('cloudtech-static-')&&key!==CACHE_VERSION).map(key=>caches.delete(key)))),
  self.clients.claim(),
 ]));
});
self.addEventListener('fetch',event=>{
 const req=event.request;
 if(req.method!=='GET')return;
 const url=new URL(req.url);
 if(url.origin!==self.location.origin)return;
 if(/^\/(api\/|v4(?:\/|$)|admin\/|private\/|uploads\/)/.test(url.pathname))return;
 if(req.mode==='navigate'){
  event.respondWith(fetch(req).catch(async()=>(await caches.match(OFFLINE_PAGE))||Response.error()));
  return;
 }
 if(/^\/assets\/.+[-.][a-z0-9_-]{8,}\.(?:js|css)$/i.test(url.pathname)){
  event.respondWith(caches.open(CACHE_VERSION).then(async cache=>{
   const hit=await cache.match(req);if(hit)return hit;
   const response=await fetch(req);
   if(response.ok&&response.type==='basic')await cache.put(req,response.clone());
   return response;
  }));
 }
});
