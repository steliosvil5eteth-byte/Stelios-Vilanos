import assert from 'node:assert/strict';
import {createAccount,updateAccount} from '../server/api/_lib/accounts.js';
import {createSession,verifySession} from '../server/api/_lib/session.js';
import {csrfToken} from '../server/api/_lib/csrf.js';
import {acceptConsent} from '../server/api/_lib/consent.js';
import {updateSafetyState} from '../server/api/_lib/safety.js';
import handler from '../api/router.js';
process.env.SESSION_SECRET='bot-test-only-session-secret-not-a-real-credential';
process.env.BOT_LOCAL_DEMO='true';
process.env.PAPER_EXECUTION_ENABLED='true';
await createAccount({username:'bot-api-test',password:'OnlyATestPassword!',email:'test@example.invalid'});
const token=createSession('bot-api-test');
function req(action,extra={}){return {method:action?'POST':'GET',query:{__route:'bot'},url:'/api/bot',headers:{cookie:`tcc_session=${encodeURIComponent(token)}`,'x-csrf-token':csrfToken(verifySession(token))},body:{action,...extra}};}
function res(){return {code:200,status(c){this.code=c;return this},setHeader(){},json(body){this.body=body;return this}};}
async function call(r){const out=res();await handler(r,out);return out;}
let out=await call({...req(),headers:{}});assert.equal(out.code,401);
out=await call({...req('create',{plan:'demo',capital:100}),headers:{cookie:`tcc_session=${encodeURIComponent(token)}`}});assert.equal(out.code,403);
out=await call(req('create',{plan:'demo',capital:100}));assert.equal(out.code,200);assert.equal(out.body.state.enabled,false);
out=await call(req('create',{plan:'demo',capital:100}));assert.equal(out.code,409);
out=await call(req('start'));assert.equal(out.code,423);
await updateAccount('bot-api-test',{emailVerifiedAt:new Date().toISOString()});
await acceptConsent('bot-api-test',{acceptTerms:true,acceptRisk:true});
await updateSafetyState('test-admin',{paperExecutionEnabled:true,emergencyStop:false});
out=await call(req('start'));assert.equal(out.code,200);assert.equal(out.body.state.enabled,true);
const now=Date.now();
const oldFetch=globalThis.fetch;
globalThis.fetch=async url=>({ok:true,json:async()=>url.includes('ticker')?{code:'0',data:[{instId:'BTC-EUR',bidPx:'106',askPx:'106.1',ts:String(now)}]}:url.includes('candles')?{code:'0',data:Array.from({length:60},(_,i)=>[String(now-(60-i)*60000),'','','',String(100+i*.1),'','','','1']).reverse()}:{articles:[]}});
try{out=await call(req('tick'));assert.equal(out.code,200);assert.ok(out.body.state.position);out=await call(req('tick'));assert.equal(out.body.state.events.filter(e=>e.type==='OPEN').length,1);}finally{globalThis.fetch=oldFetch;}
out=await call(req('pause'));assert.equal(out.body.state.enabled,false);
out=await call(req());assert.equal(out.body.liveExecution,false);assert.ok(out.body.state.position);
console.log('bot-api-smoke: PASS — router, auth, CSRF, consent, safety, create/start/tick/replay/pause/read');
