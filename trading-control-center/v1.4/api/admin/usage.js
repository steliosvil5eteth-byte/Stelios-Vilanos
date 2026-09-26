import {requireAdmin} from '../_lib/access.js';
import {allAccounts} from '../_lib/accounts.js';
import {getUsage,usageSummary} from '../_lib/usage.js';
export default async function handler(req,res){try{await requireAdmin(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const users=await allAccounts(),rows=[];for(const u of users)rows.push({username:u.username,plan:u.plan,status:u.status,...usageSummary(await getUsage(u.username))});return res.status(200).json({usage:rows})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
