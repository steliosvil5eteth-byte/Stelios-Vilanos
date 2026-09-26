import {requireAccount} from '../_lib/access.js';
import {getSession} from '../_lib/session.js';
import {csrfToken} from '../_lib/csrf.js';
export default async function handler(req,res){try{if(req.method!=='GET')return res.status(405).json({error:'GET only'});await requireAccount(req);res.setHeader('Cache-Control','no-store');return res.status(200).json({csrfToken:csrfToken(getSession(req))})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
