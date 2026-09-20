import h0 from '../server/api/account/contact.js';
import h1 from '../server/api/account/delete.js';
import h2 from '../server/api/account/export.js';
import h3 from '../server/api/account.js';
import h4 from '../server/api/admin/audit-verify.js';
import h5 from '../server/api/admin/backup-verify.js';
import h6 from '../server/api/admin/backup.js';
import h7 from '../server/api/admin/deployment-manifest.js';
import h8 from '../server/api/admin/incident.js';
import h9 from '../server/api/admin/integrity.js';
import h10 from '../server/api/admin/maintenance.js';
import h11 from '../server/api/admin/migrations.js';
import h12 from '../server/api/admin/monitoring.js';
import h13 from '../server/api/admin/overview.js';
import h14 from '../server/api/admin/password-reset.js';
import h15 from '../server/api/admin/preflight.js';
import h16 from '../server/api/admin/promotion-gate.js';
import h17 from '../server/api/admin/recovery-check.js';
import h18 from '../server/api/admin/release-control.js';
import h19 from '../server/api/admin/retention.js';
import h20 from '../server/api/admin/safety.js';
import h21 from '../server/api/admin/security.js';
import h22 from '../server/api/admin/slo.js';
import h23 from '../server/api/admin/system.js';
import h24 from '../server/api/admin/usage.js';
import h25 from '../server/api/admin/users.js';
import h26 from '../server/api/alerts.js';
import h27 from '../server/api/audit.js';
import h28 from '../server/api/auth/csrf.js';
import h29 from '../server/api/auth/email/confirm.js';
import h30 from '../server/api/auth/email/request.js';
import h31 from '../server/api/auth/login.js';
import h32 from '../server/api/auth/logout.js';
import h33 from '../server/api/auth/me.js';
import h34 from '../server/api/auth/password/forgot.js';
import h35 from '../server/api/auth/password/reset.js';
import h36 from '../server/api/auth/password-reset/complete.js';
import h37 from '../server/api/auth/register.js';
import h38 from '../server/api/billing/checkout.js';
import h39 from '../server/api/billing/status.js';
import h40 from '../server/api/billing/webhook.js';
import h41 from '../server/api/broker/ibkr/monitor.js';
import h42 from '../server/api/broker/ibkr/paper-bracket.js';
import h43 from '../server/api/broker/ibkr/preview.js';
import h44 from '../server/api/broker/ibkr/reconcile.js';
import h45 from '../server/api/broker/ibkr/reply.js';
import h46 from '../server/api/broker/ibkr/resolve.js';
import h47 from '../server/api/broker/ibkr/status.js';
import h48 from '../server/api/broker/order.js';
import h49 from '../server/api/broker/whatif.js';
import h50 from '../server/api/consent.js';
import h51 from '../server/api/cron/daily-scan.js';
import h52 from '../server/api/cron/monitor.js';
import h53 from '../server/api/health.js';
import h54 from '../server/api/journal.js';
import h55 from '../server/api/library.js';
import h56 from '../server/api/market.js';
import h57 from '../server/api/onboarding.js';
import h58 from '../server/api/performance.js';
import h59 from '../server/api/portfolio.js';
import h60 from '../server/api/profile.js';
import h61 from '../server/api/release.js';
import h62 from '../server/api/report.js';
import h63 from '../server/api/scans.js';
import h64 from '../server/api/signals.js';
import h65 from '../server/api/state.js';
import h66 from '../server/api/strategies.js';
import h67 from '../server/api/trades.js';
import h68 from '../server/api/usage.js';

const routes = new Map([
  ['account/contact', h0],
  ['account/delete', h1],
  ['account/export', h2],
  ['account', h3],
  ['admin/audit-verify', h4],
  ['admin/backup-verify', h5],
  ['admin/backup', h6],
  ['admin/deployment-manifest', h7],
  ['admin/incident', h8],
  ['admin/integrity', h9],
  ['admin/maintenance', h10],
  ['admin/migrations', h11],
  ['admin/monitoring', h12],
  ['admin/overview', h13],
  ['admin/password-reset', h14],
  ['admin/preflight', h15],
  ['admin/promotion-gate', h16],
  ['admin/recovery-check', h17],
  ['admin/release-control', h18],
  ['admin/retention', h19],
  ['admin/safety', h20],
  ['admin/security', h21],
  ['admin/slo', h22],
  ['admin/system', h23],
  ['admin/usage', h24],
  ['admin/users', h25],
  ['alerts', h26],
  ['audit', h27],
  ['auth/csrf', h28],
  ['auth/email/confirm', h29],
  ['auth/email/request', h30],
  ['auth/login', h31],
  ['auth/logout', h32],
  ['auth/me', h33],
  ['auth/password/forgot', h34],
  ['auth/password/reset', h35],
  ['auth/password-reset/complete', h36],
  ['auth/register', h37],
  ['billing/checkout', h38],
  ['billing/status', h39],
  ['billing/webhook', h40],
  ['broker/ibkr/monitor', h41],
  ['broker/ibkr/paper-bracket', h42],
  ['broker/ibkr/preview', h43],
  ['broker/ibkr/reconcile', h44],
  ['broker/ibkr/reply', h45],
  ['broker/ibkr/resolve', h46],
  ['broker/ibkr/status', h47],
  ['broker/order', h48],
  ['broker/whatif', h49],
  ['consent', h50],
  ['cron/daily-scan', h51],
  ['cron/monitor', h52],
  ['health', h53],
  ['journal', h54],
  ['library', h55],
  ['market', h56],
  ['onboarding', h57],
  ['performance', h58],
  ['portfolio', h59],
  ['profile', h60],
  ['release', h61],
  ['report', h62],
  ['scans', h63],
  ['signals', h64],
  ['state', h65],
  ['strategies', h66],
  ['trades', h67],
  ['usage', h68],
]);

function normalizeRoute(value){
  if(Array.isArray(value)) value=value.join('/');
  return decodeURIComponent(String(value||'')).replace(/^\/+|\/+$/g,'');
}

export default async function handler(req,res){
  const key=normalizeRoute(req.query?.__route);
  const fn=routes.get(key);
  if(!fn) return res.status(404).json({error:'Not found',route:key});
  if(req.query && Object.prototype.hasOwnProperty.call(req.query,'__route')) delete req.query.__route;
  return fn(req,res);
}
