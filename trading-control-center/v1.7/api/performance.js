import {performanceForUser} from './_lib/model.js';
import {requireAccount} from './_lib/access.js';
export default async function handler(req,res){try{const a=await requireAccount(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});return res.status(200).json(await performanceForUser(a.username))}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
