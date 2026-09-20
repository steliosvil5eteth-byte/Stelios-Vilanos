import crypto from 'node:crypto';
process.env.APP_USER='apiadmin';
process.env.APP_PASSWORD_SHA256=crypto.createHash('sha256').update('AdminPassword123!').digest('hex');
process.env.SESSION_SECRET='api-smoke-session-secret-123456789';
const {createAccount}=await import('../server/api/_lib/accounts.js');
const {createSession,verifySession}=await import('../server/api/_lib/session.js');
const {csrfToken}=await import('../server/api/_lib/csrf.js');
const stateHandler=(await import('../server/api/state.js')).default;
const strategyHandler=(await import('../server/api/strategies.js')).default;
const adminHandler=(await import('../server/api/admin/users.js')).default;
await createAccount({username:'free-api-user',password:'FreePassword123!',plan:'free'});
function req(user,method='GET',body={},query={}){const token=createSession(user),headers={cookie:`tcc_session=${encodeURIComponent(token)}`};if(!['GET','HEAD','OPTIONS'].includes(method))headers['x-csrf-token']=csrfToken(verifySession(token));return {method,body,query,headers}}
function res(){return {code:200,body:null,headers:{},status(c){this.code=c;return this},json(v){this.body=v;return this},setHeader(k,v){this.headers[k]=v}}}
let r=res();await stateHandler(req('free-api-user','PUT',{state:{settings:{minScore:68},paper:[],scanConfig:{symbols:'AAPL,MSFT,NVDA,AMZN'}}}),r);if(r.code!==200||r.body.scanConfig.symbols!=='AAPL,MSFT')throw Error('free watchlist entitlement failed');
for(let i=0;i<2;i++){r=res();await strategyHandler(req('free-api-user','POST',{name:`S${i}`,settings:{minScore:60+i}}),r);if(r.code!==200)throw Error('strategy create failed')}
r=res();await strategyHandler(req('free-api-user','POST',{name:'S3',settings:{minScore:99}}),r);if(r.code!==403||r.body.code!=='PLAN_LIMIT')throw Error('strategy plan limit failed');
r=res();await adminHandler(req('free-api-user','GET'),r);if(r.code!==403)throw Error('admin authorization failed');
r=res();await adminHandler(req('apiadmin','GET'),r);if(r.code!==200||!Array.isArray(r.body.users))throw Error('admin listing failed');
console.log('api smoke: OK');
