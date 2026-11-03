# Vercel setup required for Trading Control Center v1.8

A GitHub Actions preview probe was executed on 2026-09-20.

Result: deployment did **not** start because all three required GitHub Actions secrets are currently missing:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

No credential values are stored in this repository.

## One-time Vercel setup

1. Sign in to Vercel.
2. Add New → Project.
3. Import GitHub repository `steliosvil5eteth-byte/Stelios-Vilanos`.
4. Set the project Root Directory to:
   `trading-control-center/v1.8`
5. Keep the first deployment in preview/test configuration. Do not enable IBKR paper execution or billing yet.
6. Create a Vercel access token in Vercel account/team settings.
7. Copy the Vercel Team/Org ID and Project ID from the linked project's settings or `.vercel/project.json` after linking.
8. In GitHub repository Settings → Secrets and variables → Actions, create repository secrets:
   - `VERCEL_TOKEN`
   - `VERCEL_ORG_ID`
   - `VERCEL_PROJECT_ID`

## What happens next automatically

The workflow `Trading Control Center Vercel Preview Probe` can then perform:

1. credential check
2. npm install
3. validate
4. preflight
5. release-check
6. ops-check
7. `vercel pull --environment=preview`
8. preview build
9. preview deployment

Production deployment remains separate and manual.

## Runtime environment still required after project link

Minimum production-like preview variables:

- `SESSION_SECRET`
- `DATABASE_URL`
- `CRON_SECRET`
- `BACKUP_EXPORT_SECRET`
- `APP_BASE_URL`
- one supported market-data API key

Safety defaults should remain:

- `PAPER_EXECUTION_ENABLED=false`
- `IBKR_PAPER_EXECUTION_ENABLED=false`
- `BILLING_MODE=disabled`

Live trading is not implemented.
