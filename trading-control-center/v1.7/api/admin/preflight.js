import {requireAdmin} from '../_lib/access.js';
import {allAccounts} from '../_lib/accounts.js';
import {getJson} from '../_lib/store.js';
import {checkDataIntegrity} from '../_lib/integrity.js';
import {schemaStatus,APP_VERSION} from '../_lib/release.js';
import {migrationStatus} from '../_lib/migrations.js';
import {getReleaseControl} from '../_lib/release-control.js';
import {verifyAuditChain} from '../_lib/audit-chain.js';
import {systemSnapshot} from '../_lib/monitoring.js';
import {requestId} from '../_lib/request-trace.js';
export default async function handler(req,res){try{const rid=requestId(req,res);await requireAdmin(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const [integrity,schema,migrations,release,system,accounts]=await Promise.all([checkDataIntegrity(),schemaStatus(),migrationStatus(),getReleaseControl(),systemSnapshot(),allAccounts()]);const auditReports=[];for(const a of accounts){const rows=(await getJson(`tcc:${a.username}:audit`))||[];auditReports.push({username:a.username,...verifyAuditChain(rows)})}const auditOk=auditReports.every(x=>x.ok);const checks={integrity:integrity.ok,schema:schema.configured?schema.ok:true,migrations:migrations.configured?migrations.ok:true,system:system.ok,auditChain:auditOk,liveExecutionOff:system.liveExecution===false,emergencySafety:Boolean(system.safety),releaseUnlocked:release.releaseLock===false,maintenanceEnabled:Boolean(system.maintenance?.enabled)};const ready=Object.values(checks).every(Boolean);return res.status(ready?200:409).json({version:APP_VERSION,requestId:rid,ready,checks,integrity,schema,migrations,release,audit:{ok:auditOk,reports:auditReports},system})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
