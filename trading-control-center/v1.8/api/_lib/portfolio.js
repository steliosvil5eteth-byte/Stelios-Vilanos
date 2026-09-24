import {getJson,setJson} from './store.js';
import {fetchAlphaDaily} from './market-data.js';

function num(v,d=0){const n=Number(v);return Number.isFinite(n)?n:d}
function isClosed(t){return Boolean(t?.closedAt)&&String(t?.status||'').toUpperCase()!=='OPEN'}
function pnl(t){return Number.isFinite(Number(t?.netPnl))?num(t.netPnl):(num(t.current)-num(t.entry))*num(t.qty)-Math.abs(num(t.exitCommission))}
function risk(t){return Math.max(0,(num(t.entry)-num(t.stop))*num(t.qty))}
function unrealized(t){return (num(t.current)-num(t.entry))*num(t.qty)}
function wilson95(w,n){if(!n)return [0,0];const z=1.96,p=w/n,den=1+z*z/n,center=(p+z*z/(2*n))/den,margin=z*Math.sqrt((p*(1-p)+z*z/(4*n))/n)/den;return [Math.max(0,center-margin)*100,Math.min(1,center+margin)*100]}

export function strategyLifecycle(rows=[]){
  const closed=rows.filter(isClosed).slice().sort((a,b)=>String(a.closedAt).localeCompare(String(b.closedAt)));
  const n=closed.length,wins=closed.filter(t=>pnl(t)>0).length;
  const rs=closed.map(t=>{const r=risk(t);return r?pnl(t)/r:0});
  const avgR=n?rs.reduce((a,b)=>a+b,0)/n:0;
  const recent=rs.slice(-20),recentAvgR=recent.length?recent.reduce((a,b)=>a+b,0)/recent.length:0;
  let gp=0,gl=0,eq=0,peak=0,maxDD=0;
  for(const t of closed){const p=pnl(t);eq+=p;peak=Math.max(peak,eq);maxDD=Math.max(maxDD,peak-eq);if(p>0)gp+=p;else gl+=Math.abs(p)}
  const pf=gl?gp/gl:(gp?999:0),ci=wilson95(wins,n);
  let lifecycle='LEARNING',executionEligible=true,reason='Χρειάζονται περισσότερα κλειστά paper trades.';
  if(n>=60&&avgR<=-0.10&&pf<0.80){lifecycle='RETIRED';executionEligible=false;reason='≥60 trades, Avg R ≤ -0.10 και Profit Factor < 0.80.'}
  else if(n>=30&&(avgR<=0||pf<0.90)){lifecycle='PAUSED';executionEligible=false;reason='≥30 trades και μη θετικό expectancy ή Profit Factor < 0.90.'}
  else if(n>=30&&(recentAvgR<=0||pf<1.05)){lifecycle='WATCH';executionEligible=true;reason='Θετικό μακροχρόνιο ιστορικό αλλά αδύναμο πρόσφατο 20-trade window ή PF < 1.05.'}
  else if(n>=30){lifecycle='ACTIVE';executionEligible=true;reason='≥30 trades με θετικό Avg R και Profit Factor ≥ 1.05.'}
  return {n,wins,winRate:n?wins/n*100:null,winRate95:ci,avgR,recentAvgR,profitFactor:pf,maxDrawdown:maxDD,lifecycle,executionEligible,reason};
}

export function portfolioMetrics({settings={},trades=[]}={}){
  const capital=Math.max(0,num(settings.capital));
  const open=trades.filter(t=>String(t.status||'').toUpperCase()==='OPEN');
  const closed=trades.filter(isClosed).slice().sort((a,b)=>String(a.closedAt).localeCompare(String(b.closedAt)));
  const realized=closed.reduce((a,t)=>a+pnl(t),0),unrl=open.reduce((a,t)=>a+unrealized(t),0);
  const exposure=open.reduce((a,t)=>a+Math.max(0,num(t.current||t.entry)*num(t.qty)),0);
  const stopStress=open.reduce((a,t)=>a+risk(t),0);
  let eq=capital,peak=capital,maxDD=0;const curve=[];
  for(const t of closed){eq+=pnl(t);peak=Math.max(peak,eq);maxDD=Math.max(maxDD,peak-eq);curve.push({ts:t.closedAt,equity:eq,pnl:pnl(t),ticker:t.ticker,strategyId:t.strategyId||'LEGACY'})}
  const equity=capital+realized+unrl;
  const bySymbol=Object.values(open.reduce((m,t)=>{const k=String(t.ticker||'').toUpperCase()||'UNKNOWN';const value=Math.max(0,num(t.current||t.entry)*num(t.qty));m[k]??={ticker:k,value:0,risk:0,count:0};m[k].value+=value;m[k].risk+=risk(t);m[k].count++;return m},{})).sort((a,b)=>b.value-a.value);
  const byStrategy=Object.values(trades.reduce((m,t)=>{const k=t.strategyId||'LEGACY';m[k]??={strategyId:k,name:t.strategyName||'Legacy / unversioned',rows:[]};m[k].rows.push(t);return m},{})).map(g=>({...g,lifecycle:strategyLifecycle(g.rows)})).sort((a,b)=>b.lifecycle.n-a.lifecycle.n);
  const maxExposure=capital*Math.max(0,num(settings.maxExposurePct))/100;
  const dailyLossLimit=capital*Math.max(0,num(settings.dailyLoss))/100;
  const maxPosition=capital*Math.max(0,num(settings.maxPositionPct))/100;
  const today=new Date().toISOString().slice(0,10),month=today.slice(0,7);const dailyRealized=closed.filter(t=>String(t.closedAt).slice(0,10)===today).reduce((a,t)=>a+pnl(t),0),monthlyRealized=closed.filter(t=>String(t.closedAt).slice(0,7)===month).reduce((a,t)=>a+pnl(t),0),monthlyLossLimit=capital*Math.max(0,num(settings.monthlyLossPct,10))/100,monthlyLossHit=monthlyLossLimit>0&&monthlyRealized<=-monthlyLossLimit;
  return {asOf:new Date().toISOString(),capital,equity,realizedPnl:realized,unrealizedPnl:unrl,openPositions:open.length,exposure,exposurePct:capital?exposure/capital*100:0,maxExposure,exposureUtilizationPct:maxExposure?exposure/maxExposure*100:0,stopLossStress:stopStress,stopLossStressPct:capital?stopStress/capital*100:0,maxPosition,dailyRealized,dailyLossLimit,monthlyRealized,monthlyLossLimit,monthlyLossHit,maxDrawdown:maxDD,maxDrawdownPct:capital?maxDD/capital*100:0,equityCurve:curve.slice(-500),bySymbol,byStrategy};
}

function valueOnOrAfter(series,date){const row=series.find(x=>x.date>=date)||series.at(-1);return row?.close||null}
function valueOnOrBefore(series,date){const rows=series.filter(x=>x.date<=date);return rows.at(-1)?.close||series[0]?.close||null}
export async function benchmarkComparison(user,trades=[],symbol='SPY'){
  const closed=trades.filter(isClosed).sort((a,b)=>String(a.closedAt).localeCompare(String(b.closedAt)));
  if(closed.length<2)return {symbol,status:'INSUFFICIENT_TRADES'};
  const start=String(closed[0].closedAt).slice(0,10),end=String(closed.at(-1).closedAt).slice(0,10);
  const key=`tcc:benchmark:${symbol}`;let cache=await getJson(key);const age=cache?.fetchedAt?Date.now()-Date.parse(cache.fetchedAt):Infinity;
  if(!cache?.series||age>6*3600e3){
    try{let r;try{r=await fetchAlphaDaily(symbol,{outputsize:'full'})}catch{r=await fetchAlphaDaily(symbol,{outputsize:'compact'})}cache={symbol,series:r.series,fetchedAt:new Date().toISOString(),outputsize:r.outputsize};await setJson(key,cache)}catch(e){return {symbol,status:'UNAVAILABLE',error:e.message}}
  }
  const a=valueOnOrAfter(cache.series,start),b=valueOnOrBefore(cache.series,end);if(!(a>0&&b>0))return {symbol,status:'NO_OVERLAP'};
  const benchmarkReturn=(b/a-1)*100;
  return {symbol,status:'OK',start,end,startPrice:a,endPrice:b,returnPct:benchmarkReturn,fetchedAt:cache.fetchedAt};
}

export function correlationFromSeries(seriesBySymbol={},symbols=[],lookback=60){
  const unique=[...new Set(symbols.map(x=>String(x).toUpperCase()))].filter(Boolean);const pairs=[];
  function returns(series){const rows=(series||[]).slice(-Math.max(lookback+1,2));const out=new Map();for(let i=1;i<rows.length;i++){const p=num(rows[i-1].close),c=num(rows[i].close);if(p>0&&c>0)out.set(rows[i].date,c/p-1)}return out}
  const ret=Object.fromEntries(unique.map(s=>[s,returns(seriesBySymbol[s])]));
  for(let i=0;i<unique.length;i++)for(let j=i+1;j<unique.length;j++){const a=ret[unique[i]],b=ret[unique[j]],xs=[],ys=[];for(const [d,x] of a)if(b.has(d)){xs.push(x);ys.push(b.get(d))}if(xs.length<20)continue;const mx=xs.reduce((p,c)=>p+c,0)/xs.length,my=ys.reduce((p,c)=>p+c,0)/ys.length;let cov=0,vx=0,vy=0;for(let k=0;k<xs.length;k++){const dx=xs[k]-mx,dy=ys[k]-my;cov+=dx*dy;vx+=dx*dx;vy+=dy*dy}const corr=vx&&vy?cov/Math.sqrt(vx*vy):0;pairs.push({a:unique[i],b:unique[j],correlation:corr,n:xs.length})}
  return pairs.sort((x,y)=>Math.abs(y.correlation)-Math.abs(x.correlation));
}

export async function strategyExecutionGate(user,strategyId){
  if(!strategyId)return {allowed:true,lifecycle:'UNKNOWN',reason:'No strategy id supplied'};
  const trades=(await getJson(`tcc:${user}:trades`))||[];const rows=trades.filter(t=>(t.strategyId||'LEGACY')===strategyId);const life=strategyLifecycle(rows);return {allowed:life.executionEligible,lifecycle:life.lifecycle,reason:life.reason,metrics:life};
}
