const requireIntraday=String(process.env.SIGNAL_REQUIRE_INTRADAY||'true').toLowerCase()!=='false';
const requireEvents=String(process.env.EVENT_CONFIRMATION_REQUIRED||'true').toLowerCase()!=='false';
const checks=[
 ['SESSION_SECRET',Boolean(process.env.SESSION_SECRET&&process.env.SESSION_SECRET.length>=32),'Use >=32 random characters'],
 ['DATABASE_URL',Boolean(process.env.DATABASE_URL),'Required for production persistence'],
 ['CRON_SECRET',Boolean(process.env.CRON_SECRET),'Required for scheduled scans/monitoring'],
 ['BACKUP_EXPORT_SECRET',Boolean(process.env.BACKUP_EXPORT_SECRET&&process.env.BACKUP_EXPORT_SECRET.length>=24),'Required for protected full backups'],
 ['APP_BASE_URL',/^https:\/\//i.test(process.env.APP_BASE_URL||''),'Required for email links and test checkout redirects'],
 ['TWELVE_DATA_API_KEY',!requireIntraday||Boolean(process.env.TWELVE_DATA_API_KEY),'Required while SIGNAL_REQUIRE_INTRADAY=true'],
 ['ALPHAVANTAGE_API_KEY',!requireEvents||Boolean(process.env.ALPHAVANTAGE_API_KEY),'Required for directional event confirmation while EVENT_CONFIRMATION_REQUIRED=true'],
];
let ok=true;for(const [name,pass,note] of checks){console.log(`${pass?'OK ':'ERR'} ${name} — ${note}`);if(!pass)ok=false}
const email=String(process.env.EMAIL_MODE||'disabled').toLowerCase();console.log(`INFO email — mode=${email}; configured=${email==='resend'&&String(process.env.RESEND_API_KEY||'').startsWith('re_')&&String(process.env.EMAIL_FROM||'').includes('@')}`);
const billingMode=String(process.env.BILLING_MODE||'disabled').toLowerCase(),testBilling=billingMode==='stripe_test'&&String(process.env.STRIPE_SECRET_KEY||'').startsWith('sk_test_');console.log(`INFO billing — mode=${billingMode}; safe test enabled=${testBilling}; live billing is unsupported`);
console.log(`INFO signal market — interval=${process.env.SIGNAL_INTERVAL||'5min'}; intradayRequired=${requireIntraday}; Twelve Data=${process.env.TWELVE_DATA_API_KEY?'configured':'not configured'}`);
console.log(`INFO event confirmation — required=${requireEvents}; Alpha Vantage news=${process.env.ALPHAVANTAGE_API_KEY?'configured':'not configured'}; SEC=${process.env.SEC_USER_AGENT?'configured':'not configured'}`);
console.log('INFO execution — signal-only=true; liveExecution=false; legacy brokerPaper disabled by plan');
console.log(`INFO auto-watch — enabled=${String(process.env.SIGNAL_AUTOWATCH_ENABLED||'false')}`);
if(!ok)process.exitCode=2;else console.log('production readiness: PASS');
