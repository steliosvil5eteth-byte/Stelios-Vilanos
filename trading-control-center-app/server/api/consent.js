import {requireAccount} from './_lib/access.js';
import {getConsent,acceptConsent} from './_lib/consent.js';
import {appendAudit} from './_lib/store.js';
export default async function handler(req,res){try{const a=await requireAccount(req);if(req.method==='GET')return res.status(200).json({consent:await getConsent(a.username)});if(req.method==='POST'){const consent=await acceptConsent(a.username,req.body||{});await appendAudit(a.username,{ts:new Date().toISOString(),type:'CONSENT_ACCEPTED',detail:`terms=${consent.termsVersion} risk=${consent.riskVersion}`});return res.status(200).json({ok:true,consent})}return res.status(405).json({error:'GET or POST only'})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
