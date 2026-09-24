import assert from 'node:assert/strict';
import {updateForwardLedger,getSignals} from '../api/_lib/signal-ledger.js';

const user='short-ledger-smoke';
const strategy={id:'S-SHORT-SMOKE',name:'Short smoke'};
const settings={slippageBps:0,commissionBps:0,maxHold:20};
const base=[{symbol:'XYZ',provider:'test',series:[{date:'2026-09-25T10:00:00Z',open:100,high:100,low:100,close:100,volume:1000}]}];
const evaluation={symbol:'XYZ',accepted:true,setup:{ticker:'XYZ',asOf:'2026-09-25T10:00:00Z',direction:'SHORT',entry:100,stop:105,target:90,score:98,rr:2,stopLossPct:5,targetPct:10},signalScore:97,event:{score:93,direction:'SHORT',articles:[{title:'Negative catalyst'}]},oos:null};
await updateForwardLedger(user,{fetched:base,evaluations:[evaluation],strategy,settings});
let rows=await getSignals(user,20);let sig=rows.find(x=>x.strategyId===strategy.id&&x.symbol==='XYZ');assert.ok(sig);assert.equal(sig.direction,'SHORT');assert.equal(sig.status,'OPEN');
const future=[{symbol:'XYZ',provider:'test',series:[...base[0].series,{date:'2026-09-25T10:05:00Z',open:99,high:101,low:89,close:90,volume:1500}]}];
await updateForwardLedger(user,{fetched:future,evaluations:[],strategy,settings});
rows=await getSignals(user,20);sig=rows.find(x=>x.strategyId===strategy.id&&x.symbol==='XYZ');assert.equal(sig.status,'CLOSED');assert.equal(sig.reason,'TARGET');assert.equal(sig.exit,90);assert.ok(Math.abs(sig.rMultiple-2)<1e-9);
console.log('short-ledger-smoke: OK');
