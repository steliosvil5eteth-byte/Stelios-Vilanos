import crypto from 'crypto';

function stable(value){
  if(value==null||typeof value!=='object')return value;
  if(Array.isArray(value))return value.map(stable);
  return Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])]));
}
export function auditHash(item,prevHash='GENESIS'){
  const payload={...item};delete payload.hash;delete payload.prevHash;
  return crypto.createHash('sha256').update(`${prevHash}|${JSON.stringify(stable(payload))}`).digest('hex');
}
export function chainAuditItem(item,previous=null){
  const prevHash=previous?.hash||'GENESIS';
  const base={...item,prevHash};
  return {...base,hash:auditHash(base,prevHash)};
}
export function verifyAuditChain(rows=[]){
  const hashed=rows.filter(x=>x?.hash&&x?.prevHash).slice().reverse();
  let prev=hashed.length?(hashed[0].prevHash||'GENESIS'):'GENESIS',checked=0;
  const errors=[];
  for(const row of hashed){
    if(row.prevHash!==prev)errors.push({type:'PREV_HASH_MISMATCH',ts:row.ts||null,expected:prev,actual:row.prevHash});
    const expected=auditHash(row,row.prevHash);
    if(expected!==row.hash)errors.push({type:'HASH_MISMATCH',ts:row.ts||null,expected,actual:row.hash});
    prev=row.hash;checked++;
  }
  return {ok:errors.length===0,checked,legacyRows:Math.max(0,rows.length-hashed.length),headHash:hashed.length?hashed.at(-1).hash:null,errors:errors.slice(0,50)};
}
