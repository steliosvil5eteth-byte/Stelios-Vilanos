import crypto from 'crypto';
import {databaseConfigured,db} from './db.js';
const buckets=globalThis.__TCC_RL__||(globalThis.__TCC_RL__=new Map());
function fingerprint(req,label='generic'){
  const raw=String(req.headers['x-forwarded-for']||req.headers['x-real-ip']||req.socket?.remoteAddress||'unknown').split(',')[0].trim();
  const salt=process.env.SESSION_SECRET||'tcc-local';
  return crypto.createHash('sha256').update(`${label}|${salt}|${raw}`).digest('hex').slice(0,32);
}
export async function rateLimit(req,{label='api',limit=60,windowMs=60_000}={}){
  const now=Date.now(),start=Math.floor(now/windowMs)*windowMs,key=`${label}:${fingerprint(req,label)}`;
  let count=1;
  if(databaseConfigured()){
    const sql=await db();
    const rows=await sql`
      insert into tcc_rate_limits (bucket_key,window_start,count,updated_at)
      values (${key},${start},1,now())
      on conflict (bucket_key) do update set
        window_start=case when tcc_rate_limits.window_start<${start} then ${start} else tcc_rate_limits.window_start end,
        count=case when tcc_rate_limits.window_start<${start} then 1 else tcc_rate_limits.count+1 end,
        updated_at=now()
      returning count`;
    count=Number(rows[0]?.count||1);
  }else{
    const cur=buckets.get(key); if(!cur||cur.start!==start){buckets.set(key,{start,count:1});count=1}else{cur.count++;count=cur.count}
  }
  const retryAfter=Math.max(1,Math.ceil((start+windowMs-now)/1000));
  if(count>limit){const e=new Error('Too many requests');e.status=429;e.code='RATE_LIMIT';e.retryAfter=retryAfter;throw e}
  return {count,limit,retryAfter};
}
export function applyRateLimitError(res,e){if(e?.status===429&&e.retryAfter)res.setHeader('Retry-After',String(e.retryAfter))}
