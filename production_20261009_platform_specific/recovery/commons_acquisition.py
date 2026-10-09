"""Serialized public Wikimedia image acquisition using server-documented thumbnails.

No retries, proxy changes, cookies, impersonation, or synthesized image URLs.
Call with exact imageinfo metadata (iiurlwidth=1280 or1920) from Commons API.
"""
import pathlib,json,time,fcntl,urllib.request,urllib.parse,urllib.error,email.utils,hashlib
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parent
LOCK=ROOT/'commons_acquisition.lock'
STATE=ROOT/'commons_acquisition_state.json'
POLICY=ROOT/'commons_acquisition_policy.json'
LOG=ROOT/'commons_acquisition_events.jsonl'
USER_AGENT='SteliosSocialSourceAudit/1.0'

def _read(path,default):
 try:return json.loads(path.read_text())
 except FileNotFoundError:return default

def _event(data):
 with LOG.open('a') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')

def fetch_image(imageinfo,destination):
 """Fetch once under the shared lock; return actual hash/bytes/size/source URL."""
 destination=pathlib.Path(destination)
 url=imageinfo.get('thumburl') or imageinfo['url']
 parsed=urllib.parse.urlparse(url)
 if parsed.scheme!='https' or parsed.hostname not in {'thumb.wikimedia.org','upload.wikimedia.org'}:
  raise ValueError('Expected the exact public Commons imageinfo media URL')
 if not destination.exists() and (parsed.hostname!='thumb.wikimedia.org' or '/thumb/' not in parsed.path or 'thumbnail_unscaled' in parsed.query):
  raise ValueError('Unscaled original forbidden: request the largest standard imageinfo thumbnail width strictly below the original width')
 with LOCK.open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  state=_read(STATE,{'last_request_epoch':0})
  if state.get('globally_paused'):
   raise RuntimeError('Shared image acquisition paused after HTTP denial; see commons_acquisition_state.json')
  while True:
   policy=_read(POLICY,{'min_interval_seconds':30})
   delay=float(policy['min_interval_seconds'])-(time.time()-float(state.get('last_request_epoch',0)))
   if delay<=0:break
   time.sleep(min(delay,5))
  if destination.exists():
   raw=destination.read_bytes()
  else:
   destination.parent.mkdir(parents=True,exist_ok=True)
   now=time.time();state['last_request_epoch']=now;STATE.write_text(json.dumps(state,indent=2)+'\n')
   try:
    response=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':USER_AGENT}),timeout=45)
    raw=response.read()
    # Validate before materializing a requested media artifact.
    import io
    im=Image.open(io.BytesIO(raw));im.verify()
    destination.write_bytes(raw)
    state['last_request_epoch']=time.time();STATE.write_text(json.dumps(state,indent=2)+'\n')
    _event({'at_epoch':now,'url':url,'status':response.status,'bytes':len(raw),'path':str(destination)})
   except urllib.error.HTTPError as exc:
    error={'at_epoch':now,'url':url,'status':exc.code,'reason':str(exc.reason),'retry_after':exc.headers.get('Retry-After'),'path':str(destination)}
    _event(error)
    if exc.code in (403,429):
     state['globally_paused']=True;state['pause_error']=error
     retry_after=error['retry_after']
     if retry_after:
      try: state['earliest_retry_epoch']=time.time()+float(retry_after)
      except ValueError:
       try: state['earliest_retry_epoch']=email.utils.parsedate_to_datetime(retry_after).timestamp()
       except (ValueError,TypeError): pass
     STATE.write_text(json.dumps(state,indent=2)+'\n')
    raise
  im=Image.open(destination)
  if list(im.size)==[imageinfo.get('width'),imageinfo.get('height')]:
   url=imageinfo['url']
  return {'path':str(destination),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'dimensions_px':list(im.size),'media_url':url,'original_media_url':imageinfo['url'],'media_is_standard_thumbnail':url!=imageinfo['url']}
