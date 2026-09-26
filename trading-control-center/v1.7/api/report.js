import {requireAccount} from './_lib/access.js';
import {getJson,persistentStoreConfigured} from './_lib/store.js';
import {performanceReport} from './_lib/report.js';
export default async function handler(req,res){try{const a=await requireAccount(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const state=(await getJson(`tcc:${a.username}:state`))||{};const trades=(await getJson(`tcc:${a.username}:trades`))||[];return res.status(200).json({report:performanceReport({settings:state.settings||{},trades}),persistent:persistentStoreConfigured(),account:{plan:a.plan}})}catch(e){return res.status(e.status||500).json({error:e.message})}}
