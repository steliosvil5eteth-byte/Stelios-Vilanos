import {clearSessionCookie} from '../_lib/session.js';
import {requireAccount} from '../_lib/access.js';
import {securityEvent} from '../_lib/security-events.js';
export default async function handler(req,res){if(req.method!=='POST')return res.status(405).json({error:'POST only'});try{const a=await requireAccount(req);await securityEvent(req,{type:'LOGOUT',user:a.username,ok:true});clearSessionCookie(res);return res.status(200).json({ok:true})}catch(e){clearSessionCookie(res);return res.status(e.status||500).json({error:e.message,code:e.code})}}
