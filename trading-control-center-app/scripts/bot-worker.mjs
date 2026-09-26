// Run on an existing always-on machine; no exchange key, no paid service.
const base=process.env.BOT_BASE_URL,secret=process.env.CRON_SECRET;
if(!base||!secret||!/^https:\/\//.test(base))throw new Error('Set HTTPS BOT_BASE_URL and CRON_SECRET');
let stopping=false;process.on('SIGINT',()=>{stopping=true});process.on('SIGTERM',()=>{stopping=true});
while(!stopping){
  try{const r=await fetch(new URL('/api/bot',base),{method:'POST',headers:{Authorization:`Bearer ${secret}`,'Content-Type':'application/json'},body:JSON.stringify({action:'tick'}),signal:AbortSignal.timeout(45000)});const j=await r.json();console.log(JSON.stringify({at:new Date().toISOString(),ok:r.ok,error:j.error,metrics:j.metrics}));}
  catch(e){console.error(JSON.stringify({at:new Date().toISOString(),error:e.message}));}
  if(process.env.BOT_RUN_ONCE==='true')break;
  await new Promise(resolve=>{const timer=setTimeout(resolve,60000);if(stopping){clearTimeout(timer);resolve();}});
}
