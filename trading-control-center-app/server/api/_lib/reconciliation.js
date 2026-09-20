function normSymbol(s){return String(s||'').trim().toUpperCase()}
export function reconcilePaperState({localTrades=[],positions=[],openOrders=[],brokerTrades=[]}={}){
  const localOpen=localTrades.filter(t=>String(t.status||'').toUpperCase()==='OPEN');
  const brokerLong=positions.filter(p=>Number(p.position)>0);
  const orders=openOrders.filter(o=>!['FILLED','CANCELLED','CANCELED','INACTIVE'].includes(String(o.status||'').toUpperCase()));
  const byConid=new Map(brokerLong.map(p=>[Number(p.conid),p]));
  const bySymbol=new Map(brokerLong.map(p=>[normSymbol(p.symbol),p]));
  const orderConids=new Set(orders.map(o=>Number(o.conid)).filter(Boolean));
  const orderSymbols=new Set(orders.map(o=>normSymbol(o.symbol)).filter(Boolean));
  const issues=[];
  for(const t of localOpen){
    const match=(t.conid&&byConid.get(Number(t.conid)))||bySymbol.get(normSymbol(t.ticker));
    const protectedOrder=(t.conid&&orderConids.has(Number(t.conid)))||orderSymbols.has(normSymbol(t.ticker));
    if(!match)issues.push({severity:'critical',type:'LOCAL_OPEN_MISSING_BROKER_POSITION',tradeId:t.id,ticker:t.ticker});
    if(match&&!protectedOrder)issues.push({severity:'warning',type:'BROKER_POSITION_WITHOUT_VISIBLE_OPEN_ORDER',tradeId:t.id,ticker:t.ticker,conid:match.conid});
  }
  for(const p of brokerLong){
    const local=localOpen.find(t=>(t.conid&&Number(t.conid)===Number(p.conid))||normSymbol(t.ticker)===normSymbol(p.symbol));
    if(!local)issues.push({severity:'critical',type:'UNEXPECTED_BROKER_POSITION',ticker:p.symbol,conid:p.conid,position:p.position});
  }
  const duplicateExecIds=brokerTrades.map(x=>String(x.executionId||'')).filter(Boolean).filter((x,i,a)=>a.indexOf(x)!==i);
  if(duplicateExecIds.length)issues.push({severity:'warning',type:'DUPLICATE_EXECUTION_IDS',count:new Set(duplicateExecIds).size});
  return {ok:issues.every(x=>x.severity!=='critical'),critical:issues.filter(x=>x.severity==='critical').length,warnings:issues.filter(x=>x.severity==='warning').length,issues,localOpen:localOpen.length,brokerPositions:brokerLong.length,openOrders:orders.length,brokerTrades:brokerTrades.length,checkedAt:new Date().toISOString()};
}
