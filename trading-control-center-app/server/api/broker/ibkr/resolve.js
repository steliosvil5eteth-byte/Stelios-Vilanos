import {requireAccount} from '../../_lib/access.js';
import {requireFeature} from '../../_lib/plans.js';
import {appendAudit} from '../../_lib/store.js';
import {ibkrFetch,requirePaperSession} from './_client.js';
export default async function handler(req,res){
  if(req.method!=='GET') return res.status(405).json({error:'GET only'});
  let account;try{account=await requireAccount(req);requireFeature(account,'brokerPaper')}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})} const user=account.username;
  const symbol=String(req.query?.symbol||'').trim().toUpperCase();
  if(!/^[A-Z0-9.\-]{1,15}$/.test(symbol)) return res.status(400).json({error:'Invalid symbol'});
  try{
    await requirePaperSession();
    const data=await ibkrFetch(`/iserver/secdef/search?symbol=${encodeURIComponent(symbol)}`);
    const rows=Array.isArray(data)?data:[];
    const exact=rows.filter(x=>String(x?.symbol||'').toUpperCase()===symbol);
    const stock=exact.find(x=>Array.isArray(x?.sections)&&x.sections.some(s=>String(s?.secType||'').toUpperCase()==='STK')) || exact[0] || rows[0];
    if(!stock?.conid) return res.status(404).json({error:'No IBKR contract found for symbol'});
    await appendAudit(user,{ts:new Date().toISOString(),type:'IBKR_RESOLVE',detail:`${symbol} -> ${stock.conid}`});
    return res.status(200).json({symbol,conid:Number(stock.conid),companyName:stock.companyName||'',description:stock.description||'',restricted:stock.restricted??null,candidates:rows.slice(0,8).map(x=>({symbol:x.symbol,conid:Number(x.conid),companyName:x.companyName||'',description:x.description||''}))});
  }catch(e){return res.status(e.status||502).json({error:e.message,data:e.data})}
}
