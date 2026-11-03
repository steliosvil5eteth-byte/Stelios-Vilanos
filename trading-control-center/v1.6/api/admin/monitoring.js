import {requireAdmin} from '../_lib/access.js';
import {systemSnapshot,monitoringEvents} from '../_lib/monitoring.js';
export default async function handler(req,res){try{await requireAdmin(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});return res.status(200).json({snapshot:await systemSnapshot(),events:await monitoringEvents(Number(req.query?.limit)||100)})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
