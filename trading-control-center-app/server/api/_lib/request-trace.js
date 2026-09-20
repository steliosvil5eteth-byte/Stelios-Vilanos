import crypto from 'crypto';
export function requestId(req,res){
  const supplied=String(req.headers?.['x-request-id']||'').trim();
  const id=/^[A-Za-z0-9._:-]{8,120}$/.test(supplied)?supplied:`req_${crypto.randomUUID()}`;
  if(res?.setHeader)res.setHeader('X-Request-Id',id);
  return id;
}
