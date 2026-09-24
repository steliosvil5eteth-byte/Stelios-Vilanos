function num(v,d=0){const n=Number(v);return Number.isFinite(n)?n:d}
function clamp(v,a,b){return Math.max(a,Math.min(b,v))}
function avg(a){return a.length?a.reduce((x,y)=>x+y,0)/a.length:0}
function sd(a){if(a.length<2)return 0;const m=avg(a);return Math.sqrt(avg(a.map(x=>(x-m)**2)))}
function sma(a,p,i){if(i<p-1)return null;return avg(a.slice(i-p+1,i+1))}
function atr(series,p,i){if(i<p)return null;const tr=[];for(let j=i-p+1;j<=i;j++){const prev=series[j-1].close;tr.push(Math.max(series[j].high-series[j].low,Math.abs(series[j].high-prev),Math.abs(series[j].low-prev)))}return avg(tr)}
function rsi(series,p,i){if(i<p)return null;let g=0,l=0;for(let j=i-p+1;j<=i;j++){const d=series[j].close-series[j-1].close;if(d>=0)g+=d;else l-=d}if(l===0)return 100;const rs=(g/p)/(l/p);return 100-100/(1+rs)}
export function indicators(series,i,s={}){if(i<55)return null;const closes=series.map(x=>x.close),vols=series.map(x=>x.volume);const s20=sma(closes,20,i),s50=sma(closes,50,i),a14=atr(series,14,i),r14=rsi(series,14,i),mom=(series[i].close/series[i-20].close-1)*100,vr=series[i].volume/(avg(vols.slice(i-20,i))||1);const rets=[];for(let j=i-19;j<=i;j++)rets.push((series[j].close/series[j-1].close-1)*100);const mins=Math.max(0,num(s.barIntervalMinutes,0)),barsPerYear=mins?252*(390/mins):252,vol=sd(rets)*Math.sqrt(barsPerYear);return {s20,s50,atr:a14,rsi:r14,momentum:mom,volumeRatio:vr,annualVol:vol,price:series[i].close}}
function weights(s){const a=[num(s.wTrend),num(s.wMomentum),num(s.wVolume),num(s.wVolatility),num(s.wRsi)],sum=a.reduce((x,y)=>x+y,0)||1;return a.map(v=>v/sum)}
export function directionalScores(ind,s){
  const w=weights(s);
  const trendLong=clamp(50+((ind.price/ind.s50-1)*500)+((ind.s20/ind.s50-1)*500),0,100);
  const trendShort=100-trendLong;
  const momentumLong=clamp(50+ind.momentum*4,0,100),momentumShort=100-momentumLong;
  const volume=clamp(40+(ind.volumeRatio-1)*55,0,100);
  const volq=clamp(100-Math.abs(ind.annualVol-28)*2,0,100);
  const rsiLong=clamp(100-Math.abs(ind.rsi-58)*2.5,0,100);
  const rsiShort=clamp(100-Math.abs(ind.rsi-42)*2.5,0,100);
  const long=trendLong*w[0]+momentumLong*w[1]+volume*w[2]+volq*w[3]+rsiLong*w[4];
  const short=trendShort*w[0]+momentumShort*w[1]+volume*w[2]+volq*w[3]+rsiShort*w[4];
  return {long,short};
}
export function scoreFromIndicators(ind,s){const d=directionalScores(ind,s);return Math.max(d.long,d.short)}
function tradeGeometry(entry,score,direction,s){
  const stopPct=5;
  const targetMin=clamp(num(s.targetMinPct,5),5,10);
  const targetMax=clamp(num(s.targetMaxPct,10),targetMin,10);
  const scaled=clamp((score-95)/5,0,1);
  const targetPct=targetMin+(targetMax-targetMin)*scaled;
  const stop=direction==='SHORT'?entry*(1+stopPct/100):entry*(1-stopPct/100);
  const target=direction==='SHORT'?entry*(1-targetPct/100):entry*(1+targetPct/100);
  const rr=targetPct/stopPct;
  return {stop,target,rr,stopLossPct:stopPct,targetPct};
}
export function setupFromSeries(symbol,series,s){
  const i=series.length-1,ind=indicators(series,i,s);if(!ind)return null;
  const scores=directionalScores(ind,s),direction=scores.long>=scores.short?'LONG':'SHORT',score=Math.max(scores.long,scores.short),entry=series[i].close;
  const g=tradeGeometry(entry,score,direction,s);
  const trendPct=(ind.price/ind.s50-1)*100;
  const rationale=[
    `Direction ${direction} from long ${scores.long.toFixed(1)} vs short ${scores.short.toFixed(1)}`,
    `Price vs SMA50 ${trendPct>=0?'+':''}${trendPct.toFixed(2)}%`,
    `20-bar momentum ${ind.momentum>=0?'+':''}${ind.momentum.toFixed(2)}%`,
    `Volume ${ind.volumeRatio.toFixed(2)}x recent average`,
    `RSI ${ind.rsi.toFixed(1)}`
  ];
  return {ticker:symbol,asOf:series[i].date,bars:series.length,score,direction,entry,...g,atr:ind.atr,rsi:ind.rsi,momentum:ind.momentum,annualVol:ind.annualVol,volumeRatio:ind.volumeRatio,longScore:scores.long,shortScore:scores.short,rationale};
}
export function backtest(series,s){
  const trades=[];let i=55;const slip=num(s.slippageBps)/10000,comm=num(s.commissionBps)/10000,maxHold=Math.max(1,num(s.maxHold,20)),minScore=Math.max(95,num(s.minScore,95));
  while(i<series.length-2){
    const ind=indicators(series,i,s);if(!ind){i++;continue}
    const scores=directionalScores(ind,s),direction=scores.long>=scores.short?'LONG':'SHORT',score=Math.max(scores.long,scores.short);
    if(score<minScore){i++;continue}
    const entryIdx=i+1,rawEntry=series[entryIdx].open,entry=direction==='SHORT'?rawEntry*(1-slip):rawEntry*(1+slip),g=tradeGeometry(entry,score,direction,s),stop=g.stop,target=g.target;
    let rawExit=series[Math.min(entryIdx+maxHold,series.length-1)].close,reason='TIME',exitIdx=Math.min(entryIdx+maxHold,series.length-1);
    for(let j=entryIdx;j<=Math.min(entryIdx+maxHold,series.length-1);j++){
      const b=series[j];
      if(direction==='LONG'){
        if(b.low<=stop){rawExit=stop;reason='STOP';exitIdx=j;break}
        if(b.high>=target){rawExit=target;reason='TARGET';exitIdx=j;break}
      }else{
        if(b.high>=stop){rawExit=stop;reason='STOP';exitIdx=j;break}
        if(b.low<=target){rawExit=target;reason='TARGET';exitIdx=j;break}
      }
    }
    const exit=direction==='SHORT'?rawExit*(1+slip):rawExit*(1-slip),fees=(entry+exit)*comm,risk=Math.max(.0001,Math.abs(entry-stop));
    const pnlPerShare=direction==='SHORT'?(entry-exit)-fees:(exit-entry)-fees,R=pnlPerShare/risk;
    trades.push({signalDate:series[i].date,entryDate:series[entryIdx].date,exitDate:series[exitIdx].date,entry,exit,R,reason,score,direction,stop,target,targetPct:g.targetPct,stopLossPct:g.stopLossPct});
    i=Math.max(i+1,exitIdx+1)
  }
  return trades
}
export function metrics(trades){if(!trades.length)return {n:0,wins:0,winRate:0,avgR:0,profitFactor:0,maxDrawdown:0};const wins=trades.filter(t=>t.R>0),loss=trades.filter(t=>t.R<=0),gp=wins.reduce((a,t)=>a+t.R,0),gl=Math.abs(loss.reduce((a,t)=>a+t.R,0));let eq=0,peak=0,mdd=0;for(const t of trades){eq+=t.R;peak=Math.max(peak,eq);mdd=Math.max(mdd,peak-eq)}return {n:trades.length,wins:wins.length,winRate:wins.length/trades.length*100,avgR:avg(trades.map(t=>t.R)),profitFactor:gl?gp/gl:(gp?999:0),maxDrawdown:mdd}}
export function evaluateSeries(symbol,series,s){
  const setup=setupFromSeries(symbol,series,s);const reasons=[];const minBars=Math.max(60,num(s.scanMinBars,250)),minScore=Math.max(95,num(s.minScore,95));
  if(series.length<minBars)reasons.push(`INSUFFICIENT_BARS:${series.length}<${minBars}`);
  if(!setup)return {symbol,accepted:false,reasons:[...reasons,'NO_INDICATORS'],bars:series.length};
  if(setup.score<minScore)reasons.push(`LOW_SCORE:${setup.score.toFixed(1)}<${minScore}`);
  const minRR=Math.max(1,num(s.minRR,1));
  if(setup.rr<minRR)reasons.push(`LOW_RR:${setup.rr.toFixed(2)}<${minRR.toFixed(2)}`);
  const trades=backtest(series,{...s,minScore}),split=Math.floor(series.length*.7),cut=series[split]?.date,oos=metrics(trades.filter(t=>!cut||t.entryDate>=cut));
  const minOosTrades=Math.max(0,num(s.scanMinOosTrades,5)),minOosAvgR=num(s.scanMinOosAvgR,0),minOosPF=Math.max(0,num(s.scanMinOosPF,1));
  if(oos.n<minOosTrades)reasons.push(`INSUFFICIENT_OOS_TRADES:${oos.n}<${minOosTrades}`);
  if(oos.n>=minOosTrades&&oos.avgR<=minOosAvgR)reasons.push(`NON_POSITIVE_OOS_EXPECTANCY:${oos.avgR.toFixed(2)}<=${minOosAvgR.toFixed(2)}`);
  if(oos.n>=minOosTrades&&oos.profitFactor<minOosPF)reasons.push(`LOW_OOS_PROFIT_FACTOR:${oos.profitFactor.toFixed(2)}<${minOosPF.toFixed(2)}`);
  return {symbol,accepted:reasons.length===0,reasons,setup,oos,bars:series.length,totalBacktestTrades:trades.length,signalPolicy:{minScore,stopLossPct:5,targetRangePct:[5,10],execution:'USER_DECIDES'}};
}
