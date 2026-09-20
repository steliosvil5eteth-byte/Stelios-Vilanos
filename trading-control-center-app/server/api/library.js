import {requireAccount} from './_lib/access.js';
export const LIBRARY=[
 {id:'trend-conservative-v1',name:'Trend Conservative',description:'Πιο αυστηρό trend filter, μικρότερο trade frequency.',settings:{minScore:74,minRR:2.2,scanMinBars:300,scanMinOosTrades:8,scanMinOosAvgR:0.10,scanMinOosPF:1.20}},
 {id:'balanced-momentum-v1',name:'Balanced Momentum',description:'Ισορροπία trend, momentum και volume.',settings:{minScore:68,minRR:2.0,scanMinBars:250,scanMinOosTrades:5,scanMinOosAvgR:0.05,scanMinOosPF:1.10}},
 {id:'high-selectivity-v1',name:'High Selectivity',description:'Λιγότερα signals με αυστηρότερο score και OOS φίλτρα.',settings:{minScore:80,minRR:2.5,scanMinBars:350,scanMinOosTrades:10,scanMinOosAvgR:0.12,scanMinOosPF:1.25}}
];
export default async function handler(req,res){try{await requireAccount(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});return res.status(200).json({strategies:LIBRARY,note:'Research presets only; not investment recommendations.'})}catch(e){return res.status(e.status||500).json({error:e.message})}}
