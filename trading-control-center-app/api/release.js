import {requireAccount} from './_lib/access.js';
import {releaseAssignment} from './_lib/release-control.js';
import {APP_VERSION} from './_lib/release.js';
export default async function handler(req,res){try{const a=await requireAccount(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});return res.status(200).json({version:APP_VERSION,assignment:await releaseAssignment(a.username),liveExecution:false})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
