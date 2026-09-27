import assert from 'node:assert/strict';
import {runWorker,tickWorker} from './bot-worker.mjs';
const env={BOT_BASE_URL:'https://example.invalid',CRON_SECRET:'test-secret',BOT_RUN_ONCE:'true'};
const messages=[];
const options={env,log:x=>messages.push(x),error:x=>messages.push(x)};
assert.equal(await runWorker({...options,fetchImpl:async(url,init)=>{
  assert.equal(url.href,'https://example.invalid/api/bot');
  assert.equal(init.redirect,'error');
  assert.equal(init.headers.Authorization,'Bearer test-secret');
  assert.deepEqual(JSON.parse(init.body),{action:'tick'});
  return {ok:true,json:async()=>({state:{enabled:false},metrics:{equity:100}})};
}}),0);
for(const fetchImpl of [
  async()=>({ok:false,status:403}),
  async()=>({ok:true,json:async()=>{throw Error('invalid')}}),
  async()=>({ok:true,json:async()=>({error:'test-secret'})}),
  async()=>({ok:true,json:async()=>({})}),
  async()=>{throw Error('transport test-secret')}
]) assert.equal(await runWorker({...options,fetchImpl}),1);
assert.ok(messages.every(x=>!x.includes('test-secret')));
await assert.rejects(tickWorker({base:'http://example.invalid',secret:'test',fetchImpl:()=>assert.fail('must not fetch')}));
await assert.rejects(tickWorker({base:'https://user:pass@example.invalid',secret:'test',fetchImpl:()=>assert.fail('must not fetch')}));
const controller=new AbortController();
assert.equal(await runWorker({...options,env:{...env,BOT_RUN_ONCE:'false'},signal:controller.signal,fetchImpl:async()=>{controller.abort();throw Error('aborted')}}),0);
console.log('bot-worker-smoke: PASS — failure exit codes, request policy, redaction and shutdown');
