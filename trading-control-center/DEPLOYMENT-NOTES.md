# Trading Control Center v1.4 deployment notes

Current release: v1.4.

Safety invariants:
- paper-only execution
- liveExecution=false
- Stripe test billing only
- IBKR paper session required
- verified email + Terms/Risk consent required
- strategy/risk/plan gates remain server-side

v1.4 additions:
- idempotent simulated/IBKR paper-order flow
- duplicate/retry protection through Idempotency-Key
- Stripe webhook replay protection
- forward-test signal ledger
- Alpha Vantage / Twelve Data market-data failover
- PostgreSQL idempotency table migration
- extended production health/readiness reporting

Deployment still requires an authenticated Vercel project and production environment variables. No secrets should be committed to this repository.
