import {requireAccount} from './_lib/access.js';
import {getSignals,signalMetrics} from './_lib/signal-ledger.js';
export default async function handler(req,res){
  if(req.method!=='GET')return res.status(405).json({error:'GET only'});
  try{const a=await requireAccount(req);const rows=await getSignals(a.username,req.query?.limit||100);return res.status(200).json({signals:rows,metrics:signalMetrics(rows),paperOnly:true})}
  catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
