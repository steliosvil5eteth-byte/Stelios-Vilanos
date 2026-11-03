import crypto from 'crypto';
import {getJson,setJson,deleteJson,appendAudit} from './store.js';
import {getAccount,updateAccount} from './accounts.js';
import {sendEmail,emailConfig} from './email.js';
const TTL=24*60*60*1000;
function digest(v){return crypto.createHash('sha256').update(String(v)).digest('hex')}
export async function issueEmailVerification(username,{send=true}={}){
  const account=await getAccount(username);if(!account){const e=new Error('User not found');e.status=404;throw e}if(!account.email){const e=new Error('Add a valid email address first');e.status=400;throw e}
  if(account.emailVerifiedAt)return {alreadyVerified:true,email:account.email,expiresAt:null,sent:false};
  const token=crypto.randomBytes(32).toString('base64url'),hash=digest(token),createdAt=new Date().toISOString(),expiresAt=new Date(Date.now()+TTL).toISOString();
  await setJson(`tcc:email-verify:${hash}`,{username:account.username,email:account.email,createdAt,expiresAt});
  let delivery={sent:false,provider:'disabled'};
  if(send){const c=emailConfig();const link=c.appBaseUrl?`${c.appBaseUrl}/?verify_email=${encodeURIComponent(token)}`:'';delivery=await sendEmail({to:account.email,subject:'Verify your Trading Control Center email',text:link?`Verify your email: ${link}`:`Email verification token: ${token}`,html:link?`<p>Verify your email for Trading Control Center:</p><p><a href="${link}">Verify email</a></p><p>This link expires in 24 hours.</p>`:`<p>Email verification token: <code>${token}</code></p>`,idempotencyKey:`verify-${account.username}-${hash.slice(0,16)}`})}
  await appendAudit(account.username,{ts:createdAt,type:'EMAIL_VERIFICATION_ISSUED',detail:`email=${account.email} sent=${delivery.sent}`});
  return {alreadyVerified:false,email:account.email,expiresAt,sent:delivery.sent,provider:delivery.provider,token:process.env.EXPOSE_DEV_TOKENS==='true'?token:undefined};
}
export async function confirmEmailVerification(token){
  const hash=digest(token),key=`tcc:email-verify:${hash}`,row=await getJson(key);if(!row||Date.now()>Date.parse(row.expiresAt||0)){const e=new Error('Verification token invalid or expired');e.status=400;throw e}
  const account=await getAccount(row.username);if(!account||account.status!=='active'||account.email!==row.email){await deleteJson(key);const e=new Error('Verification token no longer matches this account');e.status=400;throw e}
  const now=new Date().toISOString();const updated=await updateAccount(account.username,{emailVerifiedAt:now});await deleteJson(key);await appendAudit(account.username,{ts:now,type:'EMAIL_VERIFIED',detail:`email=${account.email}`});return updated;
}
