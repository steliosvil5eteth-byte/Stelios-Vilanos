import {databaseConfigured,db} from './db.js';
import {REQUIRED_SCHEMA_VERSION} from './release.js';

const migrations=[
  {version:1,name:'base-kv',run:async sql=>{await sql`create table if not exists tcc_kv (key text primary key, value jsonb not null, updated_at timestamptz not null default now())`;await sql`create table if not exists tcc_rate_limits (bucket_key text primary key, window_start bigint not null, count integer not null, updated_at timestamptz not null default now())`;await sql`create table if not exists tcc_usage (username text not null, month text not null, feature text not null, count bigint not null default 0, updated_at timestamptz not null default now(), primary key (username,month,feature))`}},
  {version:2,name:'idempotency',run:async sql=>{await sql`create table if not exists tcc_idempotency (idem_key text primary key, fingerprint text not null, status text not null, response jsonb, expires_at timestamptz not null, created_at timestamptz not null default now(), updated_at timestamptz not null default now())`;await sql`create index if not exists tcc_idempotency_expires_idx on tcc_idempotency (expires_at)`}},
  {version:3,name:'release-state',run:async sql=>{await sql`create table if not exists tcc_meta (key text primary key, value text not null, updated_at timestamptz not null default now())`}},
  {version:4,name:'migration-ledger',run:async sql=>{await sql`create table if not exists tcc_migrations (version integer primary key, name text not null, applied_at timestamptz not null default now())`;await sql`create index if not exists tcc_migrations_applied_idx on tcc_migrations (applied_at)`}},
{version:5,name:'ops-observability',run:async sql=>{await sql`insert into tcc_meta (key,value,updated_at) values ('ops_observability','enabled',now()) on conflict (key) do update set value=excluded.value,updated_at=now()`}}
];

export async function migrationStatus(){
  if(!databaseConfigured())return {configured:false,current:0,required:REQUIRED_SCHEMA_VERSION,pending:migrations.map(x=>x.version)};
  const sql=await db();
  await sql`create table if not exists tcc_migrations (version integer primary key, name text not null, applied_at timestamptz not null default now())`;
  const rows=await sql`select version,name,applied_at from tcc_migrations order by version`;
  const applied=new Set(rows.map(x=>Number(x.version)));
  const pending=migrations.filter(x=>!applied.has(x.version)).map(x=>({version:x.version,name:x.name}));
  return {configured:true,current:rows.length?Math.max(...rows.map(x=>Number(x.version))):0,required:REQUIRED_SCHEMA_VERSION,applied:rows,pending,ok:pending.length===0};
}

export async function runMigrations(){
  if(!databaseConfigured()){const e=new Error('DATABASE_URL is not configured');e.status=503;throw e}
  const sql=await db();
  return sql.begin(async tx=>{
    await tx`select pg_advisory_xact_lock(78160417)`;
    await tx`create table if not exists tcc_migrations (version integer primary key, name text not null, applied_at timestamptz not null default now())`;
    const rows=await tx`select version from tcc_migrations`;
    const applied=new Set(rows.map(x=>Number(x.version))),ran=[];
    for(const m of migrations){
      if(applied.has(m.version))continue;
      await m.run(tx);
      await tx`insert into tcc_migrations (version,name,applied_at) values (${m.version},${m.name},now()) on conflict (version) do nothing`;
      await tx`insert into tcc_meta (key,value,updated_at) values ('schema_version',${String(m.version)},now()) on conflict (key) do update set value=excluded.value,updated_at=now()`;
      ran.push({version:m.version,name:m.name});
    }
    return {ran,finalVersion:migrations.at(-1).version};
  });
}
