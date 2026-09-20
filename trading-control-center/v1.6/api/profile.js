import {getJson,setJson,persistentStoreConfigured} from './_lib/store.js';
import {requireAccount} from './_lib/access.js';
export default async function handler(req,res){
 try{const a=await requireAccount(req),user=a.username,key=`tcc:${user}:profile`;
  if(req.method==='GET') return res.status(200).json({profile:(await getJson(key))||{user},persistent:persistentStoreConfigured()});
  if(req.method==='PUT'){const old=(await getJson(key))||{user,createdAt:new Date().toISOString()};const p=req.body?.profile||{};const safe={...old,user,displayName:String(p.displayName||old.displayName||user).slice(0,80),baseCurrency:['EUR','USD'].includes(p.baseCurrency)?p.baseCurrency:(old.baseCurrency||'EUR'),updatedAt:new Date().toISOString()};await setJson(key,safe);return res.status(200).json({ok:true,profile:safe,persistent:persistentStoreConfigured()})}
  return res.status(405).json({error:'GET or PUT only'});
 }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
