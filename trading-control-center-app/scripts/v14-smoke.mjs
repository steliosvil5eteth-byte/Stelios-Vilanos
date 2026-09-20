import {runIdempotent} from '../server/api/_lib/idempotency.js';
import {parseTwelveDaily,fetchMarketDaily,marketDataConfig} from '../server/api/_lib/market-data.js';
import {updateForwardLedger,getSignals,signalMetrics} from '../server/api/_lib/signal-ledger.js';

let calls=0;
let a=await runIdempotent({user:'v14',scope:'order',key:'IDEM-v14-123456',input:{symbol:'AAPL',qty:1},work:async()=>{calls++;return {ticket:'ONE'}}});
let b=await runIdempotent({user:'v14',scope:'order',key:'IDEM-v14-123456',input:{symbol:'AAPL',qty:1},work:async()=>{calls++;return {ticket:'TWO'}}});
if(a.replayed||!b.replayed||calls!==1||b.value.ticket!=='ONE')throw Error('idempotency replay failed');
let conflict=false;try{await runIdempotent({user:'v14',scope:'order',key:'IDEM-v14-123456',input:{symbol:'AAPL',qty:2},work:async()=>({})})}catch(e){conflict=e.code==='IDEMPOTENCY_CONFLICT'}if(!conflict)throw Error('idempotency fingerprint conflict not enforced');

const parsed=parseTwelveDaily({values:[{datetime:'2026-01-03',open:'10',high:'11',low:'9',close:'10.5',volume:'1000'},{datetime:'2026-01-02',open:'9',high:'10',low:'8',close:'9.5',volume:'900'}]});
if(parsed.length!==2||parsed[0].date!=='2026-01-02')throw Error('Twelve Data parser failed');
process.env.MARKET_DATA_PROVIDER='alphavantage';process.env.MARKET_DATA_FAILOVER='true';process.env.ALPHAVANTAGE_API_KEY='alpha-test';process.env.TWELVE_DATA_API_KEY='twelve-test';
const originalFetch=global.fetch;let reqs=[];global.fetch=async url=>{reqs.push(String(url));if(String(url).includes('alphavantage'))return {ok:true,json:async()=>({Note:'rate limit'})};return {ok:true,json:async()=>({meta:{symbol:'AAPL'},values:[{datetime:'2026-01-02',open:'9',high:'10',low:'8',close:'9.5',volume:'900'},{datetime:'2026-01-03',open:'10',high:'11',low:'9',close:'10.5',volume:'1000'}]})}};
const md=await fetchMarketDaily('AAPL');global.fetch=originalFetch;if(md.provider!=='twelvedata'||reqs.length!==2)throw Error('market-data failover failed');if(!marketDataConfig().failover)throw Error('market-data config failed');

const settings={maxHold:3,slippageBps:0,commissionBps:0};const strategy={id:'S-v14',name:'v14 test'};const ev=[{symbol:'AAA',accepted:true,setup:{asOf:'2026-01-01',entry:100,stop:95,target:110,score:80,rr:2},oos:{n:10,avgR:.2,profitFactor:1.4}}];
await updateForwardLedger('v14-ledger',{fetched:[{symbol:'AAA',provider:'test',series:[{date:'2026-01-01',open:100,high:101,low:99,close:100,volume:1}]}],evaluations:ev,strategy,settings});
await updateForwardLedger('v14-ledger',{fetched:[{symbol:'AAA',provider:'test',series:[{date:'2026-01-01',open:100,high:101,low:99,close:100,volume:1},{date:'2026-01-02',open:101,high:111,low:100,close:110,volume:1}]}],evaluations:ev,strategy,settings});
const signals=await getSignals('v14-ledger');if(signals.length!==1||signals[0].status!=='CLOSED'||signals[0].reason!=='TARGET'||Math.abs(signals[0].rMultiple-2)>1e-9)throw Error('forward ledger reconciliation failed');const sm=signalMetrics(signals);if(sm.n!==1||sm.wins!==1)throw Error('forward ledger metrics failed');
console.log('v1.4 smoke: OK');
