import {getJson,setJson} from './store.js';
import {dbPing} from './db.js';
import {emailConfig,sendEmail} from './email.js';
import {billingConfig} from './billing.js';
import {marketDataConfig} from './market-data.js';
import {getSafetyState} from './safety.js';
import {getMaintenanceState} from './maintenance.js';
import {migrationStatus} from './migrations.js';
import {getReleaseControl} from './release-control.js';
const KEY='tcc:monitoring:events';
export async function systemSnapshot(){const database=await dbPing(),email=emailConfig(),billing=billingConfig(),marketData=marketDataConfig(),safety=await getSafetyState(),maintenance=await getMaintenanceState(),migrations=await migrationStatus(),release=await getReleaseControl();const warnings=[];if(process.env.NODE_ENV==='production'&&!database.configured)warnings.push('DATABASE_URL not configured');if(process.env.NODE_ENV==='production'&&!email.configured)warnings.push('Transactional email not configured');if(process.env.NODE_ENV==='production'&&!marketData.alphaConfigured&&!marketData.twelveConfigured)warnings.push('No market-data provider configured');if(billing.mode!=='disabled'&&!billing.enabled)warnings.push('Billing mode configured but Stripe test safety checks failed');return {ts:new Date().toISOString(),database,email:{mode:email.mode,configured:email.configured},billing:{mode:billing.mode,enabled:billing.enabled,testMode:billing.testMode},marketData,safety,maintenance,migrations,release,paperOnly:true,liveExecution:false,warnings,ok:database.configured?database.ok&&warnings.length===0:warnings.length===0}}
export async function recordMonitoringEvent({severity='info',type='SYSTEM_CHECK',detail=''}={}){const rows=(await getJson(KEY))||[];const row={ts:new Date().toISOString(),severity:String(severity).slice(0,20),type:String(type).slice(0,60),detail:String(detail).slice(0,500)};rows.unshift(row);await setJson(KEY,rows.slice(0,500));return row}
export async function monitoringEvents(limit=100){const rows=(await getJson(KEY))||[];return rows.slice(0,Math.max(1,Math.min(500,Number(limit)||100)))}
export async function runHealthMonitor(){const snap=await systemSnapshot();const severity=snap.ok?'info':'critical';const event=await recordMonitoringEvent({severity,type:'HEALTH_CHECK',detail:snap.warnings.join(' | ')||'OK'});if(!snap.ok&&process.env.ADMIN_ALERT_EMAIL){try{await sendEmail({to:process.env.ADMIN_ALERT_EMAIL,subject:'Trading Control Center production alert',text:`Health check failed at ${snap.ts}: ${snap.warnings.join(' | ')}`,idempotencyKey:`health-${snap.ts.slice(0,13)}`})}catch{}}return {snapshot:snap,event}}
