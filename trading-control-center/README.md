# Trading Control Center

Production staging area for the paper-only trading research application.

## Safety state
- PAPER trading only
- Live execution disabled
- Billing test mode only
- User confirmation and risk consent required

Current release artifact: v1.3. The application package is validated locally before promotion. Do not place API keys, broker credentials, database URLs, or billing secrets in this repository.

## Deployment gate
Production deployment requires configured hosting, persistent database, application/session secrets, market-data credentials, email provider credentials, and paper-broker connectivity. Live trading remains out of scope.
