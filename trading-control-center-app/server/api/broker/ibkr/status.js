import {requireAccount} from '../../_lib/access.js';
import {requireFeature} from '../../_lib/plans.js';
import {appendAudit} from '../../_lib/store.js';
import {brokerConfig,requirePaperSession} from './_client.js';
export default async function handler(req,res){
  if(req.method!=='GET') return res.status(405).json({error:'GET only'});
  let account;try{account=await requireAccount(req);requireFeature(account,'brokerPaper')}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})} const user=account.username;
  const cfg=brokerConfig();
  if(!cfg.configured) return res.status(200).json({configured:false,paperExecutionEnabled:false});
  try{
    const {data,account}=await requirePaperSession();
    await appendAudit(user,{ts:new Date().toISOString(),type:'IBKR_STATUS',detail:'paper session verified'});
    return res.status(200).json({configured:true,connected:true,isPaper:true,paperExecutionEnabled:cfg.paperExecutionEnabled,accountMasked:account.length>4?`${account.slice(0,2)}••••${account.slice(-2)}`:'••••',selectedAccount:data?.selectedAccount||null,accounts:Array.isArray(data?.accounts)?data.accounts.length:0});
  }catch(e){
    return res.status(e.status||502).json({configured:true,connected:false,isPaper:false,paperExecutionEnabled:cfg.paperExecutionEnabled,error:e.message});
  }
}
