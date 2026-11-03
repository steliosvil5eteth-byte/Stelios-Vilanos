import {getSession} from './session.js';
import {getAccount,sanitizeAccount} from './accounts.js';
import {entitlements} from './plans.js';
import {verifyCsrf} from './csrf.js';
import {requireMaintenanceWriteAllowed} from './maintenance.js';
export async function requireAccount(req){const session=getSession(req);if(!session?.u){const e=new Error('Login required');e.status=401;throw e}const account=await getAccount(session.u);if(!account||account.status!=='active'){const e=new Error('Account unavailable');e.status=403;throw e}if(Number(session.sv||1)!==Number(account.sessionVersion||1)){const e=new Error('Session expired');e.status=401;e.code='SESSION_REVOKED';throw e}verifyCsrf(req,session);await requireMaintenanceWriteAllowed(req,account);return account}
export async function requireAdmin(req){const a=await requireAccount(req);if(a.role!=='admin'){const e=new Error('Admin required');e.status=403;throw e}return a}
export function accountPayload(a){return {...sanitizeAccount(a),entitlements:entitlements(a.plan)}}
