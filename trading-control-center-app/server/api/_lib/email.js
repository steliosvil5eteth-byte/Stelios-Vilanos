import {getJson,setJson} from './store.js';

const OUTBOX='tcc:email:outbox';
export function emailConfig(){
  const mode=String(process.env.EMAIL_MODE||'disabled').toLowerCase();
  const resendKey=String(process.env.RESEND_API_KEY||'');
  const from=String(process.env.EMAIL_FROM||'').trim();
  const appBaseUrl=String(process.env.APP_BASE_URL||'').replace(/\/$/,'');
  const configured=mode==='memory'||(mode==='resend'&&resendKey.startsWith('re_')&&from.includes('@'));
  return {mode,configured,from,appBaseUrl};
}
export async function sendEmail({to,subject,text='',html='',idempotencyKey=''}={}){
  const c=emailConfig();const recipient=String(to||'').trim().toLowerCase();
  if(!recipient||!subject){const e=new Error('Email recipient and subject required');e.status=400;throw e}
  if(c.mode==='memory'){
    const rows=(await getJson(OUTBOX))||[];const msg={id:`mem_${Date.now()}_${Math.random().toString(36).slice(2,8)}`,to:recipient,from:c.from||'memory@localhost',subject:String(subject).slice(0,180),text:String(text||''),html:String(html||''),createdAt:new Date().toISOString(),idempotencyKey:String(idempotencyKey||'')};rows.unshift(msg);await setJson(OUTBOX,rows.slice(0,100));return {sent:true,provider:'memory',id:msg.id};
  }
  if(c.mode!=='resend'||!c.configured)return {sent:false,provider:'disabled',reason:'email provider not configured'};
  const headers={Authorization:`Bearer ${process.env.RESEND_API_KEY}`,'Content-Type':'application/json'};if(idempotencyKey)headers['Idempotency-Key']=String(idempotencyKey).slice(0,256);
  const r=await fetch('https://api.resend.com/emails',{method:'POST',headers,body:JSON.stringify({from:c.from,to:[recipient],subject:String(subject).slice(0,180),text:String(text||''),html:String(html||'')})});
  const raw=await r.text();let data={};try{data=JSON.parse(raw)}catch{data={raw}}
  if(!r.ok){const e=new Error(`Email provider HTTP ${r.status}`);e.status=502;e.provider=data;throw e}
  return {sent:true,provider:'resend',id:data.id||null};
}
export async function emailOutbox(){return (await getJson(OUTBOX))||[]}
