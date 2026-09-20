import {requireAccount} from '../../_lib/access.js';
import {requireFeature} from '../../_lib/plans.js';
import {getJson,appendAudit} from '../../_lib/store.js';
import {ibkrFetch,requirePaperSession} from './_client.js';
import {reconcilePaperState} from '../../_lib/reconciliation.js';
import {requestId} from '../../_lib/request-trace.js';
function arr(v){return Array.isArray(v)?v:[]}
export default async function handler(req,res){
  if(req.method!=='GET')return res.status(405).json({error:'GET only'});
  try{const rid=requestId(req,res);const a=await requireAccount(req);requireFeature(a,'brokerPaper');const {account}=await requirePaperSession();await ibkrFetch('/portfolio/accounts');const [positionsRaw,ordersRaw,tradesRaw,localTrades]=await Promise.all([ibkrFetch(`/portfolio2/${encodeURIComponent(account)}/positions`),ibkrFetch('/iserver/account/orders'),ibkrFetch('/iserver/account/trades?days=7'),getJson(`tcc:${a.username}:trades`)]);const positions=arr(positionsRaw).map(p=>({conid:Number(p.conid),symbol:p.description||p.contractDesc||'',position:Number(p.position||0)}));const openOrders=arr(ordersRaw?.orders??ordersRaw).map(o=>({orderId:String(o.orderId??o.order_id??''),conid:Number(o.conid||0),symbol:o.ticker||o.symbol||o.description1||'',status:o.status||o.order_status||''}));const brokerTrades=arr(tradesRaw).map(t=>({executionId:String(t.execution_id||''),conid:Number(t.conid||0),symbol:t.symbol||t.contract_description_1||''}));const report=reconcilePaperState({localTrades:arr(localTrades),positions,openOrders,brokerTrades});await appendAudit(a.username,{ts:new Date().toISOString(),type:'IBKR_RECONCILIATION',detail:`ok=${report.ok} critical=${report.critical} warnings=${report.warnings} request=${rid}`});return res.status(report.ok?200:409).json({requestId:rid,mode:'IBKR_PAPER',report})}catch(e){return res.status(e.status||502).json({error:e.message,code:e.code,data:e.data})}
}
