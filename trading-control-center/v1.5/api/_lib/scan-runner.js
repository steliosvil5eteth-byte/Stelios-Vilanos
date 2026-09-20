import {getJson,setJson,appendAudit} from './store.js';
import {fetchMarketMany,marketDataConfig} from './market-data.js';
import {updateForwardLedger} from './signal-ledger.js';
import {evaluateSeries} from './scanner.js';
import {strategySnapshot} from './model.js';
import {marketFreshness} from './freshness.js';

function symbolsFrom(value,maxSymbols=5){
  const arr=Array.isArray(value)?value:String(value||'').split(',');
  return [...new Set(arr.map(x=>String(x).trim().toUpperCase()).filter(x=>/^[A-Z0-9.\-]{1,15}$/.test(x)))].slice(0,Math.max(1,Math.min(25,Number(maxSymbols)||5)));
}

export async function runServerScan(user,{symbols=null,source='manual',maxSymbols=5}={}){
  if(!user)throw new Error('user required');
  const state=(await getJson(`tcc:${user}:state`))||{};const settings=state.settings||{};
  const configured=symbolsFrom(symbols?.length?symbols:(state.scanConfig?.symbols||process.env.SCAN_SYMBOLS||''),maxSymbols);
  if(!configured.length)throw new Error('No server scan symbols configured');
  const startedAt=new Date().toISOString();const fetched=await fetchMarketMany(configured);
  const evaluations=[];
  for(const item of fetched){
    if(item.error){evaluations.push({symbol:item.symbol,accepted:false,reasons:[`DATA_ERROR:${item.error}`],bars:0});continue}
    evaluations.push(evaluateSeries(item.symbol,item.series,settings));
  }
  evaluations.sort((a,b)=>Number(b.accepted)-Number(a.accepted)||(b.setup?.score||0)-(a.setup?.score||0));
  const current=strategySnapshot(settings,state.strategy?.name||'Current strategy');
  const providers=[...new Set(fetched.filter(x=>!x.error).map(x=>x.provider).filter(Boolean))];
  const ledger=await updateForwardLedger(user,{fetched,evaluations,strategy:current,settings});
  const run={id:`SCAN-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,source,provider:providers.length===1?providers[0]:'mixed',providers,marketDataConfig:marketDataConfig(),startedAt,completedAt:new Date().toISOString(),strategyId:current.id,symbols:configured,evaluations,accepted:evaluations.filter(x=>x.accepted).length,rejected:evaluations.filter(x=>!x.accepted).length,forwardLedger:{changed:ledger.changed,open:ledger.open,closed:ledger.closed}};
  const key=`tcc:${user}:scanRuns`;const rows=(await getJson(key))||[];rows.unshift(run);await setJson(key,rows.slice(0,100));
  await appendAudit(user,{ts:new Date().toISOString(),type:'SERVER_SCAN',detail:`${source} symbols=${configured.length} accepted=${run.accepted} rejected=${run.rejected} strategy=${current.id}`});
  return run;
}

export async function getScanRuns(user,limit=20){const rows=(await getJson(`tcc:${user}:scanRuns`))||[];return rows.slice(0,Math.max(1,Math.min(100,Number(limit)||20)))}
