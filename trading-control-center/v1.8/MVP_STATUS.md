# Trading Signal Center — MVP Status

Updated: 2026-09-25

## Ready in code

- Signal-only product mode. No live trading endpoint is exposed in the UI.
- Legacy broker-paper features are disabled in all signal-first plans.
- LONG and SHORT technical scoring.
- Hard display gate: technical score >= 95/100.
- Event/news confirmation layer with separate event score.
- Combined technical + event release gate.
- 5-minute intraday signal data mode.
- Stock and crypto symbol formats.
- 5% per-trade stop reference.
- 5–10% target range.
- 10% monthly paper/research loss lock.
- Data quality checks and optional liquidity threshold.
- Market/news caching to reduce free API usage.
- Read-only manual holdings import.
- Existing-position/concentration context on signals.
- Forward-test ledger for LONG and SHORT.
- One open signal per symbol to prevent duplicate signal spam.
- Signal expiry based on bar interval and max holding window.
- Empirical hit-rate/calibration metrics separate from model score.
- 30 closed-signal sample gate before presenting win rate as a KPI.
- In-app 95+ signal alerts.
- Opt-in email alerts for eligible plans.
- Active Watch while the app is open.
- Disabled-by-default server auto-watch endpoint.
- Demo €0 / Starter €10.01 / Pro €30 plan model.
- Updated signal-first Terms and Risk drafts.
- Provider-aware health and production-readiness checks.
- GitHub CI validation for the signal-first branch.

## Plan model

### Demo — €0
- Up to 2 watchlist symbols
- Up to 5 imported holdings
- Manual scans
- No signal email alerts
- No automatic watch
- No broker execution

### Starter — €10.01/month
- Up to 10 watchlist symbols
- Up to 25 imported holdings
- Signal email alerts
- Active Watch every 30 minutes, up to 3 auto-watch symbols
- No broker execution

### Pro — €30/month
- Up to 25 watchlist symbols
- Up to 100 imported holdings
- Signal email alerts
- Active Watch every 5 minutes, up to 5 auto-watch symbols
- Export entitlement
- No broker execution

## Safety rules

- A 95/100 model score is not a 95% probability of profit.
- Signals are not guarantees.
- The user decides whether to execute a transaction.
- The 5% stop is a model reference; gaps/slippage can exceed it.
- The 5–10% target is a target, not a promised return.
- Commercial personalized advice/execution must remain disabled unless the regulatory structure is resolved.

## External requirements before real production use

1. Restore authorized Vercel access for the project/team.
2. Configure a Twelve Data key if 5-minute intraday signals remain required.
3. Configure an Alpha Vantage key if directional event/news confirmation remains required.
4. Configure persistent storage (DATABASE_URL) for production.
5. Configure email provider only if email alerts are enabled.
6. Keep live billing disabled until commercial/legal/tax setup is complete.
7. Obtain legal/regulatory review before commercial personalized recommendations.
8. Validate market-data commercial usage rights before selling access.

## Validation

The signal-first validation suite currently covers:

- scanner-smoke
- event-smoke
- short-ledger-smoke
- signal-features-smoke
- plan-watch-smoke
- portfolio-smoke
- commercial smoke
- v1.8 regression smoke
- full validate suite

Current branch: `trading-control-center-signal-first`
Draft PR: #8
