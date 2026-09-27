import {db,databaseConfigured} from './db.js';
import {getJson,setJson} from './store.js';
const locks=new Map();
// All bot state, fills, tick watermark and P&L persist atomically in one row.
export async function mutateBot(user,update){
  const key=`tcc:${user}:paperBot`;
  if(databaseConfigured()){
    const sql=await db();
    return sql.begin(async tx=>{
      await tx`select pg_advisory_xact_lock(hashtextextended(${key},0))`;
      const rows=await tx`select value from tcc_kv where key=${key} for update`;
      const next=update(rows[0]?.value||null);
      if(next===undefined)throw new Error('Invalid bot update');
      await tx`insert into tcc_kv(key,value,updated_at) values(${key},${JSON.stringify(next)}::jsonb,now()) on conflict(key) do update set value=excluded.value,updated_at=now()`;
      return next;
    });
  }
  if(process.env.BOT_LOCAL_DEMO!=='true'||process.env.NODE_ENV==='production')throw Object.assign(new Error('BOT_DATABASE_REQUIRED'),{status:503});
  const previous=locks.get(key)||Promise.resolve();
  const pending=previous.catch(()=>{}).then(async()=>{const next=update(structuredClone(await getJson(key)));await setJson(key,next);return next;});
  locks.set(key,pending);try{return await pending;}finally{if(locks.get(key)===pending)locks.delete(key);}
}
export async function readBot(user){return getJson(`tcc:${user}:paperBot`);}
