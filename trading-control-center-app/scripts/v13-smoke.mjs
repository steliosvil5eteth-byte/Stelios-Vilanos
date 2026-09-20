import crypto from 'node:crypto';
process.env.APP_USER='v13admin';
process.env.APP_PASSWORD_SHA256=crypto.createHash('sha256').update('AdminPassword123!').digest('hex');
process.env.SESSION_SECRET='v13-security-session-secret-123456789';
process.env.EMAIL_MODE='memory';
process.env.EMAIL_FROM='Trading Center <noreply@example.test>';
process.env.APP_BASE_URL='https://example.test';
process.env.EXPOSE_DEV_TOKENS='true';
process.env.BILLING_MODE='stripe_test';
process.env.STRIPE_SECRET_KEY='sk_test_fake_only_for_local_validation';
process.env.STRIPE_WEBHOOK_SECRET='whsec_v13_local_validation_secret';
process.env.STRIPE_PRICE_PRO='price_test_pro';
process.env.STRIPE_PRICE_PREMIUM='price_test_premium';

const {createAccount,getAccount,updateAccount}=await import('../server/api/_lib/accounts.js');
const {issueEmailVerification,confirmEmailVerification}=await import('../server/api/_lib/email-verification.js');
const {emailOutbox}=await import('../server/api/_lib/email.js');
const {acceptConsent}=await import('../server/api/_lib/consent.js');
const {onboardingStatus,requireVerifiedEmail}=await import('../server/api/_lib/onboarding.js');
const {billingConfig,verifyStripeSignature,applyStripeEvent}=await import('../server/api/_lib/billing.js');

await createAccount({username:'v13-user',password:'LongPassword123!',email:'v13@example.test',plan:'free'});
let a=await getAccount('v13-user');
let blocked=false;try{requireVerifiedEmail(a)}catch(e){blocked=e.code==='EMAIL_VERIFICATION_REQUIRED'}if(!blocked)throw Error('unverified email was not blocked');
const issued=await issueEmailVerification('v13-user',{send:true});if(!issued.sent||!issued.token)throw Error('verification email/token not issued in memory mode');
if(!(await emailOutbox()).length)throw Error('email outbox empty');
await confirmEmailVerification(issued.token);a=await getAccount('v13-user');if(!a.emailVerifiedAt)throw Error('email was not verified');
let ob=await onboardingStatus(a);if(ob.readyForPaper)throw Error('paper should require consent');
await acceptConsent('v13-user',{acceptTerms:true,acceptRisk:true});ob=await onboardingStatus(a);if(!ob.readyForPaper)throw Error('verified email + consent should be paper-ready');
await updateAccount('v13-user',{email:'new-v13@example.test'});a=await getAccount('v13-user');if(a.emailVerifiedAt)throw Error('email change did not revoke verification');
const issued2=await issueEmailVerification('v13-user',{send:false});await confirmEmailVerification(issued2.token);a=await getAccount('v13-user');if(!a.emailVerifiedAt)throw Error('second email verification failed');

let cfg=billingConfig();if(!cfg.enabled||!cfg.testMode||cfg.provider!=='stripe_test')throw Error('stripe test mode not enabled');
const raw=JSON.stringify({id:'evt_test',type:'checkout.session.completed',data:{object:{client_reference_id:'v13-user',metadata:{username:'v13-user',plan:'pro'},customer:'cus_test',subscription:'sub_test'}}});
const ts=Math.floor(Date.now()/1000),sig=crypto.createHmac('sha256',process.env.STRIPE_WEBHOOK_SECRET).update(`${ts}.${raw}`).digest('hex');
verifyStripeSignature(raw,`t=${ts},v1=${sig}`);
const applied=await applyStripeEvent(JSON.parse(raw));if(!applied.handled)throw Error('stripe test event not applied');
a=await getAccount('v13-user');if(a.plan!=='pro'||a.billing?.provider!=='stripe_test')throw Error('test billing did not activate pro');
await applyStripeEvent({type:'customer.subscription.deleted',data:{object:{id:'sub_test',customer:'cus_test',metadata:{username:'v13-user',plan:'pro'}}}});a=await getAccount('v13-user');if(a.plan!=='free')throw Error('subscription deletion did not revert free');
process.env.STRIPE_SECRET_KEY='sk_live_should_never_enable';cfg=billingConfig();if(cfg.enabled)throw Error('live Stripe key must never enable billing in v1.3');

console.log('v1.3 smoke: OK');
