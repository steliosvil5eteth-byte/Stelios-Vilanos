import {getJson,setJson,appendAudit} from './store.js';

function n(v,d=0){const x=Number(v);return Number.isFinite(x)?x:d}
const keyFor=u=>`tcc:${u}:signals`;
function costsR(signal,exit,settings){const slip=n(settings.slippageBps)/10000,comm=n(settings.commissionBps)/10000,dir=String(signal.direction||'LONG').toUpperCase();const entry=dir==='SHORT'?n(signal.entry)*(1-slip):n(signal.entry)*(1+slip),actualExit=dir==='SHORT'?n(exit)*(1+slip):n(exit)*(1-slip),fees=(entry+actualExit)*comm,risk=Math.max(.0001,Math.abs(entry-n(signal.stop))),pnl=dir==='SHORT'?(entry-actualExit)-fees:(actualExit-entry)-fees;return pnl/risk}
export async function getSignals(user,limit=100){const rows=(await getJson(keyFor(user)))||[];return rows.slice(0,Math.max(1,Math.min(1000,Number(limit)||100)))}
export async function updateForwardLedger(user,{fetched=[],evaluations=[],strategy,settings={}}={}){
  const rows=(await getJson(keyFor(user)))||[],bySymbol=new Map(fetched.filter(x=>!x.error&&Array.isArray(x.series)).map(x=>[x.symbol,x.series])),providerBySymbol=new Map(fetched.filter(x=>!x.error).map(x=>[x.symbol,x.provider||'unknown']));
  let changed=0;
  for(const sig of rows.filter(x=>x.status==='OPEN')){
    const series=bySymbol.get(sig.symbol);if(!series)continue;const future=series.filter(b=>String(b.date)>String(sig.asOf));if(!future.length)continue;
    const maxHold=Math.max(1,n(sig.maxHold,settings.maxHold||20));let exit=null,reason=null,exitDate=null;
    for(const b of future.slice(0,maxHold)){
      const dir=String(sig.direction||'LONG').toUpperCase();
      if(dir==='SHORT'){
        if(n(b.high)>=n(sig.stop)){exit=n(sig.stop);reason='STOP';exitDate=b.date;break}
        if(n(b.low)<=n(sig.target)){exit=n(sig.target);reason='TARGET';exitDate=b.date;break}
      }else{
        if(n(b.low)<=n(sig.stop)){exit=n(sig.stop);reason='STOP';exitDate=b.date;break}
        if(n(b.high)>=n(sig.target)){exit=n(sig.target);reason='TARGET';exitDate=b.date;break}
      }
    }
    if(!reason&&future.length>=maxHold){const b=future[maxHold-1];exit=n(b.close);reason='TIME';exitDate=b.date}
    if(reason){sig.status='CLOSED';sig.exit=exit;sig.reason=reason;sig.closedAt=exitDate;sig.rMultiple=costsR(sig,exit,settings);sig.updatedAt=new Date().toISOString();changed++}
  }
  for(const ev of evaluations.filter(x=>x.accepted&&x.setup)){
    const id=`${strategy.id}:${ev.symbol}:${ev.setup.asOf}:${ev.setup.direction||'LONG'}`;if(rows.some(x=>x.id===id))continue;
    rows.unshift({id,symbol:ev.symbol,strategyId:strategy.id,strategyName:strategy.name,asOf:ev.setup.asOf,createdAt:new Date().toISOString(),status:'OPEN',direction:String(ev.setup.direction||'LONG'),entry:n(ev.setup.entry),stop:n(ev.setup.stop),target:n(ev.setup.target),score:n(ev.setup.score),signalScore:n(ev.signalScore,ev.setup.score),eventScore:n(ev.event?.score),eventDirection:String(ev.event?.direction||'NEUTRAL'),headline:String(ev.event?.articles?.[0]?.title||'').slice(0,240),portfolioContext:ev.portfolioContext||null,rr:n(ev.setup.rr),stopLossPct:n(ev.setup.stopLossPct,5),targetPct:n(ev.setup.targetPct),oos:ev.oos||null,maxHold:Math.max(1,n(settings.maxHold,20)),provider:providerBySymbol.get(ev.symbol)||'unknown',updatedAt:new Date().toISOString()});changed++;
  }
  rows.sort((a,b)=>String(b.createdAt).localeCompare(String(a.createdAt)));await setJson(keyFor(user),rows.slice(0,1000));
  if(changed)await appendAudit(user,{ts:new Date().toISOString(),type:'FORWARD_LEDGER_UPDATE',detail:`signals=${rows.length} changed=${changed}`});
  return {signals:rows.slice(0,1000),changed,open:rows.filter(x=>x.status==='OPEN').length,closed:rows.filter(x=>x.status==='CLOSED').length};
}
export function signalMetrics(rows=[]){
  const closed=rows.filter(x=>x.status==='CLOSED'&&Number.isFinite(Number(x.rMultiple))),wins=closed.filter(x=>x.rMultiple>0),sum=closed.reduce((a,x)=>a+n(x.rMultiple),0),gp=wins.reduce((a,x)=>a+n(x.rMultiple),0),gl=Math.abs(closed.filter(x=>x.rMultiple<=0).reduce((a,x)=>a+n(x.rMultiple),0));
  const buckets=[{label:'95–96.9',min:95,max:97},{label:'97–98.9',min:97,max:99},{label:'99–100',min:99,max:101}].map(b=>{
    const xs=closed.filter(x=>n(x.signalScore,x.score)>=b.min&&n(x.signalScore,x.score)<b.max),target=xs.filter(x=>x.reason==='TARGET').length,stop=xs.filter(x=>x.reason==='STOP').length,w=xs.filter(x=>n(x.rMultiple)>0).length;
    return {label:b.label,n:xs.length,wins:w,winRate:xs.length?w/xs.length*100:null,targetRate:xs.length?target/xs.length*100:null,stopRate:xs.length?stop/xs.length*100:null,avgR:xs.length?xs.reduce((a,x)=>a+n(x.rMultiple),0)/xs.length:null};
  });
  return {n:closed.length,wins:wins.length,winRate:closed.length?wins.length/closed.length*100:null,avgR:closed.length?sum/closed.length:null,profitFactor:gl?gp/gl:(gp?999:0),targets:closed.filter(x=>x.reason==='TARGET').length,stops:closed.filter(x=>x.reason==='STOP').length,timeExits:closed.filter(x=>x.reason==='TIME').length,buckets,calibrationNote:'Model score is a ranking score, not a probability. Empirical hit rates are measured separately.'};
}
