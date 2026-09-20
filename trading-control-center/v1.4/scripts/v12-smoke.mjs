import crypto from 'node:crypto';
process.env.APP_USER='v12admin';
process.env.APP_PASSWORD_SHA256=crypto.createHash('sha256').update('AdminPassword123!').digest('hex');
process.env.SESSION_SECRET='v12-security-session-secret-123456789';
const {createAccount,getAccount}=await import('../api/_lib/accounts.js');
const {createSession,verifySession}=await import('../api/_lib/session.js');
const {csrfToken}=await import('../api/_lib/csrf.js');
const {requireAccount}=await import('../api/_lib/access.js');
const {acceptConsent,requirePaperConsent}=await import('../api/_lib/consent.js');
const {consumeUsage,getUsage}=await import('../api/_lib/usage.js');
const {setJson,getJson}=await import('../api/_lib/store.js');
const {exportUserData,deleteUserData}=await import('../api/_lib/user-data.js');
await createAccount({username:'v12-user',password:'LongPassword123!',plan:'free'});
const token=createSession('v12-user',1),session=verifySession(token),csrf=csrfToken(session);
let blocked=false;try{await requireAccount({method:'PUT',headers:{cookie:`tcc_session=${token}`}})}catch(e){blocked=e.code==='CSRF_REQUIRED'&&e.status===403}
if(!blocked)throw Error('csrf missing request was not blocked');
const a=await requireAccount({method:'PUT',headers:{cookie:`tcc_session=${token}`,'x-csrf-token':csrf}});if(a.username!=='v12-user')throw Error('csrf valid request failed');
let consentBlocked=false;try{await requirePaperConsent('v12-user')}catch(e){consentBlocked=e.code==='CONSENT_REQUIRED'}if(!consentBlocked)throw Error('paper consent gate failed');
await acceptConsent('v12-user',{acceptTerms:true,acceptRisk:true});await requirePaperConsent('v12-user');
await consumeUsage(a,'marketSymbols',100);let quota=false;try{await consumeUsage(a,'marketSymbols',1)}catch(e){quota=e.code==='USAGE_LIMIT'&&e.status===429}if(!quota)throw Error('monthly usage quota failed');
const u=await getUsage('v12-user');if(Number(u.counters.marketSymbols)!==100)throw Error('usage counter failed');
await setJson('tcc:v12-user:profile',{displayName:'Test'});const exp=await exportUserData('v12-user');if(exp.data.profile?.displayName!=='Test'||exp.data.consent?.termsVersion==null)throw Error('user export failed');
await deleteUserData('v12-user');if(await getJson('tcc:v12-user:profile'))throw Error('user data deletion failed');if(!(await getAccount('v12-user')))throw Error('data deletion should not delete account row');
const deleteHandler=(await import('../api/account/delete.js')).default;await createAccount({username:'delete-v12',password:'DeletePassword123!',plan:'free'});
const delToken=createSession('delete-v12',1),delCsrf=csrfToken(verifySession(delToken));function res(){return {code:200,body:null,headers:{},status(c){this.code=c;return this},json(v){this.body=v;return this},setHeader(k,v){this.headers[k]=v}}}
let dr=res();await deleteHandler({method:'POST',body:{password:'DeletePassword123!',confirm:'DELETE MY ACCOUNT'},headers:{cookie:`tcc_session=${encodeURIComponent(delToken)}`,'x-csrf-token':delCsrf,'x-forwarded-for':'203.0.113.55'}},dr);if(dr.code!==200||!dr.body?.deleted||await getAccount('delete-v12'))throw Error('account deletion endpoint failed');
console.log('v1.2 smoke: OK');
