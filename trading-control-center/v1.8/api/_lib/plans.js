export const PLANS={
  free:{id:'free',label:'Demo',monthlyPriceEur:0,maxWatchlist:2,maxHoldings:5,maxStrategies:3,scheduledScans:false,brokerPaper:true,exports:false,maxScanHistory:20,maxJournalTrades:250,monthlyMarketSymbols:100,monthlyManualScans:50,monthlyPaperOrders:50},
  pro:{id:'pro',label:'Starter',monthlyPriceEur:10.01,maxWatchlist:10,maxHoldings:25,maxStrategies:25,scheduledScans:true,brokerPaper:true,exports:false,maxScanHistory:100,maxJournalTrades:1000,monthlyMarketSymbols:2500,monthlyManualScans:1000,monthlyPaperOrders:1000},
  premium:{id:'premium',label:'Pro',monthlyPriceEur:30,maxWatchlist:25,maxHoldings:100,maxStrategies:100,scheduledScans:true,brokerPaper:true,exports:true,maxScanHistory:250,maxJournalTrades:2000,monthlyMarketSymbols:10000,monthlyManualScans:5000,monthlyPaperOrders:5000}
};
export function normalizePlan(plan){const p=String(plan||'free').toLowerCase();return PLANS[p]?p:'free'}
export function entitlements(plan){return PLANS[normalizePlan(plan)]}
export function requireFeature(account,feature){const e=entitlements(account?.plan);if(!e[feature]){const err=new Error(`${e.label} plan does not include ${feature}`);err.status=403;err.code='PLAN_LIMIT';throw err}return e}
