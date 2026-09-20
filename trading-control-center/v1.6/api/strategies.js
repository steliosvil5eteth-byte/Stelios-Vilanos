import {getJson,setJson,persistentStoreConfigured} from './_lib/store.js';
import {strategySnapshot} from './_lib/model.js';
import {requireAccount} from './_lib/access.js';
import {entitlements} from './_lib/plans.js';
export default async function handler(req,res){
 try{const account=await requireAccount(req);const key=`tcc:${account.username}:strategies`,e=entitlements(account.plan);
  if(req.method==='GET') return res.status(200).json({strategies:(await getJson(key))||[],persistent:persistentStoreConfigured(),limit:e.maxStrategies,plan:account.plan});
  if(req.method==='POST'){
    const snap=strategySnapshot(req.body?.settings||{},req.body?.name||'Current strategy'); const rows=(await getJson(key))||[]; const i=rows.findIndex(x=>x.id===snap.id); const now=new Date().toISOString();
    if(i<0&&rows.length>=e.maxStrategies)return res.status(403).json({error:`${e.label} plan allows up to ${e.maxStrategies} saved strategies`,code:'PLAN_LIMIT'});
    if(i>=0)rows[i]={...rows[i],...snap,lastUsedAt:now};else rows.unshift({...snap,createdAt:now,lastUsedAt:now}); await setJson(key,rows.slice(0,e.maxStrategies));
    return res.status(200).json({ok:true,strategy:snap,count:rows.length,limit:e.maxStrategies});
  }
  return res.status(405).json({error:'GET or POST only'});
 }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
