const checks=[
 ['SESSION_SECRET',Boolean(process.env.SESSION_SECRET&&process.env.SESSION_SECRET.length>=32),'Use >=32 random characters'],
 ['DATABASE_URL',Boolean(process.env.DATABASE_URL),'Required for production persistence'],
 ['CRON_SECRET',Boolean(process.env.CRON_SECRET),'Required for scheduled scans/monitoring'],
 ['BACKUP_EXPORT_SECRET',Boolean(process.env.BACKUP_EXPORT_SECRET&&process.env.BACKUP_EXPORT_SECRET.length>=24),'Required for protected full backups'],
 ['APP_BASE_URL',/^https:\/\//i.test(process.env.APP_BASE_URL||''),'Required for email links and test checkout redirects'],
];
let ok=true;for(const [name,pass,note] of checks){console.log(`${pass?'OK ':'ERR'} ${name} — ${note}`);if(!pass)ok=false}
const email=String(process.env.EMAIL_MODE||'disabled').toLowerCase();console.log(`INFO email — mode=${email}; configured=${email==='resend'&&String(process.env.RESEND_API_KEY||'').startsWith('re_')&&String(process.env.EMAIL_FROM||'').includes('@')}`);
const billingMode=String(process.env.BILLING_MODE||'disabled').toLowerCase(),testBilling=billingMode==='stripe_test'&&String(process.env.STRIPE_SECRET_KEY||'').startsWith('sk_test_');console.log(`INFO billing — mode=${billingMode}; safe test enabled=${testBilling}; live billing is unsupported`);
console.log(`INFO market data — Alpha Vantage=${process.env.ALPHAVANTAGE_API_KEY?'configured':'not configured'}; Twelve Data=${process.env.TWELVE_DATA_API_KEY?'configured':'not configured'}; mode=${process.env.MARKET_DATA_PROVIDER||'auto'}; failover=${process.env.MARKET_DATA_FAILOVER||'true'}`);
console.log(`INFO IBKR — ${process.env.IBKR_BASE_URL&&process.env.IBKR_ACCOUNT_ID?'configured':'not configured'}; PAPER execution=${String(process.env.IBKR_PAPER_EXECUTION_ENABLED||'false')}`);
if(!ok)process.exitCode=2;else console.log('production readiness: PASS');
