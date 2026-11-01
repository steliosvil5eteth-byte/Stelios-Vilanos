import {getJson,persistentStoreConfigured} from './_lib/store.js';
import {portfolioMetrics,benchmarkComparison} from './_lib/portfolio.js';
import {requireAccount} from './_lib/access.js';
export default async function handler(req,res){
 try{const a=await requireAccount(req),user=a.username;if(req.method!=='GET')return res.status(405).json({error:'GET only'});const state=(await getJson(`tcc:${user}:state`))||{};const trades=(await getJson(`tcc:${user}:trades`))||[];const portfolio=portfolioMetrics({settings:state.settings||{},trades});let benchmark=null;if(String(req.query?.benchmark||'').toUpperCase())benchmark=await benchmarkComparison(user,trades,String(req.query.benchmark).toUpperCase().slice(0,15));return res.status(200).json({portfolio,benchmark,persistent:persistentStoreConfigured()})
 }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
