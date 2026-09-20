import {requireAccount} from '../_lib/access.js';
import {exportUserData} from '../_lib/user-data.js';
import {appendAudit} from '../_lib/store.js';
export default async function handler(req,res){try{const a=await requireAccount(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const data=await exportUserData(a.username);await appendAudit(a.username,{ts:new Date().toISOString(),type:'ACCOUNT_DATA_EXPORT',detail:'self-service export'});res.setHeader('Cache-Control','no-store');return res.status(200).json({account:{username:a.username,displayName:a.displayName,email:a.email,role:a.role,plan:a.plan,createdAt:a.createdAt},...data})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
