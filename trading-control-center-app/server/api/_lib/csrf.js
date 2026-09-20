import crypto from 'crypto';

function secret(){return process.env.SESSION_SECRET||''}
function payload(session){return `${session?.u||''}:${Number(session?.sv||1)}:${Number(session?.iat||0)}`}
export function csrfToken(session){const s=secret();if(!s||!session?.u)return '';return crypto.createHmac('sha256',s).update(`csrf:${payload(session)}`).digest('base64url')}
function safeEqual(a,b){const aa=Buffer.from(String(a||'')),bb=Buffer.from(String(b||''));return aa.length===bb.length&&crypto.timingSafeEqual(aa,bb)}
export function verifyCsrf(req,session){const method=String(req.method||'GET').toUpperCase();if(['GET','HEAD','OPTIONS'].includes(method))return true;const expected=csrfToken(session);const got=String(req.headers?.['x-csrf-token']||'');if(!expected||!got||!safeEqual(got,expected)){const e=new Error('Security token missing or expired. Refresh the session and retry.');e.status=403;e.code='CSRF_REQUIRED';throw e}return true}
