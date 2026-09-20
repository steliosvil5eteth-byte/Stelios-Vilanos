import {requireAdmin} from '../_lib/access.js';
import {allAccounts} from '../_lib/accounts.js';
import {getJson} from '../_lib/store.js';
import {verifyAuditChain} from '../_lib/audit-chain.js';
import {requestId} from '../_lib/request-trace.js';
export default async function handler(req,res){try{const rid=requestId(req,res);await requireAdmin(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const users=await allAccounts(),reports=[];for(const u of users){const rows=(await getJson(`tcc:${u.username}:audit`))||[];reports.push({username:u.username,rows:rows.length,...verifyAuditChain(rows)})}const ok=reports.every(x=>x.ok);return res.status(ok?200:409).json({requestId:rid,ok,reports})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
