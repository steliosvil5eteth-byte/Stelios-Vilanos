import {requireAdmin} from '../_lib/access.js';
import {allAccounts,createAccount,updateAccount} from '../_lib/accounts.js';
import {appendAudit} from '../_lib/store.js';
import {rateLimit,applyRateLimitError} from '../_lib/rate-limit.js';
export default async function handler(req,res){
 try{const admin=await requireAdmin(req);
  if(req.method==='GET')return res.status(200).json({users:await allAccounts()});
  await rateLimit(req,{label:'admin-users',limit:60,windowMs:60*60*1000});
  if(req.method==='POST'){const user=await createAccount(req.body||{});await appendAudit(admin.username,{ts:new Date().toISOString(),type:'ADMIN_CREATE_USER',detail:`user=${user.username} plan=${user.plan}`});return res.status(201).json({ok:true,user})}
  if(req.method==='PATCH'){const username=String(req.body?.username||'');const user=await updateAccount(username,req.body?.patch||{});await appendAudit(admin.username,{ts:new Date().toISOString(),type:'ADMIN_UPDATE_USER',detail:`user=${user.username} plan=${user.plan} status=${user.status}`});return res.status(200).json({ok:true,user})}
  return res.status(405).json({error:'GET, POST or PATCH only'});
 }catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}
}
