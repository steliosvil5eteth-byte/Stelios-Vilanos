import {consumeResetToken} from '../../_lib/password-reset.js';
import {clearSessionCookie} from '../../_lib/session.js';
import {rateLimit,applyRateLimitError} from '../../_lib/rate-limit.js';
import {securityEvent} from '../../_lib/security-events.js';
export default async function handler(req,res){
 if(req.method!=='POST')return res.status(405).json({error:'POST only'});
 try{await rateLimit(req,{label:'password-reset-complete',limit:8,windowMs:60*60*1000});const {token='',newPassword=''}=req.body||{};const account=await consumeResetToken(token,newPassword);await securityEvent(req,{type:'PASSWORD_RESET',user:account.username,ok:true,detail:'completed'});clearSessionCookie(res);return res.status(200).json({ok:true,message:'Password updated. Sign in again.'})}catch(e){await securityEvent(req,{type:'PASSWORD_RESET',user:'',ok:false,detail:e.code||e.message});applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}
}
