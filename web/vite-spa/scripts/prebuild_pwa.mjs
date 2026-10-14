/** Build deterministic maskable app icons with only Node built-ins. */
import { mkdir, writeFile } from 'node:fs/promises';
import { deflateSync } from 'node:zlib';
const OUT = new URL('../public/icons/', import.meta.url);
const table = Uint32Array.from({length:256}, (_,i) => {let c=i;for(let k=0;k<8;k++) c=c&1?0xEDB88320^(c>>>1):c>>>1;return c>>>0;});
function crc32(data){let c=0xFFFFFFFF;for(const byte of data)c=table[(c^byte)&255]^(c>>>8);return (c^0xFFFFFFFF)>>>0;}
function chunk(name,data){const type=Buffer.from(name,'ascii'),size=Buffer.alloc(4),sum=Buffer.alloc(4);size.writeUInt32BE(data.length);sum.writeUInt32BE(crc32(Buffer.concat([type,data])));return Buffer.concat([size,type,data,sum]);}
function render(size,maskable){
 const stride=size*4+1,pixels=Buffer.alloc(size*stride);
 for(let y=0;y<size;y++){pixels[y*stride]=0;
  for(let x=0;x<size;x++){
   const xx=(x+.5-size/2)/(size/2), yy=(y+.5-size/2)/(size/2),dist=Math.hypot(xx,yy),ang=Math.atan2(yy,xx),r=maskable?.40:.55;
   const ring=dist>r*.62&&dist<r*1.02&&Math.abs(ang)>.68,spot=Math.abs(xx-.16)<.06&&Math.abs(yy)<.06,light=Math.max(0,1-dist*.48);
   const rgb=ring||spot?[248,250,252]:[Math.round(10+5*light),Math.round(22+15*light),Math.round(41+23*light)];
   const i=y*stride+1+x*4;pixels[i]=rgb[0];pixels[i+1]=rgb[1];pixels[i+2]=rgb[2];pixels[i+3]=255;
  }
 }
 const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(size,0);ihdr.writeUInt32BE(size,4);ihdr[8]=8;ihdr[9]=6;
 return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',ihdr),chunk('IDAT',deflateSync(pixels,{level:9})),chunk('IEND',Buffer.alloc(0))]);
}
await mkdir(OUT,{recursive:true});
for(const size of [192,512]) for(const purpose of ['any','maskable']){
 const file=new URL(`cloudtech-${size}-${purpose}.png`,OUT);
 await writeFile(file,render(size,purpose==='maskable'));
 console.log('PWA icon ready:',file.pathname);
}
