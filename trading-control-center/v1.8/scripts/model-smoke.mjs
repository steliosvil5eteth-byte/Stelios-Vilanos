import assert from 'node:assert/strict';
import {syncUserModel,performanceForUser,evaluateAlerts,strategySnapshot} from '../api/_lib/model.js';
const user='smoke-user';
const settings={capital:10000,riskPct:.5,dailyLoss:2,maxPositionPct:25,maxExposurePct:100,maxOpen:5,slippageBps:5,commissionBps:2,minScore:68,minRR:2,maxHold:20,wTrend:30,wMomentum:25,wVolume:20,wVolatility:15,wRsi:10};
const strategy=strategySnapshot(settings);
const paper=[];
for(let i=0;i<35;i++){const win=i%3!==0;paper.push({id:`T${i}`,ticker:'TEST',entry:100,stop:98,target:104,current:win?104:98,qty:10,status:win?'TARGET':'STOP',opened:`2026-08-${String((i%28)+1).padStart(2,'0')}T10:00:00Z`,closedAt:`2026-09-${String((i%19)+1).padStart(2,'0')}T12:00:00Z`,broker:'SIMULATED',strategyId:strategy.id,strategyName:'Current strategy'})}
paper.push({id:'OPEN1',ticker:'NEAR',entry:100,stop:95,target:110,current:95.7,qty:5,status:'OPEN',opened:'2026-09-20T08:00:00Z',broker:'SIMULATED',strategyId:strategy.id,strategyName:'Current strategy'});
const sync=await syncUserModel(user,{settings,paper});assert.equal(sync.tradeCount,36);assert.equal(sync.currentStrategy.id,strategy.id);
const perf=await performanceForUser(user);assert.equal(perf.strategies[0].n,35);assert.equal(perf.strategies[0].sampleGate,true);assert.equal(perf.strategies[0].status,'TRACK_RECORD_AVAILABLE');
const alerts=await evaluateAlerts(user,{settings,paper});assert.ok(alerts.events.some(x=>x.type==='NEAR_STOP'));
console.log('model-smoke: OK');
