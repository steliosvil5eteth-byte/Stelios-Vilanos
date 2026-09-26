# Trading Control Center — deployment checklist

The application source lives in `trading-control-center/v1.4/`.

## GitHub deployment secrets required

Configure these repository/action secrets before running **Trading Control Center Deploy**:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

These values are deployment credentials. Never commit their values to source control.

## Vercel project settings

Set the Vercel **Root Directory** to:

`trading-control-center/v1.4`

Production runtime environment should then be populated from `.env.example`, using real secret values only in Vercel Environment Variables.

Minimum production settings:

- `SESSION_SECRET`
- `DATABASE_URL`
- `CRON_SECRET`
- `BACKUP_EXPORT_SECRET`
- `APP_BASE_URL`
- an approved market-data provider key

Optional integrations remain disabled until separately configured:

- IBKR paper trading
- Resend email
- Stripe test billing

## Safety invariants

- live trading remains disabled
- IBKR orders require a paper session
- Stripe live keys must not enable billing
- no production secret belongs in GitHub source files
