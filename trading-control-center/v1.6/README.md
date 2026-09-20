# Trading Control Center v1.4

Multi-user market-research and paper-trading application. This release remains **paper-only** and **test-billing-only**. There is no live-trading endpoint and no live Stripe charging mode.

## What v1.4 adds

### 1. Idempotent paper-order execution

The simulated paper-order endpoint, IBKR paper bracket endpoint and IBKR broker-reply endpoint now require an `Idempotency-Key` header.

- Repeating the same request with the same key returns the original result.
- Reusing the same key with a different payload is rejected with `IDEMPOTENCY_CONFLICT`.
- PostgreSQL uses a dedicated `tcc_idempotency` table to make the safety gate atomic across concurrent serverless requests.
- Memory/Redis fallback remains available for local development.
- Browser order actions reuse the same key for an identical request for ten minutes, reducing duplicate orders caused by double taps, mobile retries or uncertain network responses.

Stripe test webhooks use the same idempotency engine with the Stripe event ID and a 90-day retention window. A replayed signed event therefore cannot repeatedly change plan state.

### 2. Forward-test signal ledger

Accepted scanner ideas are now stored separately from actual paper trades. The ledger records:

- strategy version,
- symbol,
- signal date,
- score,
- entry / stop / target,
- OOS metrics available when the signal was created,
- market-data provider,
- final forward outcome (`STOP`, `TARGET`, or `TIME`),
- realized R-multiple after configured slippage/commission assumptions.

On a later scan, new daily bars reconcile older open signals. If stop and target are both touched on the same bar, the stop is evaluated first. This deliberately conservative convention matches the existing backtest model.

Endpoint:

`GET /api/signals?limit=100`

This ledger is research evidence. It does **not** create a broker order automatically.

### 3. Market-data provider failover

v1.4 supports two daily-data adapters:

- Alpha Vantage
- Twelve Data

Configuration:

```env
MARKET_DATA_PROVIDER=auto
MARKET_DATA_FAILOVER=true
ALPHAVANTAGE_API_KEY=
ALPHAVANTAGE_OUTPUTSIZE=compact
TWELVE_DATA_API_KEY=
TWELVE_DATA_OUTPUTSIZE=1000
```

When failover is enabled, a provider error can fall through to the secondary provider. Every returned dataset records which provider actually supplied it. The scanner run also records the provider set used for that run.

Twelve Data's official `/time_series` endpoint supports `interval=1day` and historical output sizing; provider limits and commercial redistribution terms must be checked before a paid launch.

### 4. Production monitoring extensions

Health snapshots now include market-data-provider configuration. Production monitoring warns when no market-data provider is configured.

`GET /api/health` additionally reports:

- `idempotentOrders=true`
- `webhookReplayProtection=true`
- `forwardSignalLedger=true`
- configured market-data providers
- `paperOnly=true`
- `liveExecution=false`

## Existing safety gates retained

- IBKR paper submission requires the broker account/session to report paper mode.
- `IBKR_PAPER_EXECUTION_ENABLED` is still a separate server-side switch.
- Broker warnings require explicit confirmation.
- Verified email and current Terms/Risk consent are required before paper execution.
- Strategy lifecycle can block execution.
- Portfolio risk limits and monthly plan quotas remain server-side.
- Billing supports only `BILLING_MODE=stripe_test` with an `sk_test_` secret.
- A `sk_live_` key does not enable billing.
- `liveExecution=false` remains hard-coded in health/monitoring output.

## Storage priority

1. PostgreSQL via `DATABASE_URL` — recommended production backend.
2. Redis REST / Upstash-compatible storage.
3. Process memory — development/testing only.

Migrations:

- `migrations/001_init.sql`
- `migrations/002_idempotency.sql`

The runtime database adapter also creates required tables defensively if they do not exist.

## Validation

```bash
npm run validate
```

The validation suite covers all earlier releases plus v1.4 tests for:

- duplicate request replay,
- idempotency fingerprint conflicts,
- Twelve Data parsing,
- Alpha Vantage → Twelve Data failover,
- forward-ledger reconciliation,
- TARGET outcome R-multiple calculation,
- browser/server JavaScript syntax,
- prior scanner, portfolio, account, security, consent and billing-test regression tests.

## Deployment status

The source is Vercel-ready, but a real deployment still requires an authenticated Vercel project plus production environment variables. Do not put broker tokens, database credentials, Stripe secrets or email API keys in GitHub source files.

Recommended minimum production environment:

```env
SESSION_SECRET=<32+ random chars>
DATABASE_URL=<postgres connection>
CRON_SECRET=<random secret>
BACKUP_EXPORT_SECRET=<separate random secret>
APP_BASE_URL=https://your-domain.example
EMAIL_MODE=resend
RESEND_API_KEY=re_...
EMAIL_FROM=Trading Control Center <noreply@your-domain.example>
MARKET_DATA_PROVIDER=auto
MARKET_DATA_FAILOVER=true
```

IBKR paper and Stripe test integrations should remain disabled until their own credentials are configured and separately verified.


## v1.5 production safety hardening

- Two-key global paper-execution gate: `PAPER_EXECUTION_ENABLED=true` plus an admin-controlled stored switch.
- Emergency stop defaults to blocking paper execution on a fresh deployment.
- Stale daily market data is rejected before strategy evaluation; default maximum age is 7 days.
- IBKR reconciliation endpoint reports local/broker mismatches without automatically altering positions.
- Request IDs are emitted on critical operational routes.
- Stricter server-side symbol and order schema validation.
- Live execution remains unavailable.

Admin safety endpoint:
- `GET /api/admin/safety`
- `PUT /api/admin/safety`

IBKR reconciliation:
- `GET /api/broker/ibkr/reconcile`

Environment additions:
```env
PAPER_EXECUTION_ENABLED=false
MARKET_DATA_MAX_AGE_DAYS=7
```


## v1.6 release-candidate controls

- Server-side maintenance/read-only mode. Normal authenticated writes return `423 MAINTENANCE_MODE` while enabled; an admin can still use `/api/admin/maintenance` to turn it off.
- Database schema version metadata (`tcc_meta`, required schema version 3) and migration `003_release_state.sql`.
- Data-integrity audit across accounts, trades, strategies, scan history and forward-test signals.
- Sanitized backup round-trip verification with SHA-256 checksum.
- Admin preflight endpoint combining system health, data integrity, schema status and safety invariants.
- Release metadata and request-safe health reporting retain `liveExecution=false`.

New admin endpoints:
- `GET|PUT /api/admin/maintenance`
- `GET /api/admin/integrity`
- `GET /api/admin/backup-verify`
- `GET /api/admin/preflight`

New local checks:
```bash
npm run validate
npm run preflight
```
