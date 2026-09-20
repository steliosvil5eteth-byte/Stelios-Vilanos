import {requireAdmin} from '../_lib/access.js';
import {getReleaseControl,updateReleaseControl} from '../_lib/release-control.js';
import {requestId} from '../_lib/request-trace.js';
export default async function handler(req,res){try{const rid=requestId(req,res);const a=await requireAdmin(req);if(req.method==='GET')return res.status(200).json({requestId:rid,release:await getReleaseControl()});if(req.method==='PUT')return res.status(200).json({ok:true,requestId:rid,release:await updateReleaseControl(a.username,req.body||{})});return res.status(405).json({error:'GET or PUT only'})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
