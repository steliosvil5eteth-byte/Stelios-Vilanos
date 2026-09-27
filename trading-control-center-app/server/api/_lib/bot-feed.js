// Public data only. No exchange credentials and no order endpoints.
let newsCache;
async function json(url,fetcher){const r=await fetcher(url,{signal:AbortSignal.timeout(10000)});if(!r.ok)throw new Error(`DATA_HTTP_${r.status}`);return r.json();}
export async function fetchBotSnapshot({fetcher=fetch,now=Date.now()}={}){
  const root='https://www.okx.com/api/v5/market/';
  const [ticker,bars]=await Promise.all([json(root+'ticker?instId=BTC-EUR',fetcher),json(root+'candles?instId=BTC-EUR&bar=1m&limit=100',fetcher).catch(()=>({code:'ERROR',data:[]}))]);
  if(ticker.code!=='0'||!ticker.data?.[0])throw new Error('MARKET_DATA_UNAVAILABLE');
  const t=ticker.data[0];if(t.instId!=='BTC-EUR')throw new Error('WRONG_INSTRUMENT');
  const candles=(bars.code==='0'&&Array.isArray(bars.data)?bars.data:[]).filter(c=>c[8]==='1').map(c=>({ts:Number(c[0]),close:Number(c[4])})).sort((a,b)=>a.ts-b.ts);
  let news=newsCache;
  if(!news||now-news.fetchedAt>=5*60000){
    try{
      const data=await json('https://api.gdeltproject.org/api/v2/doc/doc?query=bitcoin%20sourcelang%3Aenglish&mode=artlist&format=json&maxrecords=20&timespan=1h&sort=datedesc',fetcher);
      if(!Array.isArray(data.articles))throw new Error('NEWS_SCHEMA');
      const articles=data.articles.filter(a=>typeof a.title==='string'&&/^https?:\/\//.test(a.url||'')).map(a=>({title:a.title.slice(0,300),url:a.url,seenAt:a.seendate}));
      news={status:'OK',fetchedAt:now,articles,negative:articles.some(a=>/\b(hack|hacked|fraud|exploit|bankrupt|ban|banned)\b/i.test(a.title)),note:'Headline filter only; discovery time is not publication time.'};newsCache=news;
    }catch{news={status:'UNAVAILABLE',fetchedAt:now,articles:[]};}
  }
  return {quote:{symbol:t.instId,bid:Number(t.bidPx),ask:Number(t.askPx),ts:Number(t.ts)},candles,news};
}
