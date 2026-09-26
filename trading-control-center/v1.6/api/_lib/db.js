let clientPromise=null;
export function databaseConfigured(){return Boolean(process.env.DATABASE_URL)}
export async function db(){
  if(!databaseConfigured()) return null;
  if(!clientPromise) clientPromise=(async()=>{
    const mod=await import('postgres');
    const postgres=mod.default;
    const sql=postgres(process.env.DATABASE_URL,{max:1,prepare:false,idle_timeout:20,connect_timeout:10,ssl:'require'});
    await sql`create table if not exists tcc_kv (key text primary key, value jsonb not null, updated_at timestamptz not null default now())`;
    await sql`create table if not exists tcc_rate_limits (bucket_key text primary key, window_start bigint not null, count integer not null, updated_at timestamptz not null default now())`;
    await sql`create table if not exists tcc_usage (username text not null, month text not null, feature text not null, count bigint not null default 0, updated_at timestamptz not null default now(), primary key (username,month,feature))`;
    await sql`create table if not exists tcc_idempotency (idem_key text primary key, fingerprint text not null, status text not null, response jsonb, expires_at timestamptz not null, created_at timestamptz not null default now(), updated_at timestamptz not null default now())`;
    await sql`create table if not exists tcc_meta (key text primary key, value text not null, updated_at timestamptz not null default now())`;
    await sql`insert into tcc_meta (key,value,updated_at) values ('schema_version','3',now()) on conflict (key) do nothing`;
    return sql;
  })();
  return clientPromise;
}
export async function dbPing(){
  const start=Date.now(); const sql=await db(); if(!sql)return {configured:false,ok:false,latencyMs:null};
  try{await sql`select 1 as ok`;return {configured:true,ok:true,latencyMs:Date.now()-start}}catch(e){return {configured:true,ok:false,latencyMs:Date.now()-start,error:e.message}}
}
