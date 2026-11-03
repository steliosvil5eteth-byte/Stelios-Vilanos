function cfg(){
  return {
    base:(process.env.IBKR_BASE_URL||'').replace(/\/$/,''),
    account:process.env.IBKR_ACCOUNT_ID||'',
    token:process.env.IBKR_BEARER_TOKEN||'',
    paperEnabled:String(process.env.IBKR_PAPER_EXECUTION_ENABLED||'').toLowerCase()==='true'
  };
}

export function brokerConfig(){
  const c=cfg();
  return {configured:Boolean(c.base&&c.account),account:c.account,paperExecutionEnabled:c.paperEnabled};
}

export async function ibkrFetch(path,{method='GET',body}={}){
  const c=cfg();
  if(!c.base||!c.account) throw Object.assign(new Error('IBKR is not configured on the server'),{status:503});
  const headers={'Content-Type':'application/json'};
  if(c.token) headers.Authorization=`Bearer ${c.token}`;
  const r=await fetch(`${c.base}${path}`,{method,headers,body:body===undefined?undefined:JSON.stringify(body)});
  const text=await r.text();
  let data; try{data=text?JSON.parse(text):null}catch{data={raw:text}}
  if(!r.ok){const e=new Error(data?.error||data?.message||`IBKR HTTP ${r.status}`);e.status=r.status;e.data=data;throw e}
  return data;
}

export async function requirePaperSession(){
  const c=cfg();
  if(!c.base||!c.account) throw Object.assign(new Error('IBKR is not configured on the server'),{status:503});
  const data=await ibkrFetch('/iserver/accounts');
  const accounts=Array.isArray(data?.accounts)?data.accounts:[];
  const isPaper=data?.isPaper===true;
  if(!isPaper) throw Object.assign(new Error('Safety gate: active IBKR session is not a paper-trading session'),{status:403,data});
  if(accounts.length&&!accounts.includes(c.account)) throw Object.assign(new Error('Configured IBKR account is not available in the active paper session'),{status:403,data});
  return {data,account:c.account};
}

export function requirePaperExecutionEnabled(){
  const c=cfg();
  if(!c.paperEnabled) throw Object.assign(new Error('IBKR paper execution is disabled on the server'),{status:403});
}

export function validBracket(o){
  return o && Number.isFinite(Number(o.conid)) && Number(o.conid)>0 && Number(o.quantity)>0 && Number(o.entry)>0 && Number(o.stop)>0 && Number(o.target)>0 && Number(o.stop)<Number(o.entry) && Number(o.target)>Number(o.entry);
}

export function bracketBody({conid,quantity,entry,stop,target,tif='DAY',outsideRTH=false,clientOrderId}){
  const c=cfg();
  const parent=clientOrderId||`TCC-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
  const q=Number(quantity), id=Number(conid);
  return {orders:[
    {acctId:c.account,conid:id,cOID:parent,orderType:'LMT',listingExchange:'SMART',outsideRTH:Boolean(outsideRTH),price:Number(entry),side:'BUY',tif,quantity:q},
    {acctId:c.account,conid:id,orderType:'LMT',listingExchange:'SMART',outsideRTH:Boolean(outsideRTH),price:Number(target),side:'SELL',tif:'GTC',quantity:q,parentId:parent},
    {acctId:c.account,conid:id,orderType:'STP',listingExchange:'SMART',outsideRTH:Boolean(outsideRTH),price:Number(stop),side:'SELL',tif:'GTC',quantity:q,parentId:parent}
  ]};
}

export async function marketDataPreflight(conid){
  const id=Number(conid);
  await ibkrFetch(`/iserver/marketdata/snapshot?conids=${encodeURIComponent(id)}&fields=31,55,84,86,6509`);
}

export function classifyOrderResponse(data){
  const arr=Array.isArray(data)?data:[data];
  const replies=arr.filter(x=>x&&x.id&&Array.isArray(x.message));
  const accepted=arr.filter(x=>x&&(x.order_id||x.orderId||x.order_status));
  const errors=arr.filter(x=>x&&x.error);
  return {requiresConfirmation:replies.length>0,replies,accepted,errors,raw:data};
}
