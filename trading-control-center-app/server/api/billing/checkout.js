import {requireAccount} from '../_lib/access.js';
import {createCheckout} from '../_lib/billing.js';
import {rateLimit,applyRateLimitError} from '../_lib/rate-limit.js';
export default async function handler(req,res){if(req.method!=='POST')return res.status(405).json({error:'POST only'});try{const a=await requireAccount(req);await rateLimit(req,{label:'billing-checkout',limit:12,windowMs:60*60*1000});const out=await createCheckout(a,req.body?.plan);return res.status(201).json({ok:true,...out})}catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}}
