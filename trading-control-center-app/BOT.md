# Paper bot — implementation and operating status

## Delivered

- `/bot.html`: mobile page linked from the existing app; existing login/CSRF applies.
- `/api/bot`: create, start, pause, tick and read. Uses only virtual EUR and BTC/EUR spot quotes. No live orders, leverage, exchange credentials or real billing.
- Plans: Demo free, A proposed €10/month (capital ≤€100), B proposed €30/month (≤€500). These are simulation profiles, not paid entitlements. Legacy Control Center subscriptions are separate and unchanged.
- Stop trigger 5% below simulated entry; target 10% above entry; one position at a time. Quantity budgets approximately 1% of equity including assumed fees/slippage. No borrowed funds.
- Monthly loss trigger 10% of starting monthly equity including unrealized P&L; monthly profit triggers €200 (Demo/A) / €1,000 (B). Halt is sticky until the next Athens calendar month. These are stop thresholds, NOT achievable return promises or guaranteed maximum losses.
- Fees 0.1% per side and slippage 0.1% per side are explicit simulation assumptions, not current broker quotes. Fill uses the observed bid/ask plus assumptions. Polling can miss intraminute crossings and gaps can exceed stops.
- Replays/out-of-order quotes cannot duplicate a position. PostgreSQL transaction and advisory lock serialize concurrent updates and store balance, position, complete fills and tick watermark atomically. Redis is not supported for bot writes. Memory mode requires `BOT_LOCAL_DEMO=true` and is prohibited in production.
- Public OKX completed 1-minute candles + ticker. Reject invalid/stale/future quotes, stale or gapped candles and wide spreads. BTC/EUR availability must be verified for deployment region; no silent currency conversion or USDT substitution.
- GDELT Bitcoin English headlines, cache 5 minutes. Missing feed blocks entries but not exits when quotes are available. Negative-keyword filter is experimental context, NOT a trained news model or a 95% probability estimate. GDELT seen time is not article publication time; this is polling, not instant news ingestion.
- Existing global paper gate, verified email, current consent, auth, CSRF and maintenance policy remain effective. Pause disables entries; stops/targets require subsequent ticks. Global entry gate is checked each cycle. Maintenance stops writes, including ticks.

## Run

Use the existing deployment with PostgreSQL (`DATABASE_URL`), existing authentication and current schema migrations. Install the existing package dependencies with `npm ci`. No new package, paid API or purchased service is needed for this code.

1. Visit `/bot.html` after signing in. Create a simulation; creation cannot reset an existing ledger/monthly loss limit.
2. Existing admin enables the normal two-key paper gate only after operational verification. The account must already have verified email and accepted current disclosures.
3. Start entries. The open browser requests a tick every 60 seconds; mobile background suspension can stop it.
4. For unattended operation on an EXISTING always-on machine, set `BOT_BASE_URL` to the deployment HTTPS URL and `CRON_SECRET` to its existing server secret; server must have `BOT_USERNAME` set to the intended account. Run `npm run bot-worker`. The worker only calls the simulated API; it does not start disabled entries.
5. `BOT_RUN_ONCE=true npm run bot-worker` performs one integration check. Never commit real secrets. No continuously running worker or paid hosting was provisioned by this change.

## Verification

`npm run validate` includes core and authenticated API integration tests, plus all prior suites. `npm run preflight`, `npm run release-check`, `npm run ops-check` retain paper-only defaults.

Core coverage: entry, stop/target exits, fee P&L accounting, loss/profit halts, stale/invalid data, unavailable/negative news, pause with protective exit, replay, concurrent local updates, failed update rollback, provider schema.
API coverage: unauthenticated rejection, CSRF rejection, no ledger reset, email/consent/safety gate, router integration, start/tick/replay/pause/read.

These use deterministic fixtures. They do not establish strategy returns, 95% accuracy, PostgreSQL concurrency in a live server, or working provider access from production.

## Remaining release blockers

- Live OKX access could not be confirmed from the execution environment (gateway returned `Site Unavailable`). GDELT live response and regional BTC/EUR support need verification from the hosting environment.
- Production database transaction behavior, current auth setup and Vercel runtime have not been validated for this change.
- No worker is running continuously yet. Stale/unavailable data blocks entries; no invented prices are used.
- Start with forward paper evaluation and report actual sample size, P&L and drawdown. No claim of guaranteed profits or 95% success is supported.

## Data references

- https://www.okx.com/docs-v5/en/ — public market ticker and completed candles.
- https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ — DOC API article list.

Vercel project check returned HTTP 403 for team `steliosvil5eteth-9734`: connection must be re-authenticated for that scope. No production deployment or execution switch was changed.
