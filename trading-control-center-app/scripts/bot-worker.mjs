// Run on an existing always-on machine; no exchange key, no paid service.
import {pathToFileURL} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';

export async function tickWorker({base, secret, fetchImpl=fetch, signal}) {
  const url = new URL(base);
  if (url.protocol !== 'https:' || url.username || url.password || !secret) {
    throw new Error('Set HTTPS BOT_BASE_URL and CRON_SECRET');
  }
  const response = await fetchImpl(new URL('/api/bot', url), {
    method: 'POST', redirect: 'error',
    headers: {Authorization: `Bearer ${secret}`, 'Content-Type': 'application/json'},
    body: JSON.stringify({action: 'tick'}), signal
  });
  if (!response.ok) throw new Error(`BOT_HTTP_${response.status}`);
  let body;
  try { body = await response.json(); }
  catch { throw new Error('BOT_INVALID_JSON'); }
  if (!body || body.error || !body.state || !body.metrics) throw new Error('BOT_INVALID_RESPONSE');
  return body.metrics;
}

export async function runWorker({env=process.env, fetchImpl=fetch, signal, log=console.log, error=console.error}={}) {
  const base=env.BOT_BASE_URL, secret=env.CRON_SECRET;
  if (!base || !secret) throw new Error('Set HTTPS BOT_BASE_URL and CRON_SECRET');
  const url=new URL(base);
  if (url.protocol!=='https:' || url.username || url.password) throw new Error('Set HTTPS BOT_BASE_URL and CRON_SECRET');
  while (!signal?.aborted) {
    let ok=false;
    try {
      const timeout=AbortSignal.timeout(45000);
      const metrics=await tickWorker({base, secret, fetchImpl, signal:signal?AbortSignal.any([signal,timeout]):timeout});
      ok=true; log(JSON.stringify({at:new Date().toISOString(),ok:true,metrics}));
    } catch (e) {
      if (signal?.aborted) break;
      // Do not print remote bodies or transport messages that may contain secrets.
      const code=/^BOT_(HTTP_\d+|INVALID_JSON|INVALID_RESPONSE)$/.test(e.message)?e.message:'BOT_REQUEST_FAILED';
      error(JSON.stringify({at:new Date().toISOString(),ok:false,error:code}));
    }
    if (env.BOT_RUN_ONCE==='true') return ok?0:1;
    try { await delay(60000,undefined,{signal}); }
    catch(e) { if(signal?.aborted) break; throw e; }
  }
  return 0;
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  const controller=new AbortController();
  const stop=()=>controller.abort();
  process.once('SIGINT',stop); process.once('SIGTERM',stop);
  try { process.exitCode=await runWorker({signal:controller.signal}); }
  catch { console.error('Worker configuration invalid: set HTTPS BOT_BASE_URL and CRON_SECRET'); process.exitCode=1; }
  finally { process.removeListener('SIGINT',stop);process.removeListener('SIGTERM',stop); }
}
