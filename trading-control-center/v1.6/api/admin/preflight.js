import {requireAdmin} from '../_lib/access.js';
import {checkDataIntegrity} from '../_lib/integrity.js';
import {schemaStatus,APP_VERSION} from '../_lib/release.js';
import {systemSnapshot} from '../_lib/monitoring.js';
import {requestId} from '../_lib/request-trace.js';
export default async function handler(req,res){try{const rid=requestId(req,res);await requireAdmin(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const [integrity,schema,system]=await Promise.all([checkDataIntegrity(),schemaStatus(),systemSnapshot()]);const checks={integrity:integrity.ok,schema:schema.configured?schema.ok:true,system:system.ok,liveExecutionOff:system.liveExecution===false,emergencySafety:Boolean(system.safety)};const ready=Object.values(checks).every(Boolean);return res.status(ready?200:409).json({version:APP_VERSION,requestId:rid,ready,checks,integrity,schema,system})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
