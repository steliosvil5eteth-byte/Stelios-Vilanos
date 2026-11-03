import {appendAudit} from '../_lib/store.js';
import {requireAccount} from '../_lib/access.js';
import {requireFeature} from '../_lib/plans.js';
export default async function handler(req,res){
  if(req.method!=='POST')return res.status(405).json({error:'POST only'});
  try{const a=await requireAccount(req);requireFeature(a,'brokerPaper');const user=a.username;const base=(process.env.IBKR_BASE_URL||'').replace(/\/$/,'');const account=process.env.IBKR_ACCOUNT_ID||'';const token=process.env.IBKR_BEARER_TOKEN||'';
   if(!base||!account)return res.status(503).json({error:'IBKR What-If is not configured on the server'});const {conid,quantity,price,side='BUY',orderType='LMT',tif='DAY'}=req.body||{};if(!Number.isFinite(Number(conid))||Number(quantity)<=0||Number(price)<=0)return res.status(400).json({error:'conid, quantity and price are required'});const headers={'Content-Type':'application/json'};if(token)headers.Authorization=`Bearer ${token}`;const body={orders:[{conid:Number(conid),orderType,price:Number(price),side,tif,quantity:Number(quantity)}]};const r=await fetch(`${base}/iserver/account/${encodeURIComponent(account)}/orders/whatif`,{method:'POST',headers,body:JSON.stringify(body)});const text=await r.text();let data;try{data=JSON.parse(text)}catch{data={raw:text}};await appendAudit(user,{ts:new Date().toISOString(),type:'IBKR_WHATIF',detail:`conid=${conid} qty=${quantity} HTTP=${r.status}`});return res.status(r.ok?200:r.status).json({ok:r.ok,data})
  }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
