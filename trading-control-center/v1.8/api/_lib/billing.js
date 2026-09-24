import crypto from 'crypto';
import {updateAccount,getAccount} from './accounts.js';
import {PLANS,normalizePlan} from './plans.js';
import {appendAudit} from './store.js';

export function billingConfig(){
  const mode=String(process.env.BILLING_MODE||'disabled').toLowerCase();const key=String(process.env.STRIPE_SECRET_KEY||'');const webhookSecret=String(process.env.STRIPE_WEBHOOK_SECRET||'');
  const safeTest=mode==='stripe_test'&&key.startsWith('sk_test_');
  return {mode,enabled:safeTest,provider:safeTest?'stripe_test':'disabled',testMode:safeTest,webhookConfigured:safeTest&&webhookSecret.startsWith('whsec_'),prices:{pro:String(process.env.STRIPE_PRICE_PRO||''),premium:String(process.env.STRIPE_PRICE_PREMIUM||'')}};
}
export async function createCheckout(account,targetPlan){
  const c=billingConfig(),plan=normalizePlan(targetPlan);if(!c.enabled){const e=new Error('Billing is disabled or not configured in Stripe test mode');e.status=503;e.code='BILLING_DISABLED';throw e}if(!['pro','premium'].includes(plan)){const e=new Error('Checkout is available only for Pro or Premium');e.status=400;throw e}if(!account.emailVerifiedAt){const e=new Error('Verify email before starting checkout');e.status=428;e.code='EMAIL_VERIFICATION_REQUIRED';throw e}const price=c.prices[plan];if(!price){const e=new Error(`Missing Stripe price for ${plan}`);e.status=503;throw e}
  const base=String(process.env.APP_BASE_URL||'').replace(/\/$/,'');if(!base){const e=new Error('APP_BASE_URL is required for checkout');e.status=503;throw e}
  const p=new URLSearchParams();p.set('mode','subscription');p.set('success_url',`${base}/?billing=success`);p.set('cancel_url',`${base}/?billing=cancel`);p.set('customer_email',account.email);p.set('client_reference_id',account.username);p.set('line_items[0][price]',price);p.set('line_items[0][quantity]','1');p.set('metadata[username]',account.username);p.set('metadata[plan]',plan);p.set('subscription_data[metadata][username]',account.username);p.set('subscription_data[metadata][plan]',plan);p.set('allow_promotion_codes','true');
  const r=await fetch('https://api.stripe.com/v1/checkout/sessions',{method:'POST',headers:{Authorization:`Bearer ${process.env.STRIPE_SECRET_KEY}`,'Content-Type':'application/x-www-form-urlencoded'},body:p.toString()});const raw=await r.text();let data={};try{data=JSON.parse(raw)}catch{data={raw}}if(!r.ok){const e=new Error(`Stripe test checkout HTTP ${r.status}`);e.status=502;e.provider=data;throw e}await appendAudit(account.username,{ts:new Date().toISOString(),type:'BILLING_CHECKOUT_CREATED',detail:`plan=${plan} testMode=true`});return {id:data.id,url:data.url,plan,testMode:true};
}
export function verifyStripeSignature(rawBody,header){
  const secret=String(process.env.STRIPE_WEBHOOK_SECRET||'');if(!secret){const e=new Error('Stripe webhook secret not configured');e.status=503;throw e}const parts=String(header||'').split(',').map(x=>x.split('=')).filter(x=>x.length===2);const ts=parts.find(x=>x[0]==='t')?.[1],sigs=parts.filter(x=>x[0]==='v1').map(x=>x[1]);if(!ts||!sigs.length){const e=new Error('Invalid Stripe signature header');e.status=400;throw e}if(Math.abs(Date.now()/1000-Number(ts))>300){const e=new Error('Stripe webhook timestamp outside tolerance');e.status=400;throw e}const expected=crypto.createHmac('sha256',secret).update(`${ts}.${rawBody}`).digest('hex');const ok=sigs.some(sig=>{const a=Buffer.from(sig),b=Buffer.from(expected);return a.length===b.length&&crypto.timingSafeEqual(a,b)});if(!ok){const e=new Error('Stripe webhook signature verification failed');e.status=400;throw e}return true;
}
export async function applyStripeEvent(event){
  const obj=event?.data?.object||{},type=String(event?.type||'');let username=String(obj?.metadata?.username||obj?.client_reference_id||'').toLowerCase(),plan=normalizePlan(obj?.metadata?.plan||'free');if(!username)return {handled:false,reason:'missing username metadata'};const account=await getAccount(username);if(!account)return {handled:false,reason:'account not found'};
  if(type==='checkout.session.completed'){
    if(!['pro','premium'].includes(plan))return {handled:false,reason:'invalid checkout plan'};await updateAccount(username,{plan,billing:{provider:'stripe_test',status:'active',testMode:true,stripeCustomerId:obj.customer||'',stripeSubscriptionId:obj.subscription||'',updatedAt:new Date().toISOString()}});await appendAudit(username,{ts:new Date().toISOString(),type:'BILLING_TEST_ACTIVATED',detail:`plan=${plan}`});return {handled:true,username,plan,status:'active'};
  }
  if(type==='customer.subscription.updated'){
    const active=['active','trialing'].includes(String(obj.status||''));if(active&&['pro','premium'].includes(plan))await updateAccount(username,{plan,billing:{provider:'stripe_test',status:String(obj.status),testMode:true,stripeCustomerId:obj.customer||'',stripeSubscriptionId:obj.id||'',updatedAt:new Date().toISOString()}});else await updateAccount(username,{billing:{provider:'stripe_test',status:String(obj.status||'unknown'),testMode:true,updatedAt:new Date().toISOString()}});return {handled:true,username,plan:active?plan:account.plan,status:String(obj.status||'unknown')};
  }
  if(type==='customer.subscription.deleted'){
    await updateAccount(username,{plan:'free',billing:{provider:'stripe_test',status:'canceled',testMode:true,stripeCustomerId:obj.customer||'',stripeSubscriptionId:obj.id||'',updatedAt:new Date().toISOString()}});await appendAudit(username,{ts:new Date().toISOString(),type:'BILLING_TEST_CANCELED',detail:'plan=free'});return {handled:true,username,plan:'free',status:'canceled'};
  }
  return {handled:false,reason:'event ignored'};
}
export function billingCatalog(){return Object.values(PLANS).map(x=>({id:x.id,label:x.label,monthlyPriceEur:x.monthlyPriceEur,maxWatchlist:x.maxWatchlist,maxHoldings:x.maxHoldings,signalEmail:x.signalEmail,autoWatch:x.autoWatch,autoWatchMinutes:x.autoWatchMinutes,maxAutoWatchSymbols:x.maxAutoWatchSymbols,exports:x.exports}))}
