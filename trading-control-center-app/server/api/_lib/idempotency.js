import crypto from 'crypto';
import {databaseConfigured,db} from './db.js';
import {getJson,setJson,deleteJson} from './store.js';

function stable(value){
  if(value==null||typeof value!=='object') return value;
  if(Array.isArray(value)) return value.map(stable);
  return Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])]));
}
export function fingerprint(value){return crypto.createHash('sha256').update(JSON.stringify(stable(value))).digest('hex')}
export function requireIdempotencyKey(req){
  const key=String(req.headers['idempotency-key']||'').trim();
  if(!/^[A-Za-z0-9._:-]{8,160}$/.test(key)){const e=new Error('Valid Idempotency-Key header is required');e.status=400;e.code='IDEMPOTENCY_KEY_REQUIRED';throw e}
  return key;
}
function fullKey(user,scope,key){return `${String(user).toLowerCase()}:${scope}:${key}`}
export async function runIdempotent({user,scope,key,input,ttlMs=24*60*60*1000,work}){
  const idemKey=fullKey(user,scope,key),fp=fingerprint(input),expiresAt=new Date(Date.now()+ttlMs);
  if(databaseConfigured()){
    const sql=await db();
    await sql`delete from tcc_idempotency where expires_at < now()`;
    const inserted=await sql`insert into tcc_idempotency (idem_key,fingerprint,status,expires_at,created_at,updated_at)
      values (${idemKey},${fp},'pending',${expiresAt.toISOString()}::timestamptz,now(),now())
      on conflict (idem_key) do nothing returning idem_key`;
    if(!inserted.length){
      const rows=await sql`select fingerprint,status,response from tcc_idempotency where idem_key=${idemKey} limit 1`;const row=rows[0];
      if(!row){const e=new Error('Idempotency state unavailable');e.status=503;throw e}
      if(row.fingerprint!==fp){const e=new Error('Idempotency-Key was already used with a different request');e.status=409;e.code='IDEMPOTENCY_CONFLICT';throw e}
      if(row.status==='done') return {replayed:true,value:row.response};
      const e=new Error('An identical request is already in progress');e.status=409;e.code='IDEMPOTENCY_IN_PROGRESS';throw e;
    }
    try{const value=await work();await sql`update tcc_idempotency set status='done',response=${JSON.stringify(value)}::jsonb,updated_at=now() where idem_key=${idemKey}`;return {replayed:false,value}}
    catch(e){await sql`delete from tcc_idempotency where idem_key=${idemKey} and status='pending'`;throw e}
  }
  const storeKey=`tcc:idem:${idemKey}`,existing=await getJson(storeKey);
  if(existing&&Date.parse(existing.expiresAt||'')>Date.now()){
    if(existing.fingerprint!==fp){const e=new Error('Idempotency-Key was already used with a different request');e.status=409;e.code='IDEMPOTENCY_CONFLICT';throw e}
    if(existing.status==='done')return {replayed:true,value:existing.response};
    const e=new Error('An identical request is already in progress');e.status=409;e.code='IDEMPOTENCY_IN_PROGRESS';throw e;
  }
  await setJson(storeKey,{fingerprint:fp,status:'pending',expiresAt:expiresAt.toISOString()});
  try{const value=await work();await setJson(storeKey,{fingerprint:fp,status:'done',response:value,expiresAt:expiresAt.toISOString()});return {replayed:false,value}}
  catch(e){await deleteJson(storeKey);throw e}
}
