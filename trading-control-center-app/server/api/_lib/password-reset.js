import crypto from 'crypto';
import {getJson,setJson,deleteJson,appendAudit} from './store.js';
import {getAccount,updateAccount} from './accounts.js';
const TTL=30*60*1000;
function digest(token){return crypto.createHash('sha256').update(String(token)).digest('hex')}
export async function issueResetToken(username,issuedBy='admin'){
  const account=await getAccount(username);if(!account){const e=new Error('User not found');e.status=404;throw e}
  const token=crypto.randomBytes(32).toString('base64url'),hash=digest(token),expiresAt=new Date(Date.now()+TTL).toISOString();
  await setJson(`tcc:reset:${hash}`,{username:account.username,issuedBy,createdAt:new Date().toISOString(),expiresAt,used:false});
  await appendAudit(account.username,{ts:new Date().toISOString(),type:'PASSWORD_RESET_ISSUED',detail:`issuedBy=${issuedBy}`});
  return {token,expiresAt};
}
export async function consumeResetToken(token,newPassword){
  if(String(newPassword||'').length<10){const e=new Error('Password must be at least 10 characters');e.status=400;throw e}
  const hash=digest(token),key=`tcc:reset:${hash}`,row=await getJson(key);
  if(!row||row.used||!row.expiresAt||Date.now()>Date.parse(row.expiresAt)){const e=new Error('Reset token invalid or expired');e.status=400;throw e}
  const account=await updateAccount(row.username,{password:newPassword});await deleteJson(key);
  await appendAudit(row.username,{ts:new Date().toISOString(),type:'PASSWORD_RESET_COMPLETED',detail:'password changed; existing sessions revoked'});
  return account;
}
