import json,pathlib,time,sys
from commons_acquisition import fetch_image,STATE
ROOT=pathlib.Path(__file__).resolve().parent
QUEUE=ROOT/'commons_queue'
STOP=ROOT/'commons_queue_stop.request'
idle_since=time.time()
while True:
 if STOP.exists():
  print('STOP_REQUESTED after preserving completed acquisition results',flush=True);sys.exit(0)
 worked=False
 if STATE.exists() and json.loads(STATE.read_text()).get('globally_paused'):
  print('GLOBAL_PAUSE '+STATE.read_text(),flush=True);sys.exit(2)
 for q in sorted(QUEUE.glob('*.queue.json')):
  d=json.loads(q.read_text());result_path=q.with_suffix('.results.json')
  results=json.loads(result_path.read_text()) if result_path.exists() else {'queue':str(q),'results':{}}
  for item in d['requests']:
   key=str(item['id'])
   if key in results['results']:continue
   worked=True;idle_since=time.time()
   try:
    result=fetch_image(item['imageinfo'],item['destination']);result['status']='downloaded'
   except Exception as exc:
    result={'status':'error','error':type(exc).__name__+': '+str(exc),'path':item['destination']}
   results['results'][key]=result
   temp=result_path.with_suffix('.tmp');temp.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');temp.replace(result_path)
   print(q.name,key,result['status'],result.get('bytes',result.get('error')),flush=True)
   if STATE.exists() and json.loads(STATE.read_text()).get('globally_paused'):
    print('GLOBAL_PAUSE '+STATE.read_text(),flush=True);sys.exit(2)
   if STOP.exists():
    print('STOP_REQUESTED after preserving completed acquisition results',flush=True);sys.exit(0)
  if worked:break
 if not worked:
  if time.time()-idle_since>1200:print('No pending requests for20minutes; stopping',flush=True);break
  time.sleep(5)
