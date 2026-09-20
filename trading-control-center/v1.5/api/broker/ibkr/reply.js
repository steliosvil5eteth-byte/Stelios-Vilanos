import {appendAudit} from '../../_lib/store.js';
import {ibkrFetch,requirePaperSession,requirePaperExecutionEnabled,classifyOrderResponse} from './_client.js';
import {requireAccount} from '../../_lib/access.js';
import {requireFeature} from '../../_lib/plans.js';
import {rateLimit,applyRateLimitError} from '../../_lib/rate-limit.js';
import {requirePaperConsent} from '../../_lib/consent.js';
import {requireVerifiedEmail} from '../../_lib/onboarding.js';
import {requireIdempotencyKey,runIdempotent} from '../../_lib/idempotency.js';\nimport {requirePaperExecutionAllowed} from '../../_lib/safety.js';\nimport {requestId} from '../../_lib/request-trace.js';
export default async function handler(req,res){
  if(req.method!=='POST') return res.status(405).json({error:'POST only'});
  try{const rid=requestId(req,res);await rateLimit(req,{label:'ibkr-paper-reply',limit:20,windowMs:10*60*1000});const account=await requireAccount(req);requireFeature(account,'brokerPaper');const user=account.username,key=requireIdempotencyKey(req);
    await requirePaperConsent(user);requireVerifiedEmail(account);await requirePaperExecutionAllowed();const replyId=String(req.body?.replyId||'').trim(),confirmed=req.body?.confirmed===true;if(!replyId||!confirmed)return res.status(400).json({error:'replyId and explicit confirmed=true are required'});requirePaperExecutionEnabled();
    const idem=await runIdempotent({user,scope:'ibkr-paper-reply',key,input:{replyId,confirmed},work:async()=>{await requirePaperSession();const data=await ibkrFetch(`/iserver/reply/${encodeURIComponent(replyId)}`,{method:'POST',body:{confirmed:true}});const parsed=classifyOrderResponse(data);await appendAudit(user,{ts:new Date().toISOString(),type:'IBKR_PAPER_REPLY',detail:`reply=${replyId} next=${parsed.requiresConfirmation} plan=${account.plan}`});return {ok:true,mode:'IBKR_PAPER',result:parsed,requestId:rid}}});
    return res.status(200).json({...idem.value,idempotencyReplayed:idem.replayed});
  }catch(e){applyRateLimitError(res,e);return res.status(e.status||502).json({error:e.message,data:e.data,code:e.code})}
}
