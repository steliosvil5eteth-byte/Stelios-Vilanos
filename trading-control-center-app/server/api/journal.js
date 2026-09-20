import {getJson,setJson,appendAudit,persistentStoreConfigured} from './_lib/store.js';
import {requireAccount} from './_lib/access.js';
import {entitlements} from './_lib/plans.js';
export default async function handler(req,res){
 try{const account=await requireAccount(req),user=account.username,e=entitlements(account.plan),key=`tcc:${user}:journal`;
  if(req.method==='GET') return res.status(200).json({trades:(await getJson(key))||[],persistent:persistentStoreConfigured(),limit:e.maxJournalTrades});
  if(req.method==='PUT'){
   const trades=Array.isArray(req.body?.trades)?req.body.trades:[];
   const safe=trades.filter(t=>t&&t.status&&t.status!=='OPEN'&&t.closedAt).slice(0,e.maxJournalTrades).map(t=>({id:String(t.id||''),ticker:String(t.ticker||'').slice(0,20),entry:Number(t.entry||0),stop:Number(t.stop||0),target:Number(t.target||0),current:Number(t.current||0),qty:Number(t.qty||0),status:String(t.status||''),opened:t.opened||null,closedAt:t.closedAt||null,source:String(t.source||''),strategy:String(t.strategy||t.source||''),strategyId:String(t.strategyId||''),strategyName:String(t.strategyName||''),broker:String(t.broker||''),exitCommission:Number(t.exitCommission||0),netPnl:Number.isFinite(Number(t.netPnl))?Number(t.netPnl):undefined}));
   await setJson(key,safe); await appendAudit(user,{ts:new Date().toISOString(),type:'JOURNAL_SYNC',detail:`closed=${safe.length} plan=${account.plan}`});
   return res.status(200).json({ok:true,count:safe.length,limit:e.maxJournalTrades,persistent:persistentStoreConfigured()});
  }
  return res.status(405).json({error:'GET or PUT only'});
 }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
