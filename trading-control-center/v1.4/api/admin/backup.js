import crypto from 'crypto';
import {requireAdmin} from '../_lib/access.js';
import {allAccounts,exportAccounts} from '../_lib/accounts.js';
import {getJson} from '../_lib/store.js';
const USER_KEYS=['state','trades','journal','audit','alerts','profile','strategies','scanRuns','consent'];
function safeEq(a,b){const aa=Buffer.from(String(a||'')),bb=Buffer.from(String(b||''));return aa.length===bb.length&&crypto.timingSafeEqual(aa,bb)}
export default async function handler(req,res){
 try{await requireAdmin(req);if(req.method!=='GET')return res.status(405).json({error:'GET only'});const includeAuth=String(req.query?.full||'')==='1';if(includeAuth&&!safeEq(req.headers['x-backup-secret'],process.env.BACKUP_EXPORT_SECRET)){return res.status(403).json({error:'Full backup requires X-Backup-Secret'})}const users=await allAccounts(),data={};for(const u of users){data[u.username]={};for(const k of USER_KEYS)data[u.username][k]=(await getJson(`tcc:${u.username}:${k}`))??null}const backup={schema:'tcc-backup-v1.3',version:'1.3',exportedAt:new Date().toISOString(),paperOnly:true,accounts:await exportAccounts({includeAuth}),data};res.setHeader('Content-Disposition',`attachment; filename="tcc-backup-${new Date().toISOString().slice(0,10)}.json"`);res.setHeader('Cache-Control','no-store');return res.status(200).json(backup)}catch(e){return res.status(e.status||500).json({error:e.message})}
}
