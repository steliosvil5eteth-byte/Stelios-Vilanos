import {getJson,persistentStoreConfigured} from './_lib/store.js';
import {requireAccount} from './_lib/access.js';
export default async function handler(req,res){
 try{const a=await requireAccount(req),user=a.username;if(req.method!=='GET')return res.status(405).json({error:'GET only'});const rows=(await getJson(`tcc:${user}:trades`))||[];const status=String(req.query?.status||'').toUpperCase();const strategyId=String(req.query?.strategyId||'');const out=rows.filter(t=>(!status||String(t.status).toUpperCase()===status)&&(!strategyId||t.strategyId===strategyId)).slice(0,1000);return res.status(200).json({trades:out,total:rows.length,persistent:persistentStoreConfigured()})
 }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
