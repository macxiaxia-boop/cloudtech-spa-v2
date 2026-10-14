/** Cross-platform deterministic responsive image generation. */
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const script=fileURLToPath(new URL('./generate_responsive_images.py',import.meta.url));
const candidates=process.platform==='win32'
 ? [['py',['-3',script]],['python',[script]],['python3',[script]]]
 : [['python3',[script]],['python',[script]]];
let last='';
for(const [cmd,args] of candidates){
 const r=spawnSync(cmd,args,{encoding:'utf8',stdio:'pipe'});
 if(r.error?.code==='ENOENT'){last=cmd+' not found';continue;}
 if(r.stdout)process.stdout.write(r.stdout);
 if(r.stderr)process.stderr.write(r.stderr);
 if(r.status===0)process.exit(0);
 last=cmd+' failed (status '+r.status+'): '+(r.stderr||r.error?.message||'');
 if(!r.error||r.error.code!=='ENOENT') break;
}
throw new Error('Cannot build CloudTech responsive images. Install Python 3 and Pillow (python -m pip install Pillow>=10,<13). '+last);
