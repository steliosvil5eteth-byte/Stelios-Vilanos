import {authConfigured,createSession,setSessionCookie} from '../_lib/session.js';
import {getAccount,verifyPassword} from '../_lib/accounts.js';
import {rateLimit,applyRateLimitError} from '../_lib/rate-limit.js';
import {securityEvent} from '../_lib/security-events.js';
export default async function handler(req,res){
  if(req.method!=='POST') return res.status(405).json({error:'POST only'});
  try{
    await rateLimit(req,{label:'login',limit:10,windowMs:15*60*1000});
    if(!authConfigured()) return res.status(503).json({error:'Server login is not configured'});
    const {username='',password=''}=req.body||{}; const account=await getAccount(username);
    if(!account||account.status!=='active'||!verifyPassword(password,account.auth)){await securityEvent(req,{type:'LOGIN',user:String(username||'').toLowerCase(),ok:false,detail:'invalid credentials'});return res.status(401).json({error:'Invalid credentials'})}
    setSessionCookie(res,createSession(account.username,account.sessionVersion));
    await securityEvent(req,{type:'LOGIN',user:account.username,ok:true,detail:`plan=${account.plan}`});
    return res.status(200).json({ok:true,user:account.username,role:account.role,plan:account.plan});
  }catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}
}
