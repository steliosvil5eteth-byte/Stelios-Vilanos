process.env.PAPER_EXECUTION_ENABLED='true';
process.env.SESSION_SECRET='v15-smoke-session-secret-123456789012345';
const {getSafetyState,updateSafetyState,requirePaperExecutionAllowed}=await import('../server/api/_lib/safety.js');
const {marketFreshness}=await import('../server/api/_lib/freshness.js');
const {reconcilePaperState}=await import('../server/api/_lib/reconciliation.js');
const {validateLongPaperOrder,normalizeSymbols}=await import('../server/api/_lib/schema.js');

let s=await getSafetyState();if(s.paperExecutionAllowed)throw Error('paper execution must default blocked');
await updateSafetyState('admin',{paperExecutionEnabled:true,emergencyStop:false,note:'smoke'});s=await getSafetyState();if(!s.paperExecutionAllowed)throw Error('two-key paper safety did not enable');await requirePaperExecutionAllowed();
await updateSafetyState('admin',{emergencyStop:true});let blocked=false;try{await requirePaperExecutionAllowed()}catch(e){blocked=e.code==='PAPER_EXECUTION_BLOCKED'}if(!blocked)throw Error('emergency stop did not block');
const fresh=marketFreshness([{date:'2026-09-20',close:1}],{now:new Date('2026-09-20T12:00:00Z'),maxAgeDays:7});if(!fresh.ok)throw Error('fresh market data rejected');
const stale=marketFreshness([{date:'2026-08-01',close:1}],{now:new Date('2026-09-20T12:00:00Z'),maxAgeDays:7});if(stale.ok)throw Error('stale market data accepted');
const o=validateLongPaperOrder({symbol:'aapl',qty:2,entry:100,stop:95,target:110});if(o.symbol!=='AAPL'||o.qty!==2)throw Error('order schema failed');
let bad=false;try{validateLongPaperOrder({symbol:'AAPL',qty:1,entry:100,stop:105,target:110})}catch(e){bad=e.code==='INVALID_ORDER'}if(!bad)throw Error('invalid long order passed');
if(normalizeSymbols('AAPL,MSFT,AAPL',5).length!==2)throw Error('symbol normalization failed');
const rec=reconcilePaperState({localTrades:[{id:'L1',ticker:'AAPL',conid:1,status:'OPEN'}],positions:[{conid:1,symbol:'AAPL',position:2}],openOrders:[{conid:1,symbol:'AAPL',status:'Submitted'}],brokerTrades:[]});if(!rec.ok||rec.critical!==0)throw Error('healthy reconciliation failed');
const orphan=reconcilePaperState({localTrades:[{id:'L2',ticker:'MSFT',conid:2,status:'OPEN'}],positions:[],openOrders:[],brokerTrades:[]});if(orphan.ok||orphan.critical<1)throw Error('orphan local trade not detected');
const unexpected=reconcilePaperState({localTrades:[],positions:[{conid:3,symbol:'NVDA',position:1}],openOrders:[],brokerTrades:[]});if(unexpected.ok||unexpected.critical<1)throw Error('unexpected broker position not detected');
console.log('v1.5 smoke: OK');
