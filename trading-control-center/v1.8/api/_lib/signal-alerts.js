import {getJson,setJson} from './store.js';
import {getAccount} from './accounts.js';
import {sendEmail} from './email.js';

const keyFor=u=>`tcc:${u}:alerts`;
function signalKey(s){return `${s.symbol}:${s.asOf||''}:${s.direction||''}`}
export async function publishSignalAlerts(user,signals=[],runId=''){
  const accepted=(Array.isArray(signals)?signals:[]).filter(x=>x&&x.symbol&&x.status==='OPEN'),saved=(await getJson(keyFor(user)))||{rules:{},events:[]},events=Array.isArray(saved.events)?saved.events:[],seen=new Set(events.map(x=>x.dedupe)),created=[];
  for(const s of accepted){
    const dedupe=`SIGNAL:${signalKey(s)}`;if(seen.has(dedupe))continue;
    const row={id:`AL-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,type:'SIGNAL_95_PLUS',severity:'info',dedupe,createdAt:new Date().toISOString(),acknowledged:false,runId,symbol:s.symbol,direction:s.direction,signalScore:Number(s.signalScore||s.score),entry:Number(s.entry),stop:Number(s.stop),target:Number(s.target),expiresAt:s.expiresAt||null,message:`${s.symbol} ${s.direction} • score ${Number(s.signalScore||s.score).toFixed(1)} • entry ${Number(s.entry).toFixed(2)} • stop ${Number(s.stop).toFixed(2)} • target ${Number(s.target).toFixed(2)}`};
    events.unshift(row);seen.add(dedupe);created.push(row);
  }
  saved.events=events.slice(0,500);saved.rules={signalEmailEnabled:false,...(saved.rules||{})};saved.updatedAt=new Date().toISOString();await setJson(keyFor(user),saved);
  let email={sent:false,reason:'disabled'};
  if(created.length&&saved.rules.signalEmailEnabled===true){
    const account=await getAccount(user);
    if(account?.emailVerifiedAt&&account.email){
      const lines=created.map(x=>x.message+(x.expiresAt?` • expires ${x.expiresAt}`:'' )).join('\n');
      email=await sendEmail({to:account.email,subject:`Trading Signal Center: ${created.length} νέο 95+ signal`,text:`Νέα research signals:\n\n${lines}\n\nΤο model score δεν είναι πιθανότητα ή εγγύηση κέρδους. Η απόφαση και η εκτέλεση ανήκουν στον χρήστη.`,idempotencyKey:`signal-${runId||created[0].dedupe}`});
    }else email={sent:false,reason:'verified email required'};
  }
  return {created:created.length,email};
}
