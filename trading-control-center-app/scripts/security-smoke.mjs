import crypto from 'node:crypto';
process.env.APP_USER='securityadmin';
process.env.APP_PASSWORD_SHA256=crypto.createHash('sha256').update('AdminPassword123!').digest('hex');
process.env.SESSION_SECRET='security-smoke-secret-123456789012345';
const {createAccount,getAccount,verifyPassword}=await import('../server/api/_lib/accounts.js');
const {createSession}=await import('../server/api/_lib/session.js');
const {requireAccount}=await import('../server/api/_lib/access.js');
const {issueResetToken,consumeResetToken}=await import('../server/api/_lib/password-reset.js');
const {rateLimit}=await import('../server/api/_lib/rate-limit.js');
await createAccount({username:'reset-user',password:'OldPassword123!',plan:'free'});
const before=await getAccount('reset-user');
const oldSession=createSession(before.username,before.sessionVersion);
const issued=await issueResetToken('reset-user','securityadmin');
await consumeResetToken(issued.token,'NewPassword123!');
const after=await getAccount('reset-user');
if(verifyPassword('OldPassword123!',after.auth)||!verifyPassword('NewPassword123!',after.auth))throw Error('password reset failed');
if(after.sessionVersion<=before.sessionVersion)throw Error('session version not incremented');
let revoked=false;try{await requireAccount({headers:{cookie:`tcc_session=${oldSession}`}})}catch(e){revoked=e.code==='SESSION_REVOKED'||e.status===401}
if(!revoked)throw Error('old session not revoked');
const req={headers:{'x-forwarded-for':'203.0.113.10'}};
await rateLimit(req,{label:'smoke',limit:2,windowMs:60000});
await rateLimit(req,{label:'smoke',limit:2,windowMs:60000});
let limited=false;try{await rateLimit(req,{label:'smoke',limit:2,windowMs:60000})}catch(e){limited=e.status===429}
if(!limited)throw Error('rate limit failed');
console.log('security smoke: OK');
