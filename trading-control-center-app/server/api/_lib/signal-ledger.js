import {getJson,setJson,appendAudit} from './store.js';

function n(v,d=0){const x=Number(v);return Number.isFinite(x)?x:d}
const keyFor=u=>`tcc:${u}:signals`;
function costsR(signal,exit,settings){const slip=n(settings.slippageBps)/10000,comm=n(settings.commissionBps)/10000;const entry=n(signal.entry)*(1+slip),actualExit=n(exit)*(1-slip),fees=(entry+actualExit)*comm,risk=Math.max(.0001,entry-n(signal.stop));return ((actualExit-entry)-fees)/risk}
export async function getSignals(user,limit=100){const rows=(await getJson(keyFor(user)))||[];return rows.slice(0,Math.max(1,Math.min(1000,Number(limit)||100)))}
export async function updateForwardLedger(user,{fetched=[],evaluations=[],strategy,settings={}}={}){
  const rows=(await getJson(keyFor(user)))||[],bySymbol=new Map(fetched.filter(x=>!x.error&&Array.isArray(x.series)).map(x=>[x.symbol,x.series])),providerBySymbol=new Map(fetched.filter(x=>!x.error).map(x=>[x.symbol,x.provider||'unknown']));
  let changed=0;
  for(const sig of rows.filter(x=>x.status==='OPEN')){
    const series=bySymbol.get(sig.symbol);if(!series)continue;const future=series.filter(b=>String(b.date)>String(sig.asOf));if(!future.length)continue;
    const maxHold=Math.max(1,n(sig.maxHold,settings.maxHold||20));let exit=null,reason=null,exitDate=null;
    for(const b of future.slice(0,maxHold)){
      if(n(b.low)<=n(sig.stop)){exit=n(sig.stop);reason='STOP';exitDate=b.date;break}
      if(n(b.high)>=n(sig.target)){exit=n(sig.target);reason='TARGET';exitDate=b.date;break}
    }
    if(!reason&&future.length>=maxHold){const b=future[maxHold-1];exit=n(b.close);reason='TIME';exitDate=b.date}
    if(reason){sig.status='CLOSED';sig.exit=exit;sig.reason=reason;sig.closedAt=exitDate;sig.rMultiple=costsR(sig,exit,settings);sig.updatedAt=new Date().toISOString();changed++}
  }
  for(const ev of evaluations.filter(x=>x.accepted&&x.setup)){
    const id=`${strategy.id}:${ev.symbol}:${ev.setup.asOf}`;if(rows.some(x=>x.id===id))continue;
    rows.unshift({id,symbol:ev.symbol,strategyId:strategy.id,strategyName:strategy.name,asOf:ev.setup.asOf,createdAt:new Date().toISOString(),status:'OPEN',entry:n(ev.setup.entry),stop:n(ev.setup.stop),target:n(ev.setup.target),score:n(ev.setup.score),rr:n(ev.setup.rr),oos:ev.oos||null,maxHold:Math.max(1,n(settings.maxHold,20)),provider:providerBySymbol.get(ev.symbol)||'unknown',updatedAt:new Date().toISOString()});changed++;
  }
  rows.sort((a,b)=>String(b.createdAt).localeCompare(String(a.createdAt)));await setJson(keyFor(user),rows.slice(0,1000));
  if(changed)await appendAudit(user,{ts:new Date().toISOString(),type:'FORWARD_LEDGER_UPDATE',detail:`signals=${rows.length} changed=${changed}`});
  return {signals:rows.slice(0,1000),changed,open:rows.filter(x=>x.status==='OPEN').length,closed:rows.filter(x=>x.status==='CLOSED').length};
}
export function signalMetrics(rows=[]){const closed=rows.filter(x=>x.status==='CLOSED'&&Number.isFinite(Number(x.rMultiple)));const wins=closed.filter(x=>x.rMultiple>0),sum=closed.reduce((a,x)=>a+n(x.rMultiple),0),gp=wins.reduce((a,x)=>a+n(x.rMultiple),0),gl=Math.abs(closed.filter(x=>x.rMultiple<=0).reduce((a,x)=>a+n(x.rMultiple),0));return {n:closed.length,wins:wins.length,winRate:closed.length?wins.length/closed.length*100:null,avgR:closed.length?sum/closed.length:null,profitFactor:gl?gp/gl:(gp?999:0)}}
