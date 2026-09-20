import {appendAudit} from '../../_lib/store.js';
import {ibkrFetch,requirePaperSession,requirePaperExecutionEnabled,validBracket,bracketBody,marketDataPreflight,classifyOrderResponse} from './_client.js';
import {strategyExecutionGate} from '../../_lib/portfolio.js';
import {requireAccount} from '../../_lib/access.js';
import {requireFeature} from '../../_lib/plans.js';
import {rateLimit,applyRateLimitError} from '../../_lib/rate-limit.js';
import {requirePaperConsent} from '../../_lib/consent.js';
import {consumeUsage} from '../../_lib/usage.js';
import {requireVerifiedEmail} from '../../_lib/onboarding.js';
import {requireIdempotencyKey,runIdempotent} from '../../_lib/idempotency.js';\nimport {requirePaperExecutionAllowed} from '../../_lib/safety.js';\nimport {validateBracketOrder} from '../../_lib/schema.js';\nimport {requestId} from '../../_lib/request-trace.js';
export default async function handler(req,res){
  if(req.method!=='POST') return res.status(405).json({error:'POST only'});
  try{
    await rateLimit(req,{label:'ibkr-paper-order',limit:20,windowMs:10*60*1000});
    const account=await requireAccount(req);requireFeature(account,'brokerPaper');const user=account.username,key=requireIdempotencyKey(req);
    await requirePaperConsent(user);requireVerifiedEmail(account);const order=req.body||{};if(!validBracket(order)) return res.status(400).json({error:'Invalid bracket: require conid, quantity, stop < entry < target'});
    requirePaperExecutionEnabled();const gate=await strategyExecutionGate(user,String(order.strategyId||''));if(!gate.allowed)return res.status(409).json({error:`Strategy ${gate.lifecycle}: ${gate.reason}`,strategyGate:gate});
    const idem=await runIdempotent({user,scope:'ibkr-paper-bracket',key,input:order,work:async()=>{await consumeUsage(account,'paperOrders',1);const {account:brokerAccount}=await requirePaperSession();await marketDataPreflight(order.conid);const body=bracketBody(order);const data=await ibkrFetch(`/iserver/account/${encodeURIComponent(brokerAccount)}/orders`,{method:'POST',body});const parsed=classifyOrderResponse(data);await appendAudit(user,{ts:new Date().toISOString(),type:'IBKR_PAPER_BRACKET',detail:`conid=${order.conid} qty=${order.quantity} reply=${parsed.requiresConfirmation} plan=${account.plan}`});return {ok:true,mode:'IBKR_PAPER',strategyGate:gate,submitted:!parsed.requiresConfirmation&&parsed.errors.length===0,result:parsed,requestId:rid}}});
    return res.status(200).json({...idem.value,idempotencyReplayed:idem.replayed});
  }catch(e){applyRateLimitError(res,e);return res.status(e.status||502).json({error:e.message,data:e.data,code:e.code})}
}
