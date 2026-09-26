import {getConsent} from './consent.js';
import {getJson} from './store.js';
export async function onboardingStatus(account){
  const consent=await getConsent(account.username),profile=(await getJson(`tcc:${account.username}:profile`))||{},state=(await getJson(`tcc:${account.username}:state`))||{};
  const steps={emailAdded:Boolean(account.email),emailVerified:Boolean(account.emailVerifiedAt),consent:Boolean(consent.current),profile:Boolean(profile.displayName||account.displayName),strategy:Boolean(state.strategy?.id||state.currentStrategy?.id)};
  const completed=Object.values(steps).filter(Boolean).length,total=Object.keys(steps).length;
  return {steps,completed,total,percent:Math.round(completed/total*100),readyForPaper:steps.emailVerified&&steps.consent};
}
export function requireVerifiedEmail(account){if(!account?.email||!account?.emailVerifiedAt){const e=new Error('Verified email required before paper execution');e.status=428;e.code='EMAIL_VERIFICATION_REQUIRED';throw e}return true}
