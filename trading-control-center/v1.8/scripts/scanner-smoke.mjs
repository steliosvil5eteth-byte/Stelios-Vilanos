import assert from 'node:assert/strict';
import {evaluateSeries,backtest,metrics,setupFromSeries} from '../api/_lib/scanner.js';
function series(){const out=[];let p=100;const d=new Date('2024-01-01T00:00:00Z');for(let i=0;i<420;i++){d.setUTCDate(d.getUTCDate()+1);if([0,6].includes(d.getUTCDay())){i--;continue}const drift=.0012+Math.sin(i/17)*.0008;p*=1+drift;out.push({date:d.toISOString().slice(0,10),open:p*.998,high:p*1.012,low:p*.994,close:p,volume:1_000_000+(i%15)*80_000})}return out}
const s={minScore:95,minRR:1,maxHold:20,wTrend:30,wMomentum:25,wVolume:20,wVolatility:15,wRsi:10,slippageBps:5,commissionBps:2,stopLossPct:5,targetMinPct:5,targetMaxPct:10,monthlyLossPct:10,barIntervalMinutes:5,scanMinBars:90,scanMinOosTrades:0,scanMinOosAvgR:-5,scanMinOosPF:0};
const rows=series(),setup=setupFromSeries('TEST',rows,s);assert.ok(setup);assert.ok(['LONG','SHORT'].includes(setup.direction));assert.ok(Number.isFinite(setup.score));assert.equal(setup.stopLossPct,5);assert.ok(setup.targetPct>=5&&setup.targetPct<=10);const adversePct=Math.abs(setup.stop/setup.entry-1)*100;assert.ok(Math.abs(adversePct-5)<1e-9);
const e=evaluateSeries('TEST',rows,s);assert.equal(e.bars,420);assert.ok(e.setup);assert.equal(e.signalPolicy.minScore,95);assert.equal(e.signalPolicy.stopLossPct,5);assert.deepEqual(e.signalPolicy.targetRangePct,[5,10]);
const bt=backtest(rows,s);const m=metrics(bt);assert.equal(m.n,bt.length);assert.ok(Number.isFinite(m.avgR));for(const t of bt){assert.equal(t.stopLossPct,5);assert.ok(t.score>=95);assert.ok(t.targetPct>=5&&t.targetPct<=10)}
const tooShort=evaluateSeries('SHORT',rows.slice(-70),{...s,scanMinBars:90});assert.equal(tooShort.accepted,false);assert.ok(tooShort.reasons.some(x=>x.startsWith('INSUFFICIENT_BARS')));
const forcedLow=evaluateSeries('LOW',rows,{...s,minScore:20});assert.equal(forcedLow.signalPolicy.minScore,95);
console.log('scanner-smoke: OK');
