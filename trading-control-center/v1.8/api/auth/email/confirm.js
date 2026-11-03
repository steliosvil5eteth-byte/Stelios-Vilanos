import {confirmEmailVerification} from '../../_lib/email-verification.js';
import {rateLimit,applyRateLimitError} from '../../_lib/rate-limit.js';
import {securityEvent} from '../../_lib/security-events.js';
export default async function handler(req,res){if(req.method!=='POST')return res.status(405).json({error:'POST only'});try{await rateLimit(req,{label:'email-confirm',limit:15,windowMs:60*60*1000});const a=await confirmEmailVerification(req.body?.token);await securityEvent(req,{type:'EMAIL_VERIFY_CONFIRM',user:a.username,ok:true,detail:'verified'});return res.status(200).json({ok:true,verified:true,email:a.email})}catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}}
