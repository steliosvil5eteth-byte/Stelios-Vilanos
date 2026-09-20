import {consumeResetToken} from '../../_lib/password-reset.js';
import {rateLimit,applyRateLimitError} from '../../_lib/rate-limit.js';
import {securityEvent} from '../../_lib/security-events.js';
export default async function handler(req,res){if(req.method!=='POST')return res.status(405).json({error:'POST only'});try{await rateLimit(req,{label:'password-reset-public',limit:12,windowMs:60*60*1000});const a=await consumeResetToken(req.body?.token,req.body?.newPassword);await securityEvent(req,{type:'PASSWORD_RESET_EMAIL_COMPLETED',user:a.username,ok:true,detail:'sessions revoked'});return res.status(200).json({ok:true,message:'Password changed. Sign in again.'})}catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}}
