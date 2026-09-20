import {fetchMarketMany,marketDataConfig} from './_lib/market-data.js';
import {requireAccount} from './_lib/access.js';
import {entitlements} from './_lib/plans.js';
import {consumeUsage} from './_lib/usage.js';
export default async function handler(req,res){
  res.setHeader('Cache-Control','s-maxage=300, stale-while-revalidate=600');
  if(req.method!=='GET')return res.status(405).json({error:'GET only'});
  try{const account=await requireAccount(req);const e=entitlements(account.plan);const raw=String(req.query.symbols||'').toUpperCase();const symbols=[...new Set(raw.split(',').map(s=>s.trim()).filter(Boolean))].slice(0,e.maxWatchlist);
   if(!symbols.length)return res.status(400).json({error:'Provide symbols=AAPL,MSFT'});if(symbols.some(s=>!/^[A-Z0-9.\-]{1,15}$/.test(s)))return res.status(400).json({error:'Invalid symbol format'});
   await consumeUsage(account,'marketSymbols',symbols.length);const out=await fetchMarketMany(symbols);return res.status(200).json({providerConfig:marketDataConfig(),historical:true,symbols:out,plan:account.plan,limit:e.maxWatchlist})
  }catch(e){return res.status(e.status||503).json({error:String(e.message||e),code:e.code})}
}
