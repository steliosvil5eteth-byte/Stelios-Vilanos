import {getJson,setJson,appendAudit,persistentStoreConfigured} from './_lib/store.js';
import {syncUserModel,evaluateAlerts,strategySnapshot} from './_lib/model.js';
import {requireAccount} from './_lib/access.js';
import {entitlements} from './_lib/plans.js';
export default async function handler(req,res){
  try{
    const account=await requireAccount(req);const user=account.username,e=entitlements(account.plan),key=`tcc:${user}:state`;
    if(req.method==='GET') return res.status(200).json({state:(await getJson(key))||null,persistent:persistentStoreConfigured(),plan:account.plan,entitlements:e});
    if(req.method==='PUT'){
      const state=req.body?.state; if(!state||typeof state!=='object') return res.status(400).json({error:'state object required'});
      const settings=state.settings||{},paper=Array.isArray(state.paper)?state.paper.slice(0,1000):[]; const currentStrategy=strategySnapshot(settings,state.strategy?.name||'Current strategy');
      const symbols=[...new Set(String(state.scanConfig?.symbols||'').toUpperCase().split(',').map(x=>x.trim()).filter(x=>/^[A-Z0-9.\-]{1,15}$/.test(x)))].slice(0,e.maxWatchlist);
      const scanConfig={symbols:symbols.join(',')};
      const safe={version:'signal-first-1',settings,paper,currentStrategy,scanConfig,plan:account.plan,updatedAt:new Date().toISOString()};
      await setJson(key,safe); const model=await syncUserModel(user,{settings,paper}); const alerts=await evaluateAlerts(user,safe);
      await appendAudit(user,{ts:new Date().toISOString(),type:'STATE_SYNC',detail:`paper=${safe.paper.length} strategy=${currentStrategy.id} alerts=${alerts.events.length} plan=${account.plan}`});
      return res.status(200).json({ok:true,persistent:persistentStoreConfigured(),updatedAt:safe.updatedAt,currentStrategy:model.currentStrategy,strategyCount:model.strategyCount,tradeCount:model.tradeCount,alertCount:alerts.events.filter(x=>!x.acknowledged).length,scanConfig,entitlements:e});
    }
    return res.status(405).json({error:'GET or PUT only'});
  }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
