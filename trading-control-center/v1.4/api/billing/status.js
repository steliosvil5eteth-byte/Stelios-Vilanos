import {requireAccount} from '../_lib/access.js';
import {entitlements} from '../_lib/plans.js';
import {billingConfig,billingCatalog} from '../_lib/billing.js';
export default async function handler(req,res){try{const a=await requireAccount(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const c=billingConfig();return res.status(200).json({billing:{enabled:c.enabled,provider:c.provider,testMode:c.testMode,webhookConfigured:c.webhookConfigured,status:a.billing?.status||'manual',note:c.enabled?'Stripe TEST mode only. No live billing endpoint exists in v1.3.':'Payment provider disabled.'},plan:a.plan,entitlements:entitlements(a.plan),catalog:billingCatalog()})}catch(e){return res.status(e.status||500).json({error:e.message})}}
