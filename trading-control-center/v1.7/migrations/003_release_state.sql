create table if not exists tcc_meta (
  key text primary key,
  value text not null,
  updated_at timestamptz not null default now()
);
insert into tcc_meta (key,value,updated_at) values ('schema_version','3',now()) on conflict (key) do update set value=excluded.value,updated_at=now();
