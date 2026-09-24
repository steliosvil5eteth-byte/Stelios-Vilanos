import {getJson,setJson} from './store.js';
import {strategyLifecycle} from './portfolio.js';

export const STRATEGY_KEYS=['minScore','minRR','maxHold','wTrend','wMomentum','wVolume','wVolatility','wRsi','slippageBps','commissionBps','riskPct','stopLossPct','targetMinPct','targetMaxPct','monthlyLossPct','dailyLoss','maxPositionPct','maxExposurePct','maxOpen','scanMinBars','scanMinOosTrades','scanMinOosAvgR','scanMinOosPF'];

function num(v,d=0){const n=Number(v);return Number.isFinite(n)?n:d}
export function stableStrategySettings(settings={}){
  return Object.fromEntries(STRATEGY_KEYS.map(k=>[k,num(settings[k])]))
}
export function strategyId(settings={}){
  const json=JSON.stringify(stableStrategySettings(settings)); let h=2166136261;
  for(let i=0;i<json.length;i++){h^=json.charCodeAt(i);h=Math.imul(h,16777619)}
  return `S-${(h>>>0).toString(16).padStart(8,'0')}`;
}
export function strategySnapshot(settings={},name='Current strategy'){
  const normalized=stableStrategySettings(settings);
  return {id:strategyId(normalized),name:String(name||'Current strategy').slice(0,80),settings:normalized,updatedAt:new Date().toISOString()};
}
function tradeNetPnl(t){
  const entry=num(t.entry),exit=num(t.current),qty=num(t.qty);
  const commission=Number.isFinite(Number(t.exitCommission))?Math.abs(num(t.exitCommission)):0;
  return (exit-entry)*qty-commission;
}
function tradeR(t){const risk=Math.max(.0001,(num(t.entry)-num(t.stop))*num(t.qty));return tradeNetPnl(t)/risk}
export function normalizeTrade(t={},fallbackStrategy=null){
  const id=String(t.id||`TRADE-${Date.now()}-${Math.random().toString(36).slice(2,7)}`).slice(0,120);
  const strategy=t.strategyId?String(t.strategyId):fallbackStrategy?.id||'LEGACY';
  return {
    id,ticker:String(t.ticker||'').toUpperCase().slice(0,20),entry:num(t.entry),stop:num(t.stop),target:num(t.target),current:num(t.current),qty:num(t.qty),
    status:String(t.status||'').slice(0,30),opened:t.opened||null,closedAt:t.closedAt||null,broker:String(t.broker||'PAPER').slice(0,40),source:String(t.source||'').slice(0,40),
    conid:t.conid?num(t.conid):null,executionId:t.executionId?String(t.executionId).slice(0,120):null,exitCommission:Number.isFinite(Number(t.exitCommission))?num(t.exitCommission):null,
    strategyId:strategy,strategyName:String(t.strategyName||fallbackStrategy?.name||'Legacy / unversioned').slice(0,80),
    netPnl:tradeNetPnl(t),rMultiple:tradeR(t),updatedAt:new Date().toISOString()
  };
}
export async function syncUserModel(user,{settings={},paper=[]}={}){
  const now=new Date().toISOString();
  const profileKey=`tcc:${user}:profile`,strategyKey=`tcc:${user}:strategies`,tradesKey=`tcc:${user}:trades`;
  const profile=(await getJson(profileKey))||{user,createdAt:now};
  profile.lastSeenAt=now; await setJson(profileKey,profile);
  const current=strategySnapshot(settings,'Current strategy');
  const strategies=(await getJson(strategyKey))||[];
  const si=strategies.findIndex(x=>x.id===current.id);
  if(si>=0)strategies[si]={...strategies[si],...current,lastUsedAt:now};else strategies.unshift({...current,createdAt:now,lastUsedAt:now});
  await setJson(strategyKey,strategies.slice(0,100));
  const existing=(await getJson(tradesKey))||[]; const map=new Map(existing.map(x=>[String(x.id),x]));
  for(const raw of Array.isArray(paper)?paper:[]){const t=normalizeTrade(raw,current);map.set(String(t.id),{...map.get(String(t.id)),...t})}
  const trades=[...map.values()].sort((a,b)=>String(b.closedAt||b.opened||'').localeCompare(String(a.closedAt||a.opened||''))).slice(0,3000);
  await setJson(tradesKey,trades);
  return {currentStrategy:current,strategyCount:strategies.length,tradeCount:trades.length};
}
function wilson95(w,n){if(!n)return [0,0];const z=1.96,p=w/n,den=1+z*z/n,center=(p+z*z/(2*n))/den,margin=z*Math.sqrt((p*(1-p)+z*z/(4*n))/n)/den;return [Math.max(0,center-margin)*100,Math.min(1,center+margin)*100]}
function metrics(rows){
  const closed=rows.filter(t=>t.closedAt&&t.status!=='OPEN'); const n=closed.length;
  let eq=0,peak=0,maxDD=0,gp=0,gl=0,wins=0,sumR=0;
  for(const t of closed.slice().sort((a,b)=>String(a.closedAt).localeCompare(String(b.closedAt)))){
    const pnl=num(t.netPnl),r=num(t.rMultiple);eq+=pnl;peak=Math.max(peak,eq);maxDD=Math.max(maxDD,peak-eq);sumR+=r;if(pnl>0){wins++;gp+=pnl}else gl+=Math.abs(pnl)
  }
  const ci=wilson95(wins,n); const avgR=n?sumR/n:0; const pf=gl?gp/gl:(gp?999:0);
  return {n,wins,winRate:n?wins/n*100:null,winRate95:ci,netPnl:eq,avgR,profitFactor:pf,maxDrawdown:maxDD,sampleGate:n>=30,status:n<30?'INSUFFICIENT_SAMPLE':avgR<=0?'NON_POSITIVE_EXPECTANCY':'TRACK_RECORD_AVAILABLE'};
}
export async function performanceForUser(user){
  const strategies=(await getJson(`tcc:${user}:strategies`))||[]; const trades=(await getJson(`tcc:${user}:trades`))||[];
  const ids=new Set([...strategies.map(x=>x.id),...trades.map(x=>x.strategyId||'LEGACY')]);
  const rows=[...ids].map(id=>{const s=strategies.find(x=>x.id===id);const relevant=trades.filter(t=>(t.strategyId||'LEGACY')===id);const m=metrics(relevant),life=strategyLifecycle(relevant);return {strategyId:id,name:s?.name||trades.find(t=>t.strategyId===id)?.strategyName||'Legacy / unversioned',settings:s?.settings||null,...m,lifecycle:life.lifecycle,executionEligible:life.executionEligible,lifecycleReason:life.reason,recentAvgR:life.recentAvgR}})
    .sort((a,b)=>b.n-a.n||b.netPnl-a.netPnl);
  return {strategies:rows,totalTrades:trades.length,closedTrades:trades.filter(t=>t.closedAt&&t.status!=='OPEN').length};
}
export async function evaluateAlerts(user,state={}){
  const key=`tcc:${user}:alerts`; const saved=(await getJson(key))||{}; const rules={nearStopPct:1,nearTargetPct:1,dailyLossWarnPct:80,maxOpenWarnPct:100,...saved.rules};
  const paper=Array.isArray(state.paper)?state.paper:[]; const settings=state.settings||{}; const now=new Date(),day=now.toISOString().slice(0,10); const candidates=[];
  for(const t of paper.filter(x=>x.status==='OPEN')){
    const cur=num(t.current),stop=num(t.stop),target=num(t.target); if(cur<=0)continue;
    const stopDist=(cur-stop)/cur*100,targetDist=(target-cur)/cur*100;
    if(stopDist>=0&&stopDist<=rules.nearStopPct)candidates.push({type:'NEAR_STOP',severity:'warning',tradeId:String(t.id),ticker:t.ticker,message:`${t.ticker}: ${stopDist.toFixed(2)}% πάνω από stop`,dedupe:`${day}:NEAR_STOP:${t.id}`});
    if(targetDist>=0&&targetDist<=rules.nearTargetPct)candidates.push({type:'NEAR_TARGET',severity:'info',tradeId:String(t.id),ticker:t.ticker,message:`${t.ticker}: ${targetDist.toFixed(2)}% κάτω από target`,dedupe:`${day}:NEAR_TARGET:${t.id}`});
  }
  const capital=num(settings.capital),dailyLimit=capital*num(settings.dailyLoss)/100;
  const realized=paper.filter(t=>String(t.closedAt||'').slice(0,10)===day).reduce((a,t)=>a+tradeNetPnl(t),0);
  if(dailyLimit>0&&realized<0&&Math.abs(realized)>=dailyLimit*rules.dailyLossWarnPct/100)candidates.push({type:'DAILY_LOSS_LIMIT_NEAR',severity:'critical',message:`Daily realized loss ${Math.abs(realized).toFixed(2)} / limit ${dailyLimit.toFixed(2)}`,dedupe:`${day}:DAILY_LOSS_LIMIT_NEAR`});
  const maxOpen=Math.max(1,num(settings.maxOpen,1)),open=paper.filter(t=>t.status==='OPEN').length;
  if(open>=maxOpen*rules.maxOpenWarnPct/100)candidates.push({type:'OPEN_POSITION_LIMIT',severity:'warning',message:`Open positions ${open} / max ${maxOpen}`,dedupe:`${day}:OPEN_POSITION_LIMIT`});
  const events=Array.isArray(saved.events)?saved.events:[]; const seen=new Set(events.map(x=>x.dedupe));
  for(const c of candidates)if(!seen.has(c.dedupe))events.unshift({...c,id:`AL-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,createdAt:new Date().toISOString(),acknowledged:false});
  const next={rules,events:events.slice(0,300),evaluatedAt:new Date().toISOString()}; await setJson(key,next); return next;
}
