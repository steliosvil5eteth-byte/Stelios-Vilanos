import {getJson,setJson,persistentStoreConfigured} from './_lib/store.js';
import {requireAccount} from './_lib/access.js';
import {entitlements} from './_lib/plans.js';
export default async function handler(req,res){
 try{const account=await requireAccount(req),user=account.username,key=`tcc:${user}:alerts`;
  if(req.method==='GET'){const a=(await getJson(key))||{rules:{nearStopPct:1,nearTargetPct:1,dailyLossWarnPct:80,maxOpenWarnPct:100,signalEmailEnabled:false},events:[]};return res.status(200).json({...a,persistent:persistentStoreConfigured()})}
  if(req.method==='PUT'){const old=(await getJson(key))||{rules:{},events:[]};const r=req.body?.rules||{},e=entitlements(account.plan);if(r.signalEmailEnabled===true&&!e.signalEmail){const err=new Error(`${e.label} plan does not include signal email alerts`);err.status=403;err.code='PLAN_LIMIT';throw err}const clamp=(v,a,b,d)=>{const n=Number(v);return Number.isFinite(n)?Math.max(a,Math.min(b,n)):d};old.rules={nearStopPct:clamp(r.nearStopPct,0.1,20,old.rules.nearStopPct||1),nearTargetPct:clamp(r.nearTargetPct,0.1,20,old.rules.nearTargetPct||1),dailyLossWarnPct:clamp(r.dailyLossWarnPct,10,100,old.rules.dailyLossWarnPct||80),maxOpenWarnPct:clamp(r.maxOpenWarnPct,10,100,old.rules.maxOpenWarnPct||100),signalEmailEnabled:r.signalEmailEnabled===undefined?(old.rules.signalEmailEnabled===true):r.signalEmailEnabled===true};await setJson(key,old);return res.status(200).json({ok:true,rules:old.rules})}
  if(req.method==='DELETE'){const old=(await getJson(key))||{rules:{}};await setJson(key,{rules:old.rules||{},events:[],clearedAt:new Date().toISOString()});return res.status(200).json({ok:true})}
  return res.status(405).json({error:'GET, PUT or DELETE only'});
 }catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}
}
