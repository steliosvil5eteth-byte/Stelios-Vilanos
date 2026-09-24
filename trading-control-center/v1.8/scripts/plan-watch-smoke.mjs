import assert from 'node:assert/strict';
process.env.CRON_SECRET='watch-smoke-secret';
process.env.SIGNAL_AUTOWATCH_ENABLED='false';
import {entitlements,requireFeature} from '../api/_lib/plans.js';
import {billingCatalog} from '../api/_lib/billing.js';
const watchHandler=(await import('../api/cron/signal-watch.js')).default;

const demo=entitlements('free'),starter=entitlements('pro'),pro=entitlements('premium');
assert.equal(demo.monthlyPriceEur,0);assert.equal(demo.autoWatch,false);assert.equal(demo.signalEmail,false);assert.equal(demo.brokerPaper,false);
assert.equal(starter.monthlyPriceEur,10.01);assert.equal(starter.autoWatchMinutes,30);assert.equal(starter.signalEmail,true);assert.equal(starter.brokerPaper,false);
assert.equal(pro.monthlyPriceEur,30);assert.equal(pro.autoWatchMinutes,5);assert.equal(pro.maxAutoWatchSymbols,5);assert.equal(pro.brokerPaper,false);
let blocked=false;try{requireFeature({plan:'premium'},'brokerPaper')}catch(e){blocked=e.code==='PLAN_LIMIT'}assert.equal(blocked,true);
const catalog=billingCatalog();assert.equal(catalog.length,3);assert.equal(catalog.find(x=>x.id==='premium').autoWatchMinutes,5);

const req={method:'GET',headers:{authorization:'Bearer watch-smoke-secret'}};
const res={code:200,body:null,status(c){this.code=c;return this},json(v){this.body=v;return this}};
await watchHandler(req,res);assert.equal(res.code,200);assert.equal(res.body.enabled,false);
console.log('plan-watch-smoke: OK');
