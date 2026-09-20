import crypto from 'crypto';
import {getJson,setJson} from './store.js';
import {normalizePlan,entitlements} from './plans.js';

const KEY='tcc:accounts:v1';
function cleanUser(v){return String(v||'').trim().toLowerCase().replace(/[^a-z0-9._@+-]/g,'').slice(0,80)}
function cleanEmail(v){const x=String(v||'').trim().toLowerCase().slice(0,160);return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(x)?x:''}
function safeEqual(a,b){const aa=Buffer.from(String(a)),bb=Buffer.from(String(b));return aa.length===bb.length&&crypto.timingSafeEqual(aa,bb)}
function legacyBootstrap(){
 const username=cleanUser(process.env.APP_USER||''); const hash=String(process.env.APP_PASSWORD_SHA256||'').toLowerCase();
 if(!username||!hash)return null;
 const email=cleanEmail(process.env.APP_EMAIL||'');return {username,displayName:process.env.APP_DISPLAY_NAME||username,email,emailVerifiedAt:email?'bootstrap':null,role:'admin',plan:'premium',status:'active',sessionVersion:1,billing:{provider:'disabled',status:'manual'},auth:{type:'sha256',hash},createdAt:'bootstrap',source:'env'};
}
export function hashPassword(password,salt=crypto.randomBytes(16).toString('hex')){const hash=crypto.scryptSync(String(password),salt,64).toString('hex');return {type:'scrypt',salt,hash}}
export function verifyPassword(password,auth){
 if(auth?.type==='scrypt'&&auth.salt&&auth.hash){const got=crypto.scryptSync(String(password),auth.salt,64).toString('hex');return safeEqual(got,auth.hash)}
 if(auth?.type==='sha256'&&auth.hash){const got=crypto.createHash('sha256').update(String(password)).digest('hex');return safeEqual(got,String(auth.hash).toLowerCase())}
 return false;
}
export async function allAccounts(){const rows=(await getJson(KEY))||[];const bootstrap=legacyBootstrap();const map=new Map(rows.map(x=>[cleanUser(x.username),x]));if(bootstrap&&!map.has(bootstrap.username))map.set(bootstrap.username,bootstrap);return [...map.values()].map(sanitizeAccount)}
export async function rawAccountRows(){return (await getJson(KEY))||[]}
export async function getAccount(username){const u=cleanUser(username);if(!u)return null;const rows=await rawAccountRows();let row=rows.find(x=>cleanUser(x.username)===u)||null;if(!row){const b=legacyBootstrap();if(b?.username===u)row=b}return row?normalizeAccount(row):null}

export async function findAccountByEmail(email){const e=cleanEmail(email);if(!e)return null;const rows=await rawAccountRows();let row=rows.find(x=>cleanEmail(x.email)===e)||null;if(!row){const b=legacyBootstrap();if(b&&cleanEmail(b.email)===e)row=b}return row?normalizeAccount(row):null}
export async function saveAccount(account){const a=normalizeAccount(account);const rows=await rawAccountRows();const i=rows.findIndex(x=>cleanUser(x.username)===a.username);if(i>=0)rows[i]=a;else rows.push(a);await setJson(KEY,rows.slice(0,500));return sanitizeAccount(a)}
export async function createAccount({username,password,displayName='',email='',role='user',plan='free'}={}){const u=cleanUser(username);if(!u||String(password||'').length<10){const e=new Error('Valid username and password of at least 10 characters required');e.status=400;throw e}if(await getAccount(u)){const e=new Error('User already exists');e.status=409;throw e}const now=new Date().toISOString();return saveAccount({username:u,displayName:String(displayName||u).slice(0,80),email:cleanEmail(email),emailVerifiedAt:null,role:role==='admin'?'admin':'user',plan:normalizePlan(plan),status:'active',sessionVersion:1,billing:{provider:'disabled',status:'manual'},auth:hashPassword(password),createdAt:now,updatedAt:now,source:'store'})}
export async function updateAccount(username,patch={}){const current=await getAccount(username);if(!current){const e=new Error('User not found');e.status=404;throw e}if(current.source==='env'&&patch.status==='disabled'){const e=new Error('Bootstrap admin cannot be disabled from app');e.status=409;throw e}const nextEmail=patch.email!=null?cleanEmail(patch.email):current.email;const emailChanged=patch.email!=null&&nextEmail!==current.email;const next={...current,displayName:patch.displayName!=null?String(patch.displayName).slice(0,80):current.displayName,email:nextEmail,emailVerifiedAt:emailChanged?null:(patch.emailVerifiedAt!==undefined?patch.emailVerifiedAt:current.emailVerifiedAt||null),role:patch.role?(patch.role==='admin'?'admin':'user'):current.role,plan:patch.plan?normalizePlan(patch.plan):current.plan,status:patch.status?(patch.status==='disabled'?'disabled':'active'):current.status,updatedAt:new Date().toISOString(),source:'store'};if(patch.billing&&typeof patch.billing==='object')next.billing={...current.billing,...patch.billing};if(patch.password){if(String(patch.password).length<10){const e=new Error('Password must be at least 10 characters');e.status=400;throw e}next.auth=hashPassword(patch.password);next.sessionVersion=Number(current.sessionVersion||1)+1}return saveAccount(next)}

export async function deleteAccount(username){
 const u=cleanUser(username);if(!u){const e=new Error('Invalid user');e.status=400;throw e}
 const b=legacyBootstrap();if(b?.username===u){const e=new Error('Bootstrap admin cannot be deleted from app');e.status=409;throw e}
 const rows=await rawAccountRows();const next=rows.filter(x=>cleanUser(x.username)!==u);if(next.length===rows.length){const e=new Error('User not found');e.status=404;throw e}await setJson(KEY,next);return true;
}

export function normalizeAccount(a){return {...a,username:cleanUser(a.username),displayName:String(a.displayName||a.username||'').slice(0,80),email:cleanEmail(a.email),emailVerifiedAt:a.emailVerifiedAt||null,role:a.role==='admin'?'admin':'user',plan:normalizePlan(a.plan),status:a.status==='disabled'?'disabled':'active',sessionVersion:Math.max(1,Number(a.sessionVersion)||1),billing:{provider:'disabled',status:'manual',...(a.billing||{})}}}
export function sanitizeAccount(a){const n=normalizeAccount(a);const {auth,...safe}=n;return {...safe,entitlements:entitlements(n.plan)}}
export async function exportAccounts({includeAuth=false}={}){const rows=await rawAccountRows();return includeAuth?rows.map(normalizeAccount):rows.map(sanitizeAccount)}
