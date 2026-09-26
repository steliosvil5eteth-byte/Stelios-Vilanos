import {runServerScan} from '../_lib/scan-runner.js';
import {allAccounts} from '../_lib/accounts.js';
import {entitlements} from '../_lib/plans.js';
import {getJson} from '../_lib/store.js';
import {runHealthMonitor} from '../_lib/monitoring.js';
export default async function handler(req,res){
  if(req.method!=='GET')return res.status(405).json({error:'GET only'});
  const secret=process.env.CRON_SECRET||'';if(!secret||req.headers.authorization!==`Bearer ${secret}`)return res.status(401).json({error:'Unauthorized'});
  try{
    const health=await runHealthMonitor();
    const users=(await allAccounts()).filter(x=>x.status==='active'&&entitlements(x.plan).scheduledScans);const results=[];
    for(const u of users.slice(0,100)){
      const state=(await getJson(`tcc:${u.username}:state`))||{};const symbols=String(state.scanConfig?.symbols||'').split(',').filter(Boolean);if(!symbols.length){results.push({user:u.username,status:'SKIP_NO_WATCHLIST'});continue}
      try{const e=entitlements(u.plan);const run=await runServerScan(u.username,{source:'cron',maxSymbols:e.maxWatchlist});results.push({user:u.username,status:'OK',id:run.id,accepted:run.accepted,rejected:run.rejected})}catch(err){results.push({user:u.username,status:'ERROR',error:String(err.message||err)})}
    }
    return res.status(200).json({ok:true,health,users:users.length,results,completedAt:new Date().toISOString()});
  }catch(e){return res.status(503).json({error:String(e.message||e)})}
}
