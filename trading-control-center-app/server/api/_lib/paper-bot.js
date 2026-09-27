// Pure, long-only paper engine. Never submits broker orders or charges money.
export const BOT_PLANS = Object.freeze({
  demo: {label:'Demo',priceEur:0,capitalMax:100,profitCap:200},
  a: {label:'Plan A',priceEur:10,capitalMax:100,profitCap:200},
  b: {label:'Plan B',priceEur:30,capitalMax:500,profitCap:1000}
});
export const POLICY = Object.freeze({stopPct:.05, monthlyLossPct:.10, riskPct:.01, feePct:.001, slippagePct:.001, maxQuoteAge:90000, maxCandleAge:180000});
const month = ts => new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Athens',year:'numeric',month:'2-digit'}).format(new Date(ts));
function fail(message){throw Object.assign(new Error(message),{status:400});}
export function createBot({plan='demo',capital=100}={},now=Date.now()) {
  const p=BOT_PLANS[plan]; if(!p || !Number.isFinite(capital)||capital<=0||capital>p.capitalMax)fail('Invalid plan or capital');
  return {version:1,mode:'PAPER',liveExecution:false,currency:'EUR',plan,capital,cash:capital,enabled:false,month:month(now),monthStartEquity:capital,monthHalt:null,position:null,trades:[],events:[],lastTick:0,lastEntryCandle:0,signal:null};
}
export function botMetrics(s){
  const equity=s.cash+(s.position?s.position.qty*s.position.mark:0),pnl=equity-s.monthStartEquity;
  const wins=s.trades.filter(t=>t.pnl>0).length,loss=s.trades.reduce((v,t)=>v+Math.max(0,-t.pnl),0),gain=s.trades.reduce((v,t)=>v+Math.max(0,t.pnl),0);
  return {equity,monthPnl:pnl,totalPnl:equity-s.capital,trades:s.trades.length,winRate:s.trades.length?wins/s.trades.length:null,profitFactor:loss?gain/loss:null,accuracy95Verified:false};
}
export function evaluateSignal(candles,news,now){
  if(!Array.isArray(candles)||candles.length<51)return {accepted:false,reason:'INSUFFICIENT_CANDLES'};
  if(candles.some((c,i)=>!Number.isFinite(c.ts)||!Number.isFinite(c.close)||c.close<=0||c.ts>now||(i>0&&c.ts-candles[i-1].ts!==60000)))return {accepted:false,reason:'INVALID_OR_GAPPED_CANDLES'};
  if(now-candles.at(-1).ts>POLICY.maxCandleAge)return {accepted:false,reason:'STALE_CANDLES'};
  if(!news||news.status!=='OK'||now-news.fetchedAt>15*60000||news.fetchedAt>now)return {accepted:false,reason:'NEWS_UNAVAILABLE'};
  // Headlines are context/risk filters, never a claimed probability of a price rise.
  if(news.negative)return {accepted:false,reason:'NEGATIVE_NEWS_FILTER'};
  const avg=n=>candles.slice(-n).reduce((a,c)=>a+c.close,0)/n;
  const price=candles.at(-1).close,fast=avg(20),slow=avg(50),momentum=price/candles.at(-6).close-1;
  const accepted=price>fast&&fast>slow&&momentum>.002&&momentum<.03;
  return {accepted,reason:accepted?'TREND_AND_MOMENTUM':'NO_SETUP',fast,slow,momentum,newsCount:news.articles?.length||0,probability:null};
}
export function tickBot(original,snapshot,now=Date.now(),{allowEntry=true}={}){
  const s=structuredClone(original),q=snapshot.quote;
  if(s.mode!=='PAPER'||s.liveExecution!==false)fail('PAPER_ONLY');
  if(!q||q.symbol!=='BTC-EUR'||![q.bid,q.ask,q.ts].every(Number.isFinite)||q.bid<=0||q.ask<q.bid||q.ts>now+5000||now-q.ts>POLICY.maxQuoteAge)fail('INVALID_OR_STALE_QUOTE');
  if(q.ts<=s.lastTick)return s; // replay/out-of-order ticks cannot duplicate orders
  s.lastTick=q.ts;
  // Carry positions into a new month at their LAST known mark, before this tick's P&L.
  if(s.month!==month(now)){s.month=month(now);s.monthStartEquity=botMetrics(s).equity;s.monthHalt=null;}
  if(s.position)s.position.mark=q.bid;
  const p=BOT_PLANS[s.plan];let metrics=botMetrics(s);
  if(metrics.monthPnl<=-s.monthStartEquity*POLICY.monthlyLossPct)s.monthHalt='MONTHLY_LOSS_LIMIT';
  if(metrics.monthPnl>=p.profitCap)s.monthHalt='MONTHLY_PROFIT_CAP';
  const event=(type,detail)=>{s.events.unshift({at:new Date(now).toISOString(),type,detail});s.events=s.events.slice(0,200)};
  const pos=s.position;
  if(pos){
    const reason=s.monthHalt|| (q.bid<=pos.stop?'STOP':q.bid>=pos.target?'TARGET':null);
    if(reason){
      const exit=q.bid*(1-POLICY.slippagePct),proceeds=pos.qty*exit*(1-POLICY.feePct);
      s.cash+=proceeds;s.trades.push({...pos,exit,pnl:proceeds-pos.cost,reason,closedAt:new Date(now).toISOString()});s.position=null;event('CLOSE',reason);
      if(botMetrics(s).monthPnl<=-s.monthStartEquity*POLICY.monthlyLossPct)s.monthHalt='MONTHLY_LOSS_LIMIT';
      if(botMetrics(s).monthPnl>=p.profitCap)s.monthHalt='MONTHLY_PROFIT_CAP';
      return s; // never reopen in the same tick
    }
  }
  s.signal=evaluateSignal(snapshot.candles,snapshot.news,now);
  if(!s.enabled||!allowEntry||s.monthHalt||s.position||!s.signal.accepted)return s;
  const candle=snapshot.candles.at(-1).ts;if(candle<=s.lastEntryCandle)return s;
  if((q.ask-q.bid)/q.bid>.005){s.signal={accepted:false,reason:'WIDE_SPREAD'};return s;}
  const entry=q.ask*(1+POLICY.slippagePct),stop=entry*(1-POLICY.stopPct),target=entry*(1+POLICY.stopPct*2);
  metrics=botMetrics(s);
  // Budget includes estimated entry+exit fees/slippage. No leverage; reserve loss capacity.
  const remainingLoss=Math.max(0,s.monthStartEquity*POLICY.monthlyLossPct+metrics.monthPnl);
  const budget=Math.min(metrics.equity*POLICY.riskPct,remainingLoss);
  const perUnitRisk=entry*(POLICY.stopPct+2*POLICY.feePct+POLICY.slippagePct);
  const qty=Math.min(budget/perUnitRisk,s.cash/(entry*(1+POLICY.feePct)));
  if(!(qty>0))return s;
  const cost=qty*entry*(1+POLICY.feePct);s.cash-=cost;
  s.position={id:`BTC-EUR-${q.ts}`,symbol:q.symbol,qty,entry,stop,target,cost,mark:q.bid,openedAt:new Date(now).toISOString()};s.lastEntryCandle=candle;
  event('OPEN','TREND_AND_MOMENTUM');return s;
}
