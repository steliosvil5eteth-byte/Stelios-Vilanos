import {requireAdmin} from '../_lib/access.js';
import {issueResetToken} from '../_lib/password-reset.js';
import {rateLimit,applyRateLimitError} from '../_lib/rate-limit.js';
import {securityEvent} from '../_lib/security-events.js';
export default async function handler(req,res){
 if(req.method!=='POST')return res.status(405).json({error:'POST only'});
 try{const admin=await requireAdmin(req);await rateLimit(req,{label:'admin-reset',limit:30,windowMs:60*60*1000});const result=await issueResetToken(req.body?.username,admin.username);await securityEvent(req,{type:'ADMIN_RESET_ISSUED',user:String(req.body?.username||''),ok:true,detail:`issuedBy=${admin.username}`});return res.status(201).json({ok:true,...result,note:'Share this one-time token securely. It expires in 30 minutes.'})}catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}
}
