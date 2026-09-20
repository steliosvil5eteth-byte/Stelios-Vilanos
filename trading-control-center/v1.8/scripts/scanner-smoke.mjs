import assert from 'node:assert/strict';
import {evaluateSeries,backtest,metrics} from '../api/_lib/scanner.js';
function series(){const out=[];let p=100;const d=new Date('2024-01-01T00:00:00Z');for(let i=0;i<420;i++){d.setUTCDate(d.getUTCDate()+1);if([0,6].includes(d.getUTCDay())){i--;continue}const drift=.0012+Math.sin(i/17)*.0008;p*=1+drift;out.push({date:d.toISOString().slice(0,10),open:p*.998,high:p*1.012,low:p*.994,close:p,volume:1_000_000+(i%15)*80_000})}return out}
const s={minScore:45,minRR:1.5,maxHold:20,wTrend:30,wMomentum:25,wVolume:20,wVolatility:15,wRsi:10,slippageBps:5,commissionBps:2,scanMinBars:90,scanMinOosTrades:0,scanMinOosAvgR:-5,scanMinOosPF:0};
const rows=series(),e=evaluateSeries('TEST',rows,s);assert.equal(e.bars,420);assert.ok(e.setup);assert.ok(Number.isFinite(e.setup.score));const bt=backtest(rows,s);const m=metrics(bt);assert.equal(m.n,bt.length);assert.ok(Number.isFinite(m.avgR));
const tooShort=evaluateSeries('SHORT',rows.slice(-70),{...s,scanMinBars:90});assert.equal(tooShort.accepted,false);assert.ok(tooShort.reasons.some(x=>x.startsWith('INSUFFICIENT_BARS')));
console.log('scanner-smoke: OK');
