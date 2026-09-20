import {requireAccount} from '../../_lib/access.js';
import {issueEmailVerification} from '../../_lib/email-verification.js';
import {rateLimit,applyRateLimitError} from '../../_lib/rate-limit.js';
import {securityEvent} from '../../_lib/security-events.js';
export default async function handler(req,res){if(req.method!=='POST')return res.status(405).json({error:'POST only'});try{const a=await requireAccount(req);await rateLimit(req,{label:'email-verify',limit:6,windowMs:60*60*1000});const r=await issueEmailVerification(a.username,{send:true});await securityEvent(req,{type:'EMAIL_VERIFY_REQUEST',user:a.username,ok:true,detail:`sent=${r.sent}`});return res.status(200).json({ok:true,email:r.email,alreadyVerified:Boolean(r.alreadyVerified),sent:Boolean(r.sent),provider:r.provider||'disabled',expiresAt:r.expiresAt||null,token:r.token})}catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}}
