const ALPHA_BASE='https://www.alphavantage.co/query';
const TWELVE_BASE='https://api.twelvedata.com/time_series';
const symbolOk=s=>/^[A-Z0-9.\-]{1,15}$/.test(s);

export function parseDaily(payload){
  const ts=payload?.['Time Series (Daily)'];
  if(!ts)return null;
  return Object.entries(ts).map(([date,row])=>({date,open:Number(row['1. open']),high:Number(row['2. high']),low:Number(row['3. low']),close:Number(row['4. close']),volume:Number(row['5. volume'])})).filter(x=>[x.open,x.high,x.low,x.close,x.volume].every(Number.isFinite)).sort((a,b)=>a.date.localeCompare(b.date));
}
export function parseTwelveDaily(payload){
  if(!Array.isArray(payload?.values))return null;
  return payload.values.map(row=>({date:String(row.datetime||'').slice(0,10),open:Number(row.open),high:Number(row.high),low:Number(row.low),close:Number(row.close),volume:Number(row.volume||0)})).filter(x=>x.date&&[x.open,x.high,x.low,x.close].every(Number.isFinite)&&Number.isFinite(x.volume)).sort((a,b)=>a.date.localeCompare(b.date));
}
export async function fetchAlphaDaily(symbol,{apiKey=process.env.ALPHAVANTAGE_API_KEY,outputsize=process.env.ALPHAVANTAGE_OUTPUTSIZE||'compact'}={}){
  if(!apiKey)throw new Error('ALPHAVANTAGE_API_KEY is not configured on the server');if(!symbolOk(symbol))throw new Error('Invalid symbol format');const size=String(outputsize).toLowerCase()==='full'?'full':'compact';
  const u=new URL(ALPHA_BASE);u.searchParams.set('function','TIME_SERIES_DAILY');u.searchParams.set('symbol',symbol);u.searchParams.set('outputsize',size);u.searchParams.set('apikey',apiKey);
  const r=await fetch(u,{headers:{'User-Agent':'Trading-Control-Center/1.4'}});if(!r.ok)throw new Error(`HTTP ${r.status}`);const json=await r.json();if(json.Note)throw new Error('API rate limit');if(json.Information)throw new Error(json.Information);if(json['Error Message'])throw new Error('Unknown/unsupported symbol');const series=parseDaily(json);if(!series?.length)throw new Error('No daily series returned');return {symbol,series,meta:json['Meta Data']||{},provider:'alphavantage',outputsize:size};
}
export async function fetchTwelveDaily(symbol,{apiKey=process.env.TWELVE_DATA_API_KEY,outputsize=process.env.TWELVE_DATA_OUTPUTSIZE||'1000'}={}){
  if(!apiKey)throw new Error('TWELVE_DATA_API_KEY is not configured on the server');if(!symbolOk(symbol))throw new Error('Invalid symbol format');const size=Math.max(60,Math.min(5000,Number(outputsize)||1000));
  const u=new URL(TWELVE_BASE);u.searchParams.set('symbol',symbol);u.searchParams.set('interval','1day');u.searchParams.set('outputsize',String(size));u.searchParams.set('order','asc');u.searchParams.set('format','JSON');u.searchParams.set('apikey',apiKey);
  const r=await fetch(u,{headers:{'User-Agent':'Trading-Control-Center/1.4'}});if(!r.ok)throw new Error(`HTTP ${r.status}`);const json=await r.json();if(json.status==='error'||json.code)throw new Error(json.message||`Twelve Data error ${json.code}`);const series=parseTwelveDaily(json);if(!series?.length)throw new Error('No daily series returned');return {symbol,series,meta:json.meta||{},provider:'twelvedata',outputsize:size};
}
function providerOrder(){
  const mode=String(process.env.MARKET_DATA_PROVIDER||'auto').toLowerCase();const failover=String(process.env.MARKET_DATA_FAILOVER||'true').toLowerCase()!=='false';
  if(mode==='alphavantage')return failover?['alphavantage','twelvedata']:['alphavantage'];if(mode==='twelvedata')return failover?['twelvedata','alphavantage']:['twelvedata'];
  const preferred=[];if(process.env.TWELVE_DATA_API_KEY)preferred.push('twelvedata');if(process.env.ALPHAVANTAGE_API_KEY)preferred.push('alphavantage');return preferred.length?preferred:['alphavantage','twelvedata'];
}
export function marketDataConfig(){return {mode:String(process.env.MARKET_DATA_PROVIDER||'auto').toLowerCase(),failover:String(process.env.MARKET_DATA_FAILOVER||'true').toLowerCase()!=='false',alphaConfigured:Boolean(process.env.ALPHAVANTAGE_API_KEY),twelveConfigured:Boolean(process.env.TWELVE_DATA_API_KEY),order:providerOrder()}}
export async function fetchMarketDaily(symbol,opts={}){
  const errors=[];for(const provider of providerOrder())try{return provider==='twelvedata'?await fetchTwelveDaily(symbol,opts):await fetchAlphaDaily(symbol,opts)}catch(e){errors.push(`${provider}:${e.message||e}`)}
  throw new Error(`All market-data providers failed: ${errors.join(' | ')}`);
}
export async function fetchMarketMany(symbols,opts={}){const out=[];for(const symbol of symbols){try{out.push(await fetchMarketDaily(symbol,opts))}catch(e){out.push({symbol,error:String(e.message||e)})}}return out}
export const fetchAlphaMany=fetchMarketMany;
