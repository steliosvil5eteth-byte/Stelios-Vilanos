function num(v,d=0){const n=Number(v);return Number.isFinite(n)?n:d}
function cleanSymbol(v){const s=String(v||'').trim().toUpperCase();return /^[A-Z0-9.\/:-]{1,24}$/.test(s)?s:''}
function assetType(v,symbol){const x=String(v||'').toLowerCase();if(['stock','etf','crypto','cash','other'].includes(x))return x;if(String(symbol).includes('/'))return 'crypto';return 'stock'}
export function normalizeHoldings(input,max=100){
  if(!Array.isArray(input))return [];
  const out=[];
  for(const raw of input){
    const symbol=cleanSymbol(raw?.symbol);if(!symbol)continue;
    const quantity=Math.max(0,num(raw?.quantity)),avgCost=Math.max(0,num(raw?.avgCost)),currentPrice=Math.max(0,num(raw?.currentPrice));
    if(quantity<=0)continue;
    out.push({symbol,quantity,avgCost,currentPrice:currentPrice||null,assetType:assetType(raw?.assetType,symbol),updatedAt:new Date().toISOString()});
  }
  const map=new Map();for(const h of out){const k=h.symbol;const old=map.get(k);if(!old)map.set(k,h);else{const q=old.quantity+h.quantity,weighted=q?((old.avgCost*old.quantity)+(h.avgCost*h.quantity))/q:0;map.set(k,{...h,quantity:q,avgCost:weighted,currentPrice:h.currentPrice||old.currentPrice})}}
  return [...map.values()].slice(0,Math.max(1,Math.min(500,Number(max)||100)));
}
export function holdingValue(h){const px=num(h.currentPrice)||num(h.avgCost);return Math.max(0,px*num(h.quantity))}
export function holdingsSummary(rows=[]){
  const holdings=Array.isArray(rows)?rows:[],total=holdings.reduce((a,h)=>a+holdingValue(h),0);
  const positions=holdings.map(h=>({...h,value:holdingValue(h),weightPct:total?holdingValue(h)/total*100:0})).sort((a,b)=>b.value-a.value);
  return {count:positions.length,totalReferenceValue:total,positions,largestPositionPct:positions[0]?.weightPct||0,concentrated:positions.some(x=>x.weightPct>25)};
}
export function signalPortfolioContext(setup,rows=[]){
  const symbol=String(setup?.ticker||setup?.symbol||'').toUpperCase(),summary=holdingsSummary(rows),same=summary.positions.find(x=>x.symbol===symbol)||null;
  return {symbol,hasExistingPosition:Boolean(same),existingValue:same?.value||0,existingWeightPct:same?.weightPct||0,portfolioPositions:summary.count,portfolioConcentrated:summary.concentrated,note:same?'Existing exposure detected; user should consider concentration before acting.':'No existing position detected in imported holdings.'};
}
