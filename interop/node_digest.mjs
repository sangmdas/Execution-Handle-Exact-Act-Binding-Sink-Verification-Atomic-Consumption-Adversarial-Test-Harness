import fs from 'fs';
import crypto from 'crypto';
import path from 'path';
import {fileURLToPath} from 'url';
const here=path.dirname(fileURLToPath(import.meta.url));
const vectors=JSON.parse(fs.readFileSync(path.join(here,'..','test_vectors','canonicalization_vectors.json'),'utf8'));
function validate(v){
  if(v===null||typeof v==='string'||typeof v==='boolean') return;
  if(typeof v==='number') { if(!Number.isSafeInteger(v)) throw new Error('REFCANON-1 requires safe integer in JS interop'); return; }
  if(Array.isArray(v)){v.forEach(validate);return;}
  if(typeof v==='object'){Object.values(v).forEach(validate);return;}
  throw new Error('unsupported type');
}
function sortRec(v){
  if(Array.isArray(v)) return v.map(sortRec);
  if(v&&typeof v==='object') return Object.fromEntries(Object.keys(v).sort().map(k=>[k,sortRec(v[k])]));
  return v;
}
for(const v of vectors){
  validate(v.value);
  const b=Buffer.from(JSON.stringify(sortRec(v.value)),'utf8');
  console.log(v.name,crypto.createHash('sha256').update(b).digest('hex'));
}
