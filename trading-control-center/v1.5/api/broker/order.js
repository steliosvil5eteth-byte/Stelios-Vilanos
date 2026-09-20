import {appendAudit} from '../_lib/store.js';
import {strategyExecutionGate} from '../_lib/portfolio.js';
import {requireAccount} from '../_lib/access.js';
import {rateLimit,applyRateLimitError} from '../_lib/rate-limit.js';
import {requirePaperConsent} from '../_lib/consent.js';
import {consumeUsage} from '../_lib/usage.js';
import {requireVerifiedEmail} from '../_lib/onboarding.js';
import {requireIdempotencyKey,runIdempotent} from '../_lib/idempotency.js';\nimport {requirePaperExecutionAllowed} from '../_lib/safety.js';\nimport {validateLongPaperOrder} from '../_lib/schema.js';\nimport {requestId} from '../_lib/request-trace.js';
function validOrder(o){return o&&/^[A-Z0-9.\-]{1,15}$/.test(String(o.symbol||''))&&Number(o.qty)>0&&Number(o.entry)>0&&Number(o.stop)>0&&Number(o.target)>0}
export default async function handler(req,res){
  if(req.method!=='POST') return res.status(405).json({error:'POST only'});
  try{await rateLimit(req,{label:'paper-order',limit:30,windowMs:10*60*1000});const account=await requireAccount(req),user=account.username,key=requireIdempotencyKey(req);
    await requirePaperConsent(user);requireVerifiedEmail(account);const order=req.body?.order;if(!validOrder(order)) return res.status(400).json({error:'Invalid order'});
    if(!(Number(order.stop)<Number(order.entry)&&Number(order.target)>Number(order.entry))) return res.status(400).json({error:'Long order requires stop < entry < target'});
    const gate=await strategyExecutionGate(user,String(order.strategyId||''));if(!gate.allowed)return res.status(409).json({error:`Strategy ${gate.lifecycle}: ${gate.reason}`,strategyGate:gate});
    const idem=await runIdempotent({user,scope:'sim-paper-order',key,input:order,work:async()=>{await consumeUsage(account,'paperOrders',1);const ticket={id:`SIM-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,broker:'SIMULATED',mode:'PAPER',status:'ACCEPTED',createdAt:new Date().toISOString(),...order};await appendAudit(user,{ts:ticket.createdAt,type:'SERVER_PAPER_ORDER',detail:`${order.symbol} qty=${order.qty} entry=${order.entry} stop=${order.stop} target=${order.target} plan=${account.plan}`});return {ok:true,ticket,strategyGate:gate,requestId:rid}}});
    return res.status(200).json({...idem.value,idempotencyReplayed:idem.replayed});
  }catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}
}
