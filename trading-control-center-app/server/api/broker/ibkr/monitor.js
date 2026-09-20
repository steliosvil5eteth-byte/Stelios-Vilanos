import {requireAccount} from '../../_lib/access.js';
import {requireFeature} from '../../_lib/plans.js';
import {appendAudit} from '../../_lib/store.js';
import {ibkrFetch,requirePaperSession} from './_client.js';

function asArray(v){return Array.isArray(v)?v:[]}

export default async function handler(req,res){
  if(req.method!=='GET') return res.status(405).json({error:'GET only'});
  let account;try{account=await requireAccount(req);requireFeature(account,'brokerPaper')}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})} const user=account.username;
  try{
    const {account}=await requirePaperSession();
    // IBKR requires /portfolio/accounts to prime portfolio endpoints.
    await ibkrFetch('/portfolio/accounts');
    const [positionsRaw,ordersRaw,tradesRaw]=await Promise.all([
      ibkrFetch(`/portfolio2/${encodeURIComponent(account)}/positions`),
      ibkrFetch('/iserver/account/orders'),
      ibkrFetch('/iserver/account/trades?days=7')
    ]);
    const positions=asArray(positionsRaw).map(p=>({
      conid:Number(p.conid),symbol:p.description||p.contractDesc||'',position:Number(p.position||0),
      marketPrice:Number(p.marketPrice??p.mktPrice??0),marketValue:Number(p.marketValue??p.mktValue??0),
      avgPrice:Number(p.avgPrice??p.avgCost??0),unrealizedPnl:Number(p.unrealizedPnl||0),realizedPnl:Number(p.realizedPnl||0),currency:p.currency||''
    }));
    const orderList=asArray(ordersRaw?.orders??ordersRaw).map(o=>({
      orderId:String(o.orderId??o.order_id??''),conid:Number(o.conid||0),symbol:o.ticker||o.symbol||o.description1||'',
      side:o.side||'',status:o.status||o.order_status||'',filledQuantity:Number(o.filledQuantity||0),
      remainingQuantity:Number(o.remainingQuantity??o.remaining_quantity??0),price:Number(o.price??o.orderPrice??0),
      avgPrice:Number(o.avgPrice||0),orderRef:o.order_ref||o.orderRef||''
    }));
    const trades=asArray(tradesRaw).map(t=>({
      executionId:String(t.execution_id||''),orderId:String(t.order_id??''),conid:Number(t.conid||0),symbol:t.symbol||t.contract_description_1||'',
      side:String(t.side||'').toUpperCase(),size:Number(t.size||0),price:Number(t.price||0),tradeTime:t.trade_time||'',
      tradeTimeMs:Number(t.trade_time_r||0),commission:Number(t.commission||0),orderRef:t.order_ref||''
    }));
    const ts=new Date().toISOString();
    await appendAudit(user,{ts,type:'IBKR_PAPER_MONITOR',detail:`positions=${positions.length} openOrders=${orderList.length} trades=${trades.length}`});
    return res.status(200).json({ok:true,mode:'IBKR_PAPER',accountMasked:account.length>4?`••••${account.slice(-4)}`:account,asOf:ts,positions,openOrders:orderList,trades});
  }catch(e){return res.status(e.status||502).json({error:e.message,data:e.data})}
}
