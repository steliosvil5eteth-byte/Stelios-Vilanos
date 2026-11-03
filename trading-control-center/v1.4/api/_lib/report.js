import {portfolioMetrics,strategyLifecycle} from './portfolio.js';
function n(v){const x=Number(v);return Number.isFinite(x)?x:0}
function isClosed(t){return Boolean(t?.closedAt)&&String(t?.status||'').toUpperCase()!=='OPEN'}
function pnl(t){return Number.isFinite(Number(t?.netPnl))?n(t.netPnl):(n(t.current)-n(t.entry))*n(t.qty)-Math.abs(n(t.exitCommission))}
export function performanceReport({settings={},trades=[]}={}){
 const p=portfolioMetrics({settings,trades});const closed=trades.filter(isClosed).slice().sort((a,b)=>String(a.closedAt).localeCompare(String(b.closedAt)));
 const monthly={};for(const t of closed){const k=String(t.closedAt).slice(0,7)||'unknown';monthly[k]=(monthly[k]||0)+pnl(t)}
 const groups={};for(const t of trades){const id=t.strategyId||'LEGACY';groups[id]??={strategyId:id,name:t.strategyName||'Legacy / unversioned',rows:[]};groups[id].rows.push(t)}
 const strategies=Object.values(groups).map(g=>({...g,lifecycle:strategyLifecycle(g.rows)})).map(g=>({strategyId:g.strategyId,name:g.name,...g.lifecycle})).sort((a,b)=>b.n-a.n);
 const wins=closed.filter(t=>pnl(t)>0).length,losses=closed.filter(t=>pnl(t)<0).length,grossProfit=closed.filter(t=>pnl(t)>0).reduce((a,t)=>a+pnl(t),0),grossLoss=Math.abs(closed.filter(t=>pnl(t)<0).reduce((a,t)=>a+pnl(t),0));
 return {generatedAt:new Date().toISOString(),summary:{closedTrades:closed.length,wins,losses,winRate:closed.length?wins/closed.length*100:null,netPnl:p.realizedPnl,grossProfit,grossLoss,profitFactor:grossLoss?grossProfit/grossLoss:(grossProfit?999:0),maxDrawdown:p.maxDrawdown,maxDrawdownPct:p.maxDrawdownPct,equity:p.equity},monthly:Object.entries(monthly).sort().map(([month,netPnl])=>({month,netPnl})),strategies,equityCurve:p.equityCurve.slice(-500)};
}
