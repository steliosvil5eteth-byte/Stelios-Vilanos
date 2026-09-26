create table if not exists tcc_idempotency (
  idem_key text primary key,
  fingerprint text not null,
  status text not null,
  response jsonb,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists tcc_idempotency_expires_idx on tcc_idempotency (expires_at);
