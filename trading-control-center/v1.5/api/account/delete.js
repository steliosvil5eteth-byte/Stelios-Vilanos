import {requireAccount} from '../_lib/access.js';
import {verifyPassword,deleteAccount} from '../_lib/accounts.js';
import {deleteUserData} from '../_lib/user-data.js';
import {clearSessionCookie} from '../_lib/session.js';
import {securityEvent,anonymizeSecurityEvents,userHash} from '../_lib/security-events.js';
import {rateLimit,applyRateLimitError} from '../_lib/rate-limit.js';
export default async function handler(req,res){if(req.method!=='POST')return res.status(405).json({error:'POST only'});try{await rateLimit(req,{label:'account-delete',limit:3,windowMs:60*60*1000});const a=await requireAccount(req);const password=String(req.body?.password||'');const phrase=String(req.body?.confirm||'');if(phrase!=='DELETE MY ACCOUNT')return res.status(400).json({error:'Confirmation phrase must be exactly DELETE MY ACCOUNT'});if(!verifyPassword(password,a.auth))return res.status(401).json({error:'Password confirmation failed'});const pseudonym=userHash(a.username);await anonymizeSecurityEvents(a.username);await deleteUserData(a.username);await deleteAccount(a.username);await securityEvent(req,{type:'ACCOUNT_DELETED',user:'',ok:true,anonymous:true,detail:`userHash=${pseudonym}`});clearSessionCookie(res);return res.status(200).json({ok:true,deleted:true})}catch(e){applyRateLimitError(res,e);return res.status(e.status||500).json({error:e.message,code:e.code})}}
