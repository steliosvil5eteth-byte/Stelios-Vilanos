create table if not exists tcc_kv (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists tcc_rate_limits (
  bucket_key text primary key,
  window_start bigint not null,
  count integer not null,
  updated_at timestamptz not null default now()
);

create table if not exists tcc_usage (
  username text not null,
  month text not null,
  feature text not null,
  count bigint not null default 0,
  updated_at timestamptz not null default now(),
  primary key (username, month, feature)
);
