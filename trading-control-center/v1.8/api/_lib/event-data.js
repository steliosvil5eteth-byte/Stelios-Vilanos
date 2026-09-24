const ALPHA_BASE='https://www.alphavantage.co/query';
const SEC_TICKERS='https://www.sec.gov/files/company_tickers.json';
const SEC_SUBMISSIONS='https://data.sec.gov/submissions';
let secTickerCache=null,secTickerCacheAt=0;

function clamp(v,a,b){return Math.max(a,Math.min(b,v))}
function num(v,d=0){const n=Number(v);return Number.isFinite(n)?n:d}
function symbolOk(s){return /^[A-Z0-9.\-]{1,15}$/.test(String(s||''))}
function normalizedTicker(s){return String(s||'').toUpperCase().replace(/\./g,'-')}
function alphaTime(v){
  const s=String(v||'');const m=s.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})?/);
  if(!m)return null;const d=new Date(Date.UTC(Number(m[1]),Number(m[2])-1,Number(m[3]),Number(m[4]),Number(m[5]),Number(m[6]||0)));
  return Number.isNaN(d.getTime())?null:d;
}
function hoursOld(date,now=new Date()){if(!(date instanceof Date)||Number.isNaN(date.getTime()))return Infinity;return Math.max(0,(now-date)/3600000)}

export function parseAlphaNews(payload,symbol,{now=new Date(),lookbackHours=24}={}){
  const sym=normalizedTicker(symbol),feed=Array.isArray(payload?.feed)?payload.feed:[],rows=[];
  for(const article of feed){
    const published=alphaTime(article.time_published);if(!published)continue;
    const ageHours=hoursOld(published,now);if(ageHours>lookbackHours)continue;
    const ts=(Array.isArray(article.ticker_sentiment)?article.ticker_sentiment:[]).find(x=>normalizedTicker(x.ticker)===sym);
    if(!ts)continue;
    const relevance=clamp(num(ts.relevance_score),0,1),sentiment=clamp(num(ts.ticker_sentiment_score),-1,1);
    rows.push({title:String(article.title||'').slice(0,240),url:String(article.url||'').slice(0,1000),source:String(article.source||'').slice(0,120),publishedAt:published.toISOString(),ageHours,relevance,sentiment,label:String(ts.ticker_sentiment_label||'').slice(0,80)});
  }
  if(!rows.length)return {status:'NO_RECENT_NEWS',direction:'NEUTRAL',score:0,weightedSentiment:0,headlineCount:0,freshnessHours:null,articles:[]};
  let sw=0,ss=0;for(const r of rows){const recency=Math.max(.15,1-r.ageHours/Math.max(1,lookbackHours));const w=Math.max(.05,r.relevance)*recency;sw+=w;ss+=r.sentiment*w}
  const weightedSentiment=sw?ss/sw:0,abs=Math.abs(weightedSentiment),sources=new Set(rows.map(x=>x.source).filter(Boolean)).size,freshnessHours=Math.min(...rows.map(x=>x.ageHours));
  const recencyBonus=clamp(15*(1-freshnessHours/Math.max(1,lookbackHours)),0,15),breadthBonus=clamp(sources*4,0,20);
  const score=clamp(55+abs*85+recencyBonus+breadthBonus,0,100);
  const direction=weightedSentiment>.04?'LONG':weightedSentiment<-.04?'SHORT':'NEUTRAL';
  return {status:'OK',direction,score,weightedSentiment,headlineCount:rows.length,freshnessHours,articles:rows.sort((a,b)=>a.ageHours-b.ageHours).slice(0,8)};
}

async function fetchAlphaNews(symbol,{apiKey=process.env.ALPHAVANTAGE_API_KEY,lookbackHours=24,now=new Date()}={}){
  if(!apiKey)throw new Error('ALPHAVANTAGE_API_KEY not configured');if(!symbolOk(symbol))throw new Error('Invalid symbol');
  const from=new Date(now.getTime()-lookbackHours*3600000);const z=n=>String(n).padStart(2,'0');
  const timeFrom=`${from.getUTCFullYear()}${z(from.getUTCMonth()+1)}${z(from.getUTCDate())}T${z(from.getUTCHours())}${z(from.getUTCMinutes())}`;
  const u=new URL(ALPHA_BASE);u.searchParams.set('function','NEWS_SENTIMENT');u.searchParams.set('tickers',symbol);u.searchParams.set('time_from',timeFrom);u.searchParams.set('sort','LATEST');u.searchParams.set('limit','50');u.searchParams.set('apikey',apiKey);
  const r=await fetch(u,{headers:{'User-Agent':'Trading-Signal-Center/1.0'}});if(!r.ok)throw new Error(`Alpha news HTTP ${r.status}`);
  const json=await r.json();if(json.Note)throw new Error('Alpha news API rate limit');if(json.Information)throw new Error(json.Information);if(json['Error Message'])throw new Error('Alpha news symbol error');
  return parseAlphaNews(json,symbol,{now,lookbackHours});
}

async function secTickerMap({userAgent=process.env.SEC_USER_AGENT,now=Date.now()}={}){
  if(!userAgent)throw new Error('SEC_USER_AGENT not configured');
  if(secTickerCache&&now-secTickerCacheAt<24*3600e3)return secTickerCache;
  const r=await fetch(SEC_TICKERS,{headers:{'User-Agent':userAgent,'Accept-Encoding':'gzip, deflate'}});
  if(!r.ok)throw new Error(`SEC ticker map HTTP ${r.status}`);const json=await r.json();const map=new Map();
  for(const row of Object.values(json||{})){const ticker=normalizedTicker(row?.ticker);const cik=Number(row?.cik_str);if(ticker&&Number.isFinite(cik))map.set(ticker,String(cik).padStart(10,'0'))}
  secTickerCache=map;secTickerCacheAt=now;return map;
}
function formWeight(form){const f=String(form||'').toUpperCase();if(f==='8-K'||f==='6-K')return 90;if(['10-Q','10-K','20-F','40-F'].includes(f))return 82;if(['S-1','S-3','424B5'].includes(f))return 75;return 60}
export function parseSecSubmissions(payload,{now=new Date(),lookbackHours=48}={}){
  const r=payload?.filings?.recent||{},forms=r.form||[],filingDates=r.filingDate||[],acceptance=r.acceptanceDateTime||[],accession=r.accessionNumber||[],primary=r.primaryDocument||[],items=r.items||[],rows=[];
  for(let i=0;i<forms.length;i++){
    const form=String(forms[i]||'');if(!['8-K','6-K','10-Q','10-K','20-F','40-F','S-1','S-3','424B5'].includes(form))continue;
    const d=acceptance[i]?new Date(acceptance[i]):new Date(`${filingDates[i]}T23:59:59Z`);if(Number.isNaN(d.getTime()))continue;
    const ageHours=hoursOld(d,now);if(ageHours>lookbackHours)continue;
    rows.push({form,filingDate:String(filingDates[i]||''),acceptedAt:d.toISOString(),ageHours,accessionNumber:String(accession[i]||''),primaryDocument:String(primary[i]||''),items:String(items[i]||''),score:formWeight(form)});
  }
  if(!rows.length)return {status:'NO_RECENT_FILINGS',score:0,freshnessHours:null,filings:[]};
  rows.sort((a,b)=>a.ageHours-b.ageHours);const freshnessHours=rows[0].ageHours,score=clamp(Math.max(...rows.map(x=>x.score))+Math.max(0,8-freshnessHours/6),0,100);
  return {status:'OK',score,freshnessHours,filings:rows.slice(0,8)};
}
async function fetchSecEvents(symbol,{userAgent=process.env.SEC_USER_AGENT,lookbackHours=48,now=new Date()}={}){
  const map=await secTickerMap({userAgent,now:now.getTime()}),cik=map.get(normalizedTicker(symbol));if(!cik)return {status:'NO_SEC_CIK',score:0,freshnessHours:null,filings:[]};
  const r=await fetch(`${SEC_SUBMISSIONS}/CIK${cik}.json`,{headers:{'User-Agent':userAgent,'Accept-Encoding':'gzip, deflate'}});
  if(!r.ok)throw new Error(`SEC submissions HTTP ${r.status}`);const json=await r.json();return {...parseSecSubmissions(json,{now,lookbackHours}),cik};
}

export function eventDataConfig(){
  return {alphaNewsConfigured:Boolean(process.env.ALPHAVANTAGE_API_KEY),secConfigured:Boolean(process.env.SEC_USER_AGENT),required:String(process.env.EVENT_CONFIRMATION_REQUIRED||'true').toLowerCase()!=='false',lookbackHours:Math.max(1,Math.min(72,num(process.env.EVENT_LOOKBACK_HOURS,24))),minEventScore:clamp(num(process.env.EVENT_MIN_SCORE,80),0,100)};
}

export async function fetchEventSignal(symbol,{now=new Date()}={}){
  const cfg=eventDataConfig(),errors=[];let alpha=null,sec=null;
  if(cfg.alphaNewsConfigured)try{alpha=await fetchAlphaNews(symbol,{lookbackHours:cfg.lookbackHours,now})}catch(e){errors.push(`alpha:${e.message||e}`)}
  if(cfg.secConfigured)try{sec=await fetchSecEvents(symbol,{lookbackHours:Math.max(48,cfg.lookbackHours),now})}catch(e){errors.push(`sec:${e.message||e}`)}
  const direction=alpha?.direction||'NEUTRAL';let score=alpha?.score||0;
  if(sec?.status==='OK'&&score>0)score=clamp(score+Math.min(5,sec.score/20),0,100);
  else if(sec?.status==='OK'&&score===0)score=Math.min(85,sec.score);
  const freshness=[alpha?.freshnessHours,sec?.freshnessHours].filter(Number.isFinite);
  return {symbol,configured:cfg.alphaNewsConfigured||cfg.secConfigured,required:cfg.required,minEventScore:cfg.minEventScore,status:errors.length&&!(alpha||sec)?'ERROR':'OK',direction,score,freshnessHours:freshness.length?Math.min(...freshness):null,headlineCount:alpha?.headlineCount||0,weightedSentiment:alpha?.weightedSentiment||0,articles:alpha?.articles||[],sec:sec||null,errors};
}


export function combineTechnicalAndEvent(setup,event,{required=true,minEventScore=80}={}){
  const reasons=[];if(!setup)return {accepted:false,signalScore:0,reasons:['NO_TECHNICAL_SETUP']};
  const technicalScore=num(setup.score),configured=Boolean(event?.configured),eventScore=num(event?.score),eventDirection=String(event?.direction||'NEUTRAL');
  const signalScore=configured?Math.min(100,technicalScore*.80+eventScore*.20):technicalScore;
  if(technicalScore<95)reasons.push(`LOW_TECHNICAL_SCORE:${technicalScore.toFixed(1)}<95`);
  if(required){
    if(!configured)reasons.push('EVENT_SOURCE_UNAVAILABLE');
    if(configured&&eventDirection!==String(setup.direction||''))reasons.push(`EVENT_DIRECTION_MISMATCH:${eventDirection}!=${setup.direction}`);
    if(configured&&eventScore<minEventScore)reasons.push(`LOW_EVENT_SCORE:${eventScore.toFixed(1)}<${minEventScore}`);
    if(configured&&signalScore<95)reasons.push(`LOW_COMBINED_SIGNAL_SCORE:${signalScore.toFixed(1)}<95`);
  }
  return {accepted:reasons.length===0,signalScore,reasons,eventScore,eventDirection};
}
