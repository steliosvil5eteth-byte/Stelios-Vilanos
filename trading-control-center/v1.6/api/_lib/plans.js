export const PLANS={
  free:{id:'free',label:'Free',monthlyPriceEur:0,maxWatchlist:2,maxStrategies:3,scheduledScans:false,brokerPaper:false,exports:false,maxScanHistory:20,maxJournalTrades:250,monthlyMarketSymbols:100,monthlyManualScans:50,monthlyPaperOrders:50},
  pro:{id:'pro',label:'Pro',monthlyPriceEur:19.90,maxWatchlist:5,maxStrategies:25,scheduledScans:true,brokerPaper:true,exports:true,maxScanHistory:100,maxJournalTrades:1000,monthlyMarketSymbols:2500,monthlyManualScans:1000,monthlyPaperOrders:1000},
  premium:{id:'premium',label:'Premium',monthlyPriceEur:39.90,maxWatchlist:10,maxStrategies:100,scheduledScans:true,brokerPaper:true,exports:true,maxScanHistory:250,maxJournalTrades:2000,monthlyMarketSymbols:10000,monthlyManualScans:5000,monthlyPaperOrders:5000}
};
export function normalizePlan(plan){const p=String(plan||'free').toLowerCase();return PLANS[p]?p:'free'}
export function entitlements(plan){return PLANS[normalizePlan(plan)]}
export function requireFeature(account,feature){const e=entitlements(account?.plan);if(!e[feature]){const err=new Error(`${e.label} plan does not include ${feature}`);err.status=403;err.code='PLAN_LIMIT';throw err}return e}
