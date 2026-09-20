import {requireAdmin} from '../_lib/access.js';
import {checkDataIntegrity} from '../_lib/integrity.js';
import {requestId} from '../_lib/request-trace.js';
export default async function handler(req,res){try{const rid=requestId(req,res);await requireAdmin(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const report=await checkDataIntegrity();return res.status(report.ok?200:409).json({requestId:rid,report})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
