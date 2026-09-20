import {checksumJson} from './integrity.js';
const REQUIRED_TOP=['schema','exportedAt','accounts','data'];
export function verifyRecoveryPayload(payload,{maxUsers=1000}={}){
  const issues=[];
  if(!payload||typeof payload!=='object'||Array.isArray(payload))issues.push({severity:'critical',type:'INVALID_ROOT'});
  for(const k of REQUIRED_TOP)if(payload?.[k]===undefined)issues.push({severity:'critical',type:'MISSING_FIELD',field:k});
  const accounts=Array.isArray(payload?.accounts)?payload.accounts:[];
  if(accounts.length>maxUsers)issues.push({severity:'critical',type:'TOO_MANY_USERS',count:accounts.length,maxUsers});
  const names=new Set();
  for(const a of accounts){const u=String(a?.username||'').toLowerCase();if(!u)issues.push({severity:'critical',type:'ACCOUNT_WITHOUT_USERNAME'});if(names.has(u))issues.push({severity:'critical',type:'DUPLICATE_USERNAME',username:u});names.add(u);if(a?.auth)issues.push({severity:'warning',type:'CONTAINS_AUTH_MATERIAL',username:u})}
  const data=payload?.data&&typeof payload.data==='object'?payload.data:{};
  for(const u of Object.keys(data))if(!names.has(String(u).toLowerCase()))issues.push({severity:'warning',type:'DATA_WITHOUT_ACCOUNT',username:u});
  return {ok:issues.every(x=>x.severity!=='critical'),users:accounts.length,dataUsers:Object.keys(data).length,sha256:checksumJson(payload),critical:issues.filter(x=>x.severity==='critical').length,warnings:issues.filter(x=>x.severity==='warning').length,issues:issues.slice(0,100)};
}
