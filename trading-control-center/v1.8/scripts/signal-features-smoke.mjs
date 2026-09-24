import assert from 'node:assert/strict';
process.env.EMAIL_MODE='memory';process.env.EMAIL_FROM='signals@example.test';
import {normalizeHoldings,holdingsSummary,signalPortfolioContext} from '../api/_lib/holdings.js';
import {dataQuality} from '../api/_lib/scanner.js';
import {signalMetrics} from '../api/_lib/signal-ledger.js';
import {createAccount,updateAccount} from '../api/_lib/accounts.js';
import {setJson} from '../api/_lib/store.js';
import {publishSignalAlerts} from '../api/_lib/signal-alerts.js';
import {emailOutbox} from '../api/_lib/email.js';

const holdings=normalizeHoldings([{symbol:'AAPL',quantity:2,avgCost:180,assetType:'stock'},{symbol:'BTC/USD',quantity:.01,avgCost:60000,assetType:'crypto'}],5);
assert.equal(holdings.length,2);const hs=holdingsSummary(holdings);assert.ok(hs.totalReferenceValue>0);
const ctx=signalPortfolioContext({ticker:'AAPL'},holdings);assert.equal(ctx.hasExistingPosition,true);assert.ok(ctx.existingWeightPct>0);

const good=Array.from({length:60},(_,i)=>({date:`2026-09-25T${String(10+Math.floor(i/12)).padStart(2,'0')}:${String((i%12)*5).padStart(2,'0')}:00Z`,open:100+i*.01,high:101+i*.01,low:99+i*.01,close:100.5+i*.01,volume:10000}));
const q=dataQuality(good);assert.equal(q.valid,true);assert.equal(q.score,100);const bad=good.map(x=>({...x}));bad[10].high=1;assert.equal(dataQuality(bad).valid,false);

const rows=[
 {status:'CLOSED',signalScore:95.5,rMultiple:1,reason:'TARGET'},
 {status:'CLOSED',signalScore:97.5,rMultiple:-1,reason:'STOP'},
 {status:'CLOSED',signalScore:99.4,rMultiple:1.5,reason:'TARGET'}
];
const sm=signalMetrics(rows);assert.equal(sm.n,3);assert.equal(sm.targets,2);assert.equal(sm.stops,1);assert.equal(sm.buckets.reduce((a,b)=>a+b.n,0),3);

await createAccount({username:'signal-alert-user',password:'LongPassword123!',email:'signal@example.test',plan:'free'});
await updateAccount('signal-alert-user',{emailVerifiedAt:new Date().toISOString()});
await setJson('tcc:signal-alert-user:alerts',{rules:{signalEmailEnabled:true},events:[]});
const ev={symbol:'AAPL',status:'OPEN',signalScore:97,asOf:'2026-09-25T10:00:00Z',direction:'LONG',entry:100,stop:95,target:107,expiresAt:'2026-09-25T11:40:00Z'};
const out=await publishSignalAlerts('signal-alert-user',[ev],'RUN-1');assert.equal(out.created,1);assert.equal(out.email.sent,true);
const out2=await publishSignalAlerts('signal-alert-user',[ev],'RUN-2');assert.equal(out2.created,0);
const mail=await emailOutbox();assert.equal(mail.length,1);
console.log('signal-features-smoke: OK');
