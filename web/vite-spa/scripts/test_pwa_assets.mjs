/** Verify real PWA build outputs, not merely the presence of manifest text. */
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const dist=new URL('../dist-v45/',import.meta.url);
const manifest=JSON.parse(await readFile(new URL('manifest.webmanifest',dist),'utf8'));
assert.equal(manifest.display,'standalone');
assert.equal(manifest.scope,'/');
assert.equal(manifest.icons.length,4);
assert(manifest.icons.some(icon=>icon.purpose==='maskable'&&icon.sizes==='512x512'));
for(const icon of manifest.icons){
 const data=await readFile(new URL(icon.src.slice(1),dist));
 assert.deepEqual([...data.subarray(0,8)],[137,80,78,71,13,10,26,10],icon.src+' PNG signature');
 const size=Number(icon.sizes.split('x')[0]);
 assert.equal(data.readUInt32BE(16),size,icon.src+' width');
 assert.equal(data.readUInt32BE(20),size,icon.src+' height');
}
const worker=await readFile(new URL('sw.js',dist),'utf8');
const offline=await readFile(new URL('offline.html',dist),'utf8');
assert(worker.includes("request.method !== 'GET'")||worker.includes("req.method!=='GET'"),'worker must ignore mutating methods');
assert(worker.includes('api\\/'),'worker must explicitly exclude API paths');
assert(offline.includes('不会显示或执行未验证的任务'),'offline must not promise private data');
console.log('Verified four real PNG icons + manifest + no API cache + truthful offline page');
