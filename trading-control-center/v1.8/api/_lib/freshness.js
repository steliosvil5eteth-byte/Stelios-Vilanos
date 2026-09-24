function daysBetween(a,b){return Math.abs((b-a)/86400000)}
function minutesBetween(a,b){return Math.abs((b-a)/60000)}
export function marketFreshness(series,{maxAgeDays=Number(process.env.MARKET_DATA_MAX_AGE_DAYS||7),maxAgeMinutes=Number(process.env.INTRADAY_MAX_AGE_MINUTES||30),now=new Date()}={}){
  const last=Array.isArray(series)?series.at(-1):null;if(!last?.date)return {ok:false,ageDays:null,ageMinutes:null,lastDate:null,reason:'NO_LAST_BAR'};
  const raw=String(last.date),intraday=/T\d{2}:\d{2}/.test(raw);
  const d=intraday?new Date(raw):new Date(`${raw.slice(0,10)}T23:59:59Z`);
  if(Number.isNaN(d.getTime()))return {ok:false,ageDays:null,ageMinutes:null,lastDate:raw,reason:'INVALID_LAST_BAR_DATE'};
  if(intraday){const ageMinutes=minutesBetween(d,now);return {ok:ageMinutes<=maxAgeMinutes,mode:'intraday',ageMinutes,lastDate:raw,maxAgeMinutes,reason:ageMinutes<=maxAgeMinutes?'FRESH':`STALE>${maxAgeMinutes}MIN`}}
  const ageDays=daysBetween(d,now);return {ok:ageDays<=maxAgeDays,mode:'daily',ageDays,lastDate:raw,maxAgeDays,reason:ageDays<=maxAgeDays?'FRESH':`STALE>${maxAgeDays}D`}
}
