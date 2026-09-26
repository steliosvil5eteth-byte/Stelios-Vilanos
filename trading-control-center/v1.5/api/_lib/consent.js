import {getJson,setJson} from './store.js';
export const TERMS_VERSION='2026-09-20-v1';
export const RISK_VERSION='2026-09-20-v1';
function key(user){return `tcc:${user}:consent`}
export async function getConsent(user){const c=(await getJson(key(user)))||{};return {...c,termsVersion:TERMS_VERSION,riskVersion:RISK_VERSION,termsCurrent:c.termsVersion===TERMS_VERSION,riskCurrent:c.riskVersion===RISK_VERSION,current:c.termsVersion===TERMS_VERSION&&c.riskVersion===RISK_VERSION}}
export async function acceptConsent(user,{acceptTerms=false,acceptRisk=false}={}){if(acceptTerms!==true||acceptRisk!==true){const e=new Error('Terms and paper-trading risk disclosure must both be accepted');e.status=400;throw e}const now=new Date().toISOString();const c={termsVersion:TERMS_VERSION,riskVersion:RISK_VERSION,acceptedAt:now,updatedAt:now};await setJson(key(user),c);return {...c,termsCurrent:true,riskCurrent:true,current:true}}
export async function requirePaperConsent(user){const c=await getConsent(user);if(!c.current){const e=new Error('Accept the current Terms and Paper Trading Risk Disclosure before submitting paper orders');e.status=428;e.code='CONSENT_REQUIRED';throw e}return c}
