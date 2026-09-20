import {requireAccount} from './_lib/access.js';
import {getUsage,usageSummary} from './_lib/usage.js';
export default async function handler(req,res){try{const a=await requireAccount(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});return res.status(200).json({usage:usageSummary(await getUsage(a.username),a.plan),plan:a.plan})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
