import {requireAdmin} from '../_lib/access.js';
import {getMaintenanceState,setMaintenanceState} from '../_lib/maintenance.js';
import {requestId} from '../_lib/request-trace.js';
export default async function handler(req,res){try{const rid=requestId(req,res);const a=await requireAdmin(req);if(req.method==='GET')return res.status(200).json({requestId:rid,maintenance:await getMaintenanceState()});if(req.method==='PUT'){const maintenance=await setMaintenanceState(a.username,req.body||{});return res.status(200).json({ok:true,requestId:rid,maintenance})}return res.status(405).json({error:'GET or PUT only'})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code,maintenance:e.maintenance})}}
