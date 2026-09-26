import {requireAccount} from '../../_lib/access.js';
import {requireFeature} from '../../_lib/plans.js';
import {appendAudit} from '../../_lib/store.js';
import {ibkrFetch,requirePaperSession,validBracket,bracketBody,marketDataPreflight,classifyOrderResponse,brokerConfig} from './_client.js';
export default async function handler(req,res){
  if(req.method!=='POST') return res.status(405).json({error:'POST only'});
  let account;try{account=await requireAccount(req);requireFeature(account,'brokerPaper')}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})} const user=account.username;
  const order=req.body||{}; if(!validBracket(order)) return res.status(400).json({error:'Invalid bracket: require conid, quantity, stop < entry < target'});
  try{
    const {account}=await requirePaperSession();
    await marketDataPreflight(order.conid);
    const body=bracketBody(order);
    const data=await ibkrFetch(`/iserver/account/${encodeURIComponent(account)}/orders/whatif`,{method:'POST',body});
    const parsed=classifyOrderResponse(data);
    await appendAudit(user,{ts:new Date().toISOString(),type:'IBKR_BRACKET_PREVIEW',detail:`conid=${order.conid} qty=${order.quantity}`});
    return res.status(200).json({ok:true,mode:'PAPER_WHATIF',accountMasked:brokerConfig().account.replace(/.(?=.{2})/g,'•'),bodySummary:{conid:Number(order.conid),quantity:Number(order.quantity),entry:Number(order.entry),stop:Number(order.stop),target:Number(order.target)},result:parsed});
  }catch(e){return res.status(e.status||502).json({error:e.message,data:e.data})}
}
