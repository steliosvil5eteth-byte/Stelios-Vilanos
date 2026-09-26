import {getScanRuns,runServerScan} from './_lib/scan-runner.js';
import {persistentStoreConfigured} from './_lib/store.js';
import {requireAccount} from './_lib/access.js';
import {entitlements} from './_lib/plans.js';
import {consumeUsage} from './_lib/usage.js';
import {normalizeSymbols} from './_lib/schema.js';
import {requestId} from './_lib/request-trace.js';
export default async function handler(req,res){
  try{
    const rid=requestId(req,res);const account=await requireAccount(req);const e=entitlements(account.plan);
    if(req.method==='GET')return res.status(200).json({runs:await getScanRuns(account.username,Math.min(Number(req.query?.limit||20),e.maxScanHistory)),persistent:persistentStoreConfigured(),plan:account.plan});
    if(req.method==='POST'){await consumeUsage(account,'manualScans',1);const symbols=normalizeSymbols(req.body?.symbols||[],e.maxWatchlist);const run=await runServerScan(account.username,{symbols,source:'manual',maxSymbols:e.maxWatchlist});return res.status(200).json({ok:true,run,plan:account.plan,requestId:rid})}
    return res.status(405).json({error:'GET or POST only'});
  }catch(e){return res.status(e.status||503).json({error:String(e.message||e),code:e.code})}
}
