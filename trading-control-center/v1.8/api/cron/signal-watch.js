import {runServerScan,getScanRuns} from '../_lib/scan-runner.js';
import {allAccounts} from '../_lib/accounts.js';
import {entitlements} from '../_lib/plans.js';
import {getJson} from '../_lib/store.js';

function due(last,minutes){
  if(!last?.completedAt)return true;
  const ts=Date.parse(last.completedAt);if(!Number.isFinite(ts))return true;
  return Date.now()-ts>=Math.max(1,Number(minutes)||1)*60000;
}
export default async function handler(req,res){
  if(req.method!=='GET')return res.status(405).json({error:'GET only'});
  const secret=String(process.env.CRON_SECRET||'');if(!secret||String(req.headers.authorization||'')!=='Bearer '+secret)return res.status(401).json({error:'Unauthorized'});
  const enabled=String(process.env.SIGNAL_AUTOWATCH_ENABLED||'false').toLowerCase()==='true';
  if(!enabled)return res.status(200).json({ok:true,enabled:false,note:'Auto-watch is disabled by default. Manual scans remain available.'});
  try{
    const maxUsers=Math.max(1,Math.min(100,Number(process.env.SIGNAL_AUTOWATCH_MAX_USERS)||20));
    const users=(await allAccounts()).filter(x=>x.status==='active'&&entitlements(x.plan).autoWatch).slice(0,maxUsers),results=[];
    for(const u of users){
      const e=entitlements(u.plan),state=(await getJson('tcc:'+u.username+':state'))||{},symbols=String(state.scanConfig?.symbols||'').split(',').map(x=>x.trim()).filter(Boolean).slice(0,e.maxAutoWatchSymbols);
      if(!symbols.length){results.push({user:u.username,status:'SKIP_NO_WATCHLIST'});continue}
      const last=(await getScanRuns(u.username,20)).find(x=>x.source==='auto-watch');
      if(!due(last,e.autoWatchMinutes)){results.push({user:u.username,status:'SKIP_NOT_DUE',minutes:e.autoWatchMinutes});continue}
      try{const run=await runServerScan(u.username,{symbols,source:'auto-watch',maxSymbols:e.maxAutoWatchSymbols});results.push({user:u.username,status:'OK',id:run.id,accepted:run.accepted,rejected:run.rejected,alerts:run.alerts})}
      catch(err){results.push({user:u.username,status:'ERROR',error:String(err.message||err)})}
    }
    return res.status(200).json({ok:true,enabled:true,users:users.length,results,completedAt:new Date().toISOString()});
  }catch(e){return res.status(503).json({error:String(e.message||e)})}
}
