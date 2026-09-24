import {requireAccount} from './_lib/access.js';
import {entitlements} from './_lib/plans.js';
import {normalizeSymbols} from './_lib/schema.js';
import {fetchEventSignal,eventDataConfig} from './_lib/event-data.js';

export default async function handler(req,res){
  res.setHeader('Cache-Control','s-maxage=60, stale-while-revalidate=120');
  if(req.method!=='GET')return res.status(405).json({error:'GET only'});
  try{
    const account=await requireAccount(req),e=entitlements(account.plan);
    const symbols=normalizeSymbols(String(req.query?.symbols||'').split(',').filter(Boolean),e.maxWatchlist);
    if(!symbols.length)return res.status(400).json({error:'Provide symbols=AAPL,MSFT'});
    const rows=[];for(const symbol of symbols){try{rows.push(await fetchEventSignal(symbol))}catch(err){rows.push({symbol,status:'ERROR',error:String(err.message||err)})}}
    return res.status(200).json({config:eventDataConfig(),symbols:rows,plan:account.plan});
  }catch(e){return res.status(e.status||503).json({error:String(e.message||e),code:e.code})}
}
