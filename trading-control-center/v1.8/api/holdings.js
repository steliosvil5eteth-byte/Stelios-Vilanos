import {getJson,setJson,persistentStoreConfigured,appendAudit} from './_lib/store.js';
import {requireAccount} from './_lib/access.js';
import {entitlements} from './_lib/plans.js';
import {normalizeHoldings,holdingsSummary} from './_lib/holdings.js';
export default async function handler(req,res){
  try{
    const a=await requireAccount(req),key=`tcc:${a.username}:holdings`,e=entitlements(a.plan);
    if(req.method==='GET'){const rows=(await getJson(key))||[];return res.status(200).json({holdings:rows,summary:holdingsSummary(rows),maxHoldings:e.maxHoldings,persistent:persistentStoreConfigured(),readOnly:true})}
    if(req.method==='PUT'){
      const rows=normalizeHoldings(req.body?.holdings,e.maxHoldings);await setJson(key,rows);
      await appendAudit(a.username,{ts:new Date().toISOString(),type:'HOLDINGS_IMPORT',detail:`positions=${rows.length} readOnly=true`});
      return res.status(200).json({ok:true,holdings:rows,summary:holdingsSummary(rows),maxHoldings:e.maxHoldings,readOnly:true});
    }
    return res.status(405).json({error:'GET or PUT only'});
  }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
