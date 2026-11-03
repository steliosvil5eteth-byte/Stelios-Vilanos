import {authConfigured,getSession} from '../_lib/session.js';
import {persistentStoreConfigured,storageBackend} from '../_lib/store.js';
import {databaseConfigured} from '../_lib/db.js';
import {getAccount} from '../_lib/accounts.js';
import {accountPayload} from '../_lib/access.js';
import {onboardingStatus} from '../_lib/onboarding.js';
export default async function handler(req,res){if(req.method!=='GET')return res.status(405).json({error:'GET only'});const session=getSession(req);const account=session?.u?await getAccount(session.u):null;const valid=Boolean(account&&account.status==='active'&&Number(session?.sv||1)===Number(account.sessionVersion||1));res.setHeader('Cache-Control','no-store');res.status(200).json({authenticated:valid,user:valid?account.username:null,account:valid?accountPayload(account):null,onboarding:valid?await onboardingStatus(account):null,authConfigured:authConfigured(),persistentStore:persistentStoreConfigured(),storageBackend:storageBackend(),database:databaseConfigured(),paperOnly:true,sessionRevoked:Boolean(session?.u&&!valid)})}
