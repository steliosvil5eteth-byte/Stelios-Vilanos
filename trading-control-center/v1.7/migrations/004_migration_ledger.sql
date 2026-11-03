create table if not exists tcc_migrations (
  version integer primary key,
  name text not null,
  applied_at timestamptz not null default now()
);
create index if not exists tcc_migrations_applied_idx on tcc_migrations (applied_at);
insert into tcc_meta (key,value,updated_at) values ('schema_version','4',now())
on conflict (key) do update set value=excluded.value,updated_at=now();
