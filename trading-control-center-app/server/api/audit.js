import {appendAudit,getJson,persistentStoreConfigured} from './_lib/store.js';
import {requireAccount} from './_lib/access.js';
export default async function handler(req,res){
 try{const account=await requireAccount(req),user=account.username,key=`tcc:${user}:audit`;
  if(req.method==='GET') return res.status(200).json({audit:(await getJson(key))||[],persistent:persistentStoreConfigured()});
  if(req.method==='POST'){const type=String(req.body?.type||'CLIENT_EVENT').slice(0,40),detail=String(req.body?.detail||'').slice(0,500);await appendAudit(user,{ts:new Date().toISOString(),type,detail});return res.status(200).json({ok:true})}
  return res.status(405).json({error:'GET or POST only'});
 }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
