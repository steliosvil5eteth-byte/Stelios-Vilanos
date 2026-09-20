import crypto from 'crypto';
import {getJson,setJson} from './store.js';
const KEY='tcc:security:events';
function salt(){return process.env.SESSION_SECRET||'tcc'}
function ip(req){return String(req?.headers?.['x-forwarded-for']||req?.headers?.['x-real-ip']||'').split(',')[0].trim().slice(0,80)}
function hashValue(value,prefix='id'){if(!value)return '';return crypto.createHash('sha256').update(`${salt()}:${prefix}:${String(value)}`).digest('hex').slice(0,16)}
function ipHash(req){return hashValue(ip(req),'ip')}
export function userHash(user){return hashValue(String(user||'').toLowerCase(),'user')}
export async function securityEvent(req,{type,user='',ok=true,detail='',anonymous=false}={}){const rows=(await getJson(KEY))||[];const username=String(user||'').slice(0,80);rows.unshift({ts:new Date().toISOString(),type:String(type).slice(0,60),user:anonymous?'':username,userHash:username?userHash(username):'',ok:Boolean(ok),ipHash:ipHash(req),detail:String(detail||'').slice(0,240)});await setJson(KEY,rows.slice(0,1000));return rows[0]}
export async function securityEvents(limit=100){const rows=(await getJson(KEY))||[];return rows.slice(0,Math.max(1,Math.min(500,Number(limit)||100)))}
export async function anonymizeSecurityEvents(user){const h=userHash(user),rows=(await getJson(KEY))||[];let changed=0;for(const row of rows){if(String(row.user||'').toLowerCase()===String(user||'').toLowerCase()){row.user='';row.userHash=h;changed++}}if(changed)await setJson(KEY,rows);return changed}
