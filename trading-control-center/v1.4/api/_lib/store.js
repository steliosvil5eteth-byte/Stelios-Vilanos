import {databaseConfigured,db} from './db.js';
const mem = globalThis.__TCC_MEM__ || (globalThis.__TCC_MEM__ = new Map());
function redisCfg(){return {url:process.env.KV_REST_API_URL||process.env.UPSTASH_REDIS_REST_URL||'',token:process.env.KV_REST_API_TOKEN||process.env.UPSTASH_REDIS_REST_TOKEN||''}}
export function redisStoreConfigured(){const c=redisCfg();return Boolean(c.url&&c.token)}
export function persistentStoreConfigured(){return databaseConfigured()||redisStoreConfigured()}
export function storageBackend(){return databaseConfigured()?'postgres':redisStoreConfigured()?'redis':'memory'}
async function redis(cmd){
  const c=redisCfg();
  const r=await fetch(c.url,{method:'POST',headers:{Authorization:`Bearer ${c.token}`,'Content-Type':'application/json'},body:JSON.stringify(cmd)});
  if(!r.ok) throw new Error(`store HTTP ${r.status}`);
  const j=await r.json(); if(j.error) throw new Error(j.error); return j.result;
}
export async function getJson(key){
  if(databaseConfigured()){
    const sql=await db(); const rows=await sql`select value from tcc_kv where key=${key} limit 1`; return rows[0]?.value??null;
  }
  if(redisStoreConfigured()){
    const v=await redis(['GET',key]); if(v==null) return null; try{return JSON.parse(v)}catch{return null}
  }
  return mem.get(key) ?? null;
}
export async function setJson(key,value){
  if(databaseConfigured()){
    const sql=await db(); const payload=JSON.stringify(value);
    await sql`insert into tcc_kv (key,value,updated_at) values (${key},${payload}::jsonb,now()) on conflict (key) do update set value=excluded.value,updated_at=now()`; return;
  }
  if(redisStoreConfigured()){await redis(['SET',key,JSON.stringify(value)]);return}
  mem.set(key,value);
}
export async function deleteJson(key){
  if(databaseConfigured()){const sql=await db();await sql`delete from tcc_kv where key=${key}`;return}
  if(redisStoreConfigured()){await redis(['DEL',key]);return}
  mem.delete(key);
}
export async function appendAudit(user,item){
  const key=`tcc:${user}:audit`; const a=(await getJson(key))||[]; a.unshift(item); await setJson(key,a.slice(0,500)); return a.slice(0,500);
}
