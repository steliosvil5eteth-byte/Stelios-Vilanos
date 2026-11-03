import {requireAccount,accountPayload} from './_lib/access.js';
export default async function handler(req,res){try{if(req.method!=='GET')return res.status(405).json({error:'GET only'});const a=await requireAccount(req);return res.status(200).json({account:accountPayload(a),paperOnly:true,liveExecution:false})}catch(e){return res.status(e.status||500).json({error:e.message})}}
