import {getJson,setJson,appendAudit} from './store.js';
import {fetchSignalMarketMany,marketDataConfig,signalMarketConfig} from './market-data.js';
import {updateForwardLedger} from './signal-ledger.js';
import {evaluateSeries} from './scanner.js';
import {strategySnapshot} from './model.js';
import {marketFreshness} from './freshness.js';
import {portfolioMetrics} from './portfolio.js';
import {fetchEventSignal,eventDataConfig,combineTechnicalAndEvent} from './event-data.js';
import {signalPortfolioContext} from './holdings.js';
import {publishSignalAlerts} from './signal-alerts.js';

function symbolsFrom(value,maxSymbols=5){
  const arr=Array.isArray(value)?value:String(value||'').split(',');
  return [...new Set(arr.map(x=>String(x).trim().toUpperCase()).filter(x=>/^[A-Z0-9.\\/:-]{1,24}$/.test(x)))].slice(0,Math.max(1,Math.min(25,Number(maxSymbols)||5)));
}

export async function runServerScan(user,{symbols=null,source='manual',maxSymbols=5}={}){
  if(!user)throw new Error('user required');
  const state=(await getJson(`tcc:${user}:state`))||{},holdings=(await getJson(`tcc:${user}:holdings`))||[];const settings=state.settings||{},riskState=portfolioMetrics({settings,trades:Array.isArray(state.paper)?state.paper:[]});
  const configured=symbolsFrom(symbols?.length?symbols:(state.scanConfig?.symbols||process.env.SCAN_SYMBOLS||''),maxSymbols);
  if(!configured.length)throw new Error('No server scan symbols configured');
  const startedAt=new Date().toISOString();const fetched=await fetchSignalMarketMany(configured);
  const evaluations=[];const eventCfg=eventDataConfig(),signalCfg=signalMarketConfig();
  for(const item of fetched){
    if(item.error){evaluations.push({symbol:item.symbol,accepted:false,reasons:[`DATA_ERROR:${item.error}`],bars:0});continue}
    const freshness=marketFreshness(item.series);
    const interval=String(item.interval||signalCfg.interval),m=interval.match(/^(\\d+)(min|h)$/),barIntervalMinutes=m?(m[2]==='h'?Number(m[1])*60:Number(m[1])):0,scanSettings={...settings,barIntervalMinutes};const ev=evaluateSeries(item.symbol,item.series,scanSettings);ev.marketFreshness=freshness;ev.marketMode=item.mode||'unknown';ev.interval=interval;
    if(!freshness.ok){ev.accepted=false;ev.reasons=[...(ev.reasons||[]),`STALE_MARKET_DATA:${freshness.reason}`];evaluations.push(ev);continue}
    if(!ev.setup||ev.setup.score<95){evaluations.push(ev);continue}
    const event=await fetchEventSignal(item.symbol);ev.event=event;ev.technicalScore=ev.setup.score;
    const gate=combineTechnicalAndEvent(ev.setup,event,{required:eventCfg.required,minEventScore:eventCfg.minEventScore});
    ev.signalScore=gate.signalScore;ev.setup.signalScore=gate.signalScore;ev.setup.eventScore=gate.eventScore;ev.setup.eventDirection=gate.eventDirection;
    ev.reasons.push(...gate.reasons.filter(x=>!ev.reasons.includes(x)));if(riskState.monthlyLossHit)ev.reasons.push('MONTHLY_LOSS_LOCK:-10%');ev.accepted=ev.reasons.length===0;
    if(ev.setup){
      ev.portfolioContext=signalPortfolioContext(ev.setup,holdings);
      const headline=event.articles?.[0]?.title||event.sec?.filings?.[0]?.form||'No fresh event headline';
      ev.setup.rationale=[...(ev.setup.rationale||[]),`Event score ${event.score.toFixed(1)} / direction ${event.direction}`,`Fresh event: ${headline}`];
    }
    evaluations.push(ev);
  }
  evaluations.sort((a,b)=>Number(b.accepted)-Number(a.accepted)||(b.signalScore||b.setup?.score||0)-(a.signalScore||a.setup?.score||0));
  const current=strategySnapshot({...settings,barIntervalMinutes:(()=>{const m=String(signalCfg.interval).match(/^(\\d+)(min|h)$/);return m?(m[2]==='h'?Number(m[1])*60:Number(m[1])):0})()},state.strategy?.name||'Current strategy');
  const providers=[...new Set(fetched.filter(x=>!x.error).map(x=>x.provider).filter(Boolean))];
  const ledger=await updateForwardLedger(user,{fetched,evaluations,strategy:current,settings:{...settings,barIntervalMinutes:current.settings.barIntervalMinutes}});
  const run={id:`SCAN-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,source,provider:providers.length===1?providers[0]:'mixed',providers,marketDataConfig:marketDataConfig(),signalMarketConfig:signalCfg,eventDataConfig:eventCfg,riskState:{monthlyRealized:riskState.monthlyRealized,monthlyLossLimit:riskState.monthlyLossLimit,monthlyLossHit:riskState.monthlyLossHit},startedAt,completedAt:new Date().toISOString(),strategyId:current.id,symbols:configured,evaluations,accepted:evaluations.filter(x=>x.accepted).length,rejected:evaluations.filter(x=>!x.accepted).length,forwardLedger:{changed:ledger.changed,open:ledger.open,closed:ledger.closed}};
  run.alerts=await publishSignalAlerts(user,evaluations,run.id);const key=`tcc:${user}:scanRuns`;const rows=(await getJson(key))||[];rows.unshift(run);await setJson(key,rows.slice(0,100));
  await appendAudit(user,{ts:new Date().toISOString(),type:'SERVER_SCAN',detail:`${source} symbols=${configured.length} accepted=${run.accepted} rejected=${run.rejected} strategy=${current.id}`});
  return run;
}

export async function getScanRuns(user,limit=20){const rows=(await getJson(`tcc:${user}:scanRuns`))||[];return rows.slice(0,Math.max(1,Math.min(100,Number(limit)||20)))}
