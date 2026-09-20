import crypto from 'crypto';
const COOKIE='tcc_session';
function b64url(input){return Buffer.from(input).toString('base64url')}
function sign(payload,secret){return crypto.createHmac('sha256',secret).update(payload).digest('base64url')}
export function sha256(value){return crypto.createHash('sha256').update(String(value)).digest('hex')}
export function getConfig(){return {user:process.env.APP_USER||'',passwordHash:(process.env.APP_PASSWORD_SHA256||'').toLowerCase(),secret:process.env.SESSION_SECRET||''}}
export function authConfigured(){const c=getConfig();return Boolean(c.secret&&c.secret.length>=24)}
export function createSession(username,sessionVersion=1){const {secret}=getConfig();const body=b64url(JSON.stringify({u:username,sv:Number(sessionVersion)||1,iat:Date.now(),exp:Date.now()+7*864e5}));return `${body}.${sign(body,secret)}`}
export function verifySession(token){try{const {secret}=getConfig();if(!secret||!token)return null;const [body,sig]=String(token).split('.');if(!body||!sig)return null;const expected=sign(body,secret);const a=Buffer.from(sig),b=Buffer.from(expected);if(a.length!==b.length||!crypto.timingSafeEqual(a,b))return null;const p=JSON.parse(Buffer.from(body,'base64url').toString('utf8'));if(!p.u||!p.exp||Date.now()>p.exp)return null;return p}catch{return null}}
export function parseCookies(req){return Object.fromEntries(String(req.headers.cookie||'').split(';').map(x=>x.trim()).filter(Boolean).map(x=>{const i=x.indexOf('=');return [decodeURIComponent(x.slice(0,i)),decodeURIComponent(x.slice(i+1))]}))}
export function getSession(req){return verifySession(parseCookies(req)[COOKIE])}
export function getUser(req){return getSession(req)?.u||null}
export function setSessionCookie(res,token){res.setHeader('Set-Cookie',`${COOKIE}=${encodeURIComponent(token)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${7*86400}`)}
export function clearSessionCookie(res){res.setHeader('Set-Cookie',`${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`)}
