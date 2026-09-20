import {requireAccount} from './_lib/access.js';
import {onboardingStatus} from './_lib/onboarding.js';
export default async function handler(req,res){try{const a=await requireAccount(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});return res.status(200).json({onboarding:await onboardingStatus(a)})}catch(e){return res.status(e.status||500).json({error:e.message,code:e.code})}}
