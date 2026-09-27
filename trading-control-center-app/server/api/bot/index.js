import crypto from 'node:crypto';
import {requireAccount} from '../_lib/access.js';
import {getAccount} from '../_lib/accounts.js';
import {getSafetyState} from '../_lib/safety.js';
import {getConsent} from '../_lib/consent.js';
import {requireVerifiedEmail} from '../_lib/onboarding.js';
import {requireMaintenanceWriteAllowed} from '../_lib/maintenance.js';
import {rateLimit,applyRateLimitError} from '../_lib/rate-limit.js';
import {createBot,tickBot,botMetrics,BOT_PLANS,POLICY} from '../_lib/paper-bot.js';
import {readBot,mutateBot} from '../_lib/bot-store.js';
import {fetchBotSnapshot} from '../_lib/bot-feed.js';
function cronAuth(req){const secret=process.env.CRON_SECRET;if(!secret)return false;const a=Buffer.from(String(req.headers?.authorization||'')),b=Buffer.from(`Bearer ${secret}`);return a.length===b.length&&crypto.timingSafeEqual(a,b);}
export default async function handler(req,res){
  res.setHeader('Cache-Control','no-store');
  if(!['GET','POST'].includes(req.method))return res.status(405).json({error:'GET or POST only'});
  try{
    const isCron=req.method==='POST'&&req.body?.action==='tick'&&cronAuth(req);
    let account;
    if(isCron){account=await getAccount(process.env.BOT_USERNAME||'');if(!account||account.status!=='active')throw Object.assign(new Error('BOT_ACCOUNT_UNAVAILABLE'),{status:403});await requireMaintenanceWriteAllowed(req,account);}
    else {account=await requireAccount(req);await rateLimit(req,{label:`bot-${account.username}`,limit:20,windowMs:60000});}
    const user=account.username;
    if(req.method==='GET'){const state=await readBot(user);return res.json({state,metrics:state?botMetrics(state):null,plans:BOT_PLANS,policy:POLICY,liveExecution:false});}
    const action=req.body?.action;
    if(action==='create'){
      const state=await mutateBot(user,old=>{if(old)throw Object.assign(new Error('BOT_ALREADY_EXISTS: capital/plan cannot reset loss limits'),{status:409});return createBot({plan:req.body.plan,capital:req.body.capital});});
      return res.json({state,metrics:botMetrics(state)});
    }
    if(!['start','pause','tick'].includes(action))throw Object.assign(new Error('INVALID_ACTION'),{status:400});
    const safety=await getSafetyState(),consent=await getConsent(user);
    let verified=true;try{requireVerifiedEmail(account);}catch{verified=false;}
    const allowEntry=safety.paperExecutionAllowed&&consent.current&&verified;
    if(action==='start'&&!allowEntry)throw Object.assign(new Error(`START_BLOCKED: ${!verified?'EMAIL_VERIFICATION_REQUIRED':!consent.current?'CONSENT_REQUIRED':safety.reason}`),{status:423});
    // Fetch quotes even when entry gates are off: existing simulated stops still work.
    const snapshot=action==='tick'?await fetchBotSnapshot():null;
    const state=await mutateBot(user,old=>{
      if(!old)throw Object.assign(new Error('CREATE_BOT_FIRST'),{status:409});
      if(action==='start'||action==='pause')return {...old,enabled:action==='start'};
      return tickBot(old,snapshot,Date.now(),{allowEntry});
    });
    return res.json({state,metrics:botMetrics(state),entryAllowed:allowEntry,safetyReason:safety.reason,news:snapshot?.news||null});
  }catch(e){applyRateLimitError(res,e);return res.status(e.status||502).json({error:e.message,liveExecution:false});}
}
